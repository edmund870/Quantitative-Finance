
import polars as pl
import numpy as np
from datetime import datetime, timedelta
import json
import os
import glob

from data.cons_data import get_cons
from data.market_data import market_data

from utils.market_time import market_hours
from utils.params import PARAMS
from utils.performance_measures import Performance


from trade.pairs_trader import PairsTrader


import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio


import warnings

warnings.filterwarnings("ignore")
pio.templates.default = "ggplot2"


out_path = "output/polygon/optimize_60d_w_cost_sharpe_scaled_z_longer_beta_hurst"

# # GENERATE THE BT DFS
etf = "QQQ"
cons = get_cons(etf=etf)
cons_date = cons.read()

data = market_data(file_path="data/polygon/*.parquet")
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

all_df = pl.DataFrame()
all_bt = {}
for i in range(5, len(period_ends)):  # range(2, len(period_ends))
    warm_start, train_start, train_end, trade_end = (
        period_ends[i - 5],
        period_ends[i - 2],
        period_ends[i - 1],
        period_ends[i],
    )
    last_date = datetime.strptime(train_end, "%Y-%m-%d")
    next_day = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")

    if not os.path.isfile(
        (f"{out_path}/params/optimal_params_{next_day}_{trade_end}.json")
    ) or not os.path.isfile((f"{out_path}/result/result_{next_day}_{trade_end}.csv")):
        continue

    with open(f"{out_path}/params/optimal_params_{next_day}_{trade_end}.json") as r:
        p = json.load(r)

    optimal_params = {}
    for key, value in p.items():
        if key not in ["pairs_to_trade", "buffer_capital"]:
            parts = key.split("_")

            pair = (parts[0], parts[1])
            param_name = "_".join(parts[2:])

            if pair not in optimal_params:
                optimal_params[pair] = {}

            optimal_params[pair] = value

    optimal_params["pairs_to_trade"] = p["pairs_to_trade"]
    optimal_params["buffer_capital"] = p["buffer_capital"]

    pairs_to_trade = list([pair for pair in optimal_params.keys() if len(pair) == 2])
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

    cost_analysis_df = []
    for cost in np.arange(0, 0.0006, 0.0001):
        returns = trader.backtest(
            start=pl_next_day,
            end=pl_trade_end,
            cost=cost,
            stop_loss=np.array(
                [
                    optimal_params[(p1, p2)][PARAMS.stop_loss]
                    for p1, p2 in pairs_to_trade
                ]
            ),
        )

        cost_analysis_df.append(
            returns.with_columns(
                pl.col("CAPITAL")
                .pct_change()
                .fill_null(0)
                .alias(f"PORT_RET_w_{cost}_bps_cost")
            ).select(f"PORT_RET_w_{cost}_bps_cost")
        )

        if cost not in all_bt.keys():
            all_bt[cost] = pl.DataFrame()
        all_bt[cost] = pl.concat([all_bt[cost], returns], how="diagonal_relaxed")

    cost_analysis_df = pl.concat(cost_analysis_df, how="horizontal")
    cost_analysis_df = cost_analysis_df.with_columns(returns.select(["date", "time"]))
    all_df = pl.concat([all_df, cost_analysis_df], how="vertical")


for cost, df in all_bt.items():
    df.write_parquet(f"{out_path}/performance/bt_w_{cost}_bps_cost.parquet")


# # BT PERF METRICS
all_df = pl.read_parquet(f"{out_path}/performance/results.parquet")


cumret = all_df.with_columns((pl.all().exclude(["date", "time"]) + 1).cum_prod())
cumret = cumret.rename(
    {"PORT_RET_w_0.00030000000000000003_bps_cost": "PORT_RET_w_0.0003_bps_cost"}
)

fig = make_subplots(
    rows=1,
    cols=1,
    subplot_titles=(
        "Cumulative Returns",
    ),
)
x = cumret["date"].to_numpy().flatten()

for col in cumret.columns[:-2]:
    fig.add_trace(
        go.Scatter(
            x=x,
            y=cumret[col].to_numpy().flatten(),
            mode="lines",
            name=col,
        ),
        row=1,
        col=1,
    )
fig.update_layout(
    title_text="Performance Metrics",
    height=800,
    width=1800,
    showlegend=True,
)
fig.show()


(
    all_df.with_columns((pl.all().exclude(["date", "time"]) + 1).cum_prod())[-1]
    .drop(["date", "time"])
    .to_pandas()
    ** (390 * 252 / len(all_df))
) - 1


all_single_metrics = {}
all_rolling_metrics = {}


for col in all_df.columns[:-2]:
    single_pef = Performance(
        portfolio_ret=all_df.select(col).fill_null(0).to_numpy().flatten(),
        years=len(all_df) / 390 * 252,
        trade_days=390 * 252,
        rolling=False,
    )

    all_single_metrics[col] = {
        "Cumulative Returns": single_pef.compute_cum_rets()[-1],
        "Annualized Returns": single_pef.compute_annualized_rets(),
        "Sharpe Ratio": single_pef.compute_sharpe(),
        "Sortino Ratio": single_pef.compute_sortino(0),
        "Max Drawdown": single_pef.compute_max_dd(),
        "Volatility": single_pef.compute_volatility(),
    }



metrics_df = pl.DataFrame()
for key, value in all_single_metrics.items():
    metrics_df = pl.concat(
        [
            metrics_df,
            pl.DataFrame(all_single_metrics[key])
            .transpose(include_header=True)
            .drop("column")
            .rename({"column_0": key}),
        ],
        how="horizontal",
    )
metrics_df.insert_column(
    0,
    column=pl.DataFrame(all_single_metrics[key])
    .transpose(include_header=True)
    .select("column")
    .to_series(),
)


for col in all_df.columns[:-2]:
    rolling_perf = Performance(
        portfolio_ret=all_df.select(col).fill_null(0).to_numpy().flatten(),
        years=1,
        trade_days=390 * 252,
        rolling=True,
    )

    all_rolling_metrics[col] = {
        "Cumulative Returns": rolling_perf.compute_cum_rets(),
        "Rolling Sharpe": rolling_perf.compute_rolling_sharpe(),
        "Rolling Sortino": rolling_perf.compute_rolling_sortino(0),
        "Drawdown": rolling_perf.compute_drawdown(),
        "Rolling Volatility": rolling_perf.compute_rolling_volatility(),
    }


fig = make_subplots(
    rows=4,
    cols=1,
    subplot_titles=(
        "Cumulative Returns",
        "Drawdown",
        "1Y Rolling Volatility",
        "1Y Rolling Sharpe",
    ),
)
x = all_df["date"].to_numpy().flatten()

for col in all_df.columns[:-2]:
    fig.add_trace(
        go.Scatter(
            x=x,
            y=all_rolling_metrics[col]["Cumulative Returns"],
            mode="lines",
            name=col,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=all_rolling_metrics[col]["Drawdown"],
            mode="lines",
            name=col,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=all_rolling_metrics[col]["Rolling Volatility"],
            mode="lines",
            name=col,
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=all_rolling_metrics[col]["Rolling Sharpe"],
            mode="lines",
            name=col,
        ),
        row=4,
        col=1,
    )

fig.update_layout(
    title_text="Performance Metrics",
    height=1500,
    width=1500,
    showlegend=True,
)

# Show the figure
fig.show()


# # BEST PAIRS
no_cost_bt = pl.read_parquet(f"{out_path}/performance/bt_w_0.0_bps_cost.parquet")


MEGA = (
    all_bt[0.0]
    .select([col for col in all_bt[0.0].columns if "CAPITAL_" in col])
    .with_columns(
        *[
            (
                pl.when((pl.col(col).shift(-1) != 0))
                .then(
                    ((pl.col(col) - pl.col(col).shift(1)) / pl.col(col).shift(1).abs())
                )
                .otherwise(None)
                .fill_null(0)
                .fill_nan(0)
                for col in [col for col in all_bt[0.0].columns if "CAPITAL_" in col]
            )
        ]
    )
    .with_columns(
        *[
            (
                pl.when((pl.col(col).is_infinite()))
                .then(0)
                .otherwise(pl.col(col))
                .alias(f"RET_{col}")
                .fill_null(0)
                .fill_nan(0)
                for col in [col for col in all_bt[0.0].columns if "CAPITAL_" in col]
            )
        ]
    )
)


top_bot = MEGA.select(
    [
        "RET_CAPITAL_CRWD_ON_ROST",
        "RET_CAPITAL_GILD_ON_TEAM",
        "RET_CAPITAL_ALGN_ON_ZS",
        "RET_CAPITAL_AMGN_ON_JD",
        "RET_CAPITAL_CHTR_ON_MTCH",
        "RET_CAPITAL_AMAT_ON_ORLY",
        "RET_CAPITAL_MAR_ON_MRVL",
        "RET_CAPITAL_GFS_ON_SNPS",
        "RET_CAPITAL_ADBE_ON_BIIB",
        "RET_CAPITAL_CMCSA_ON_MAR",
    ]
).with_columns((pl.all() + 1).cum_prod())

x = no_cost_bt["date"].to_numpy().flatten()

fig = make_subplots(
    rows=1,
    cols=1,
    subplot_titles=(
        "Cumulative Returns",
    ),
)

for col in top_bot.columns:
    fig.add_trace(
        go.Scatter(
            x=x,
            y=top_bot[col].to_numpy().flatten(),
            mode="lines",
            name=col,
        ),
        row=1,
        col=1,
    )
    
fig.update_layout(
    title_text="Performance Metrics",
    height=800,
    width=1800,
    showlegend=True,
)
fig.show()


MEGA.select([col for col in MEGA.columns if "RET_CAPITAL" in col]).with_columns(
    (pl.all() + 1).cum_prod() - 1
)[-1].transpose(include_header=True).sort(by="column_0")


# # LOOK AT BEST TRAILS
dfs = [
    pl.read_csv(file).with_columns(pl.Series(name="file", values=[file] * 100))
    for file in glob.glob(f"{out_path}/trials/trials*.csv")
]
df = pl.concat(dfs, how="diagonal_relaxed")


for param in [
    PARAMS.trade_freq,
    PARAMS.beta_win,
    PARAMS.stop_loss,
    PARAMS.z_entry,
    PARAMS.z_exit,
    PARAMS.z_win,
    PARAMS.z_stop_scaler,
    PARAMS.buffer_capital,
]:
    if param == PARAMS.trade_freq:
        df.sort(by="value", descending=True).group_by("file").head(1).select(
            [col for col in df.columns if param in col]
        ).with_columns(pl.all().str.replace("m", "").cast(pl.Int64)).melt()[
            "value"
        ].value_counts().sort("count").to_pandas().dropna().plot(
            title=param, kind="bar", x="value", y="count", figsize=(30, 4)
        )
    else:
        df.sort(by="value", descending=True).group_by("file").head(1).select(
            [col for col in df.columns if param in col]
        ).melt()["value"].value_counts().sort("count").to_pandas().dropna().plot(
            title=param, kind="bar", x="value", y="count", figsize=(30, 4)
        )


