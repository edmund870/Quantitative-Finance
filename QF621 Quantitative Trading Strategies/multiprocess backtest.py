import polars as pl
import numpy as np
from datetime import datetime, timedelta
import json
import os
import concurrent.futures

from data.cons_data import get_cons
from data.market_data import market_data

from utils.market_time import market_hours
from utils.params import PARAMS
from utils.clustering_methods import Clustering_methods

from pairs_finding.pairs_identification import cointegration_pairs
from pairs_finding.clustering import Clustering

from trade.pairs_trader import PairsTrader
from trade.optimizer import optimizer

import warnings

warnings.filterwarnings("ignore")


def run(periods):
    warm_start, train_start, train_end, trade_end = (
        periods[0],
        periods[1],
        periods[2],
        periods[3],
    )
    data = periods[4]
    cons_date = periods[5]
    out_path = periods[6]

    # next trading day
    last_date = datetime.strptime(train_end, "%Y-%m-%d")
    next_day = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")

    print(train_start, train_end)
    if os.path.isfile((f"{out_path}/result/result_{next_day}_{trade_end}.csv")):
        return

    # TRAINING PERIOD FINDING OPTIMAL PARAMS #
    data.read(cons=cons_date[train_end], start=warm_start, end=train_end)

    train = data.filter(resample_freq="30m", hours=market_hours.MARKET)

    c = Clustering(df=train.select(pl.all().exclude(["date", "time"])))

    # c.run_clustering(method=Clustering_methods.kmeans, min_clusters=2, max_clusters=10)

    c.run_clustering(method=Clustering_methods.agnes, min_clusters=2, max_clusters=10)

    find_pairs = cointegration_pairs(
        df=train.select(pl.all().exclude(["date", "time"])),
        p_val_cutoff=0.01,
        cluster_pairs=c.cluster_pairs,
    )
    find_pairs.identify_pairs()

    potential_trade_pairs = [
        pair[0]
        for sublist in find_pairs.cluster_sorted_pairs.values()
        for pair in sublist
    ]

    data.read(
        cons=set([item for pair in potential_trade_pairs for item in pair]),
        start=warm_start,
        end=train_end,
    )

    opt = optimizer(
        data=data,
        cost=0.0005,
        find_pairs=find_pairs,  # list(params.keys()), # pairs_to_trade
        start=pl.lit(train_start).str.strptime(pl.Date, "%Y-%m-%d"),
        end=pl.lit(train_end).str.strptime(pl.Date, "%Y-%m-%d"),
    )

    del c, find_pairs

    study = opt.optimize(
        study_name="PAIRS_TRADING",
        output_file_name=f"{out_path}/db/result_{next_day}_{trade_end}.db",
        n_trials=100,
    )
    p = study.best_params

    study.trials_dataframe().to_csv(
        f"{out_path}/trials/trials_{train_start}_{train_end}.csv"
    )

    del opt, study

    optimal_params = {}
    for key, value in p.items():
        if key not in ["pairs_to_trade", "buffer_capital"]:
            parts = key.split("_")

            pair = (parts[0], parts[1])
            param_name = "_".join(parts[2:])

            if pair not in optimal_params:
                optimal_params[pair] = {}

            optimal_params[pair][param_name] = value

    # TRADING PERIOD USING PARAMS
    # reading pairs only from next trading day to next q end
    pairs_to_trade = list(optimal_params.keys())
    data.read(
        cons=set([item for pair in pairs_to_trade for item in pair]),
        start=train_start,
        end=trade_end,
    )

    trader = PairsTrader(
        data=data,
        pairs=pairs_to_trade,  # list(params.keys()),  # pairs_to_trade
        params=optimal_params,
        trade_hour=market_hours.MARKET,
    )

    pl_next_day = pl.lit(next_day).str.strptime(pl.Date, "%Y-%m-%d")
    pl_trade_end = pl.lit(trade_end).str.strptime(pl.Date, "%Y-%m-%d")
    returns = trader.backtest(
        start=pl_next_day,
        end=pl_trade_end,
        cost=0.0005,
        stop_loss=np.array(
            [optimal_params[(p1, p2)][PARAMS.stop_loss] for p1, p2 in pairs_to_trade]
        ),
        buffer_capital=p[PARAMS.buffer_capital],
    )

    returns.with_columns(
        pl.col("CAPITAL").pct_change().fill_null(0).alias("PORT_RET")
    ).write_csv(f"{out_path}/result/result_{next_day}_{trade_end}.csv")

    convert_json = {f"{p1}_{p2}": params for (p1, p2), params in optimal_params.items()}
    convert_json["pairs_to_trade"] = p["pairs_to_trade"]
    convert_json["buffer_capital"] = p["buffer_capital"]

    with open(
        f"{out_path}/params/optimal_params_{next_day}_{trade_end}.json", "w"
    ) as json_file:
        json.dump(convert_json, json_file, default=str)

    del data, returns, trader  # free ram


if __name__ == "__main__":
    etf = "QQQ"
    cons = get_cons(etf=etf)
    cons_date = cons.read()

    data = market_data(file_path="data/polygon/*.parquet")
    out_path = "output/polygon/optimize_60d_w_cost_sharpe_scaled_z_longer_beta_hurst"
    earliest_date_year = [
        i
        for i in cons_date.keys()
        if datetime.strptime(i, "%Y-%m-%d").date()
        >= datetime.strptime("2020-06-30", "%Y-%m-%d").date()
    ]

    periods = 60

    period_ends = (
        pl.DataFrame(earliest_date_year, schema=["Date"])
        .with_columns(
            pl.all().cast(pl.Date),
        )
        .with_columns((pl.col("Date").rank() // periods).alias("Chunk"))
        .group_by("Chunk", maintain_order=True)
        .agg(pl.col("Date").last())["Date"]
        .dt.strftime("%Y-%m-%d")
        .to_list()
    )

    periods = []
    for i in range(5, len(period_ends)):  # range(2, len(period_ends))
        periods.append(
            (
                period_ends[i - 5],
                period_ends[i - 2],
                period_ends[i - 1],
                period_ends[i],
                data,
                cons_date,
                out_path,
            )
        )

    with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run, p) for p in periods]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Exception occurred: {e}")
