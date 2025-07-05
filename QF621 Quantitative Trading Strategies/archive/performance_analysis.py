
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


out_path = "output/polygon/optimize_30d_w_cost_sharpe_scaled_z"


dfs = [pl.read_csv(file) for file in glob.glob(f"{out_path}/result/result*.csv")]
df = (
    pl.concat(dfs, how="diagonal_relaxed")
    .with_columns(
        dt=(pl.col("date") + " " + pl.col("time")).str.to_datetime(
            format="%Y-%m-%d %H:%M:%S.%f"
        ),
        date=pl.col("date").cast(pl.Date).dt.date(),
        time=pl.col("time").str.to_time(format="%H:%M:%S.%f"),
    )
    .sort(by="dt")
)


# pairs_ret = (
#     df.select([col for col in df.columns if "_PAIR_RET" in col] + ["dt"])
#     .fill_null(0)
#     .with_columns((pl.all().exclude("dt") + 1).cum_prod())
# )

# px.line(
#     pairs_ret.to_pandas(), x="dt", y=[col for col in pairs_ret.columns if col != "dt"]
# )


etf = "QQQ"
cons = get_cons(etf=etf)
cons_date = cons.read()

data = market_data(
    file_path="C:/Users/edmun/OneDrive/Desktop/Quantitative Trading Strategies/Project/qts/data/polygon/*.parquet"
)
out_path = "output/polygon/optimize_30d_w_cost_sharpe_scaled_z"
earliest_date_year = [
    i
    for i in cons_date.keys()
    if datetime.strptime(i, "%Y-%m-%d").date()
    >= datetime.strptime("2020-06-30", "%Y-%m-%d").date()
]

periods = 30

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
for i in range(10, len(period_ends)):  # range(2, len(period_ends))
    warm_start, train_start, train_end, trade_end = (
        period_ends[i - 10],
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
    cost_analysis_df = pl.concat(cost_analysis_df, how="horizontal")
    cost_analysis_df = cost_analysis_df.with_columns(returns.select(["date", "time"]))
    all_df = pl.concat([all_df, cost_analysis_df], how="vertical")


cumulative_ret_df = all_df.with_columns(
    (pl.all().exclude("date", "time") + 1).cum_prod()
).to_pandas()

cumulative_ret_df["dt"] = cumulative_ret_df["date"].astype(str) + cumulative_ret_df[
    "time"
].astype(str)


(
    all_df.with_columns((pl.all().exclude("date", "time") + 1).cum_prod()).to_pandas()
).iloc[:, :-2].plot(figsize=(30, 10))


all_single_metrics = {}
all_rolling_metrics = {}


for col in all_df.columns[:-2]:
    perf = Performance(
        portfolio_ret=all_df.select(col).fill_null(0).to_numpy().flatten(),
        years=len(all_df) / 390 * 252,
        trade_days=390 * 252,
    )

    all_single_metrics[col] = {
        "Cumulative Returns": perf.compute_cum_rets()[-1],
        "Annualized Returns": perf.compute_annualized_rets(),
        "Sharpe Ratio": perf.compute_sharpe(),
        "Sortino Ratio": perf.compute_sortino(0),
        "Max Drawdown": perf.compute_max_dd(),
        "Volatility": perf.compute_volatility(),
    }

    all_rolling_metrics[col] = {
        "Cumulative Returns": perf.compute_cum_rets(),
        # "Rolling Sharpe": perf.compute_rolling_sharpe(),
        # "Rolling Sortino": perf.compute_rolling_sortino(0),
        "Drawdown": perf.compute_drawdown(),
        "Rolling Volatility": perf.compute_rolling_volatility(),
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


fig = make_subplots(
    rows=3,
    cols=1,
    subplot_titles=("Cumulative Returns", "Drawdown", "Rolling Volatility"),
)
x = all_df["date"].to_numpy().flatten()

for col in all_df.columns[:-2]:
    fig.add_trace(
        go.Scatter(
            x=x,
            y=all_rolling_metrics[col]["Cumulative Returns"],
            mode="lines",
            name="Cumulative Returns",
            # line=dict(color="blue"),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=all_rolling_metrics[col]["Drawdown"],
            mode="lines",
            name="Drawdown",
            # line=dict(color="red"),
        ),
        row=2,
        col=1,
    )

    # fig.add_trace(
    #     go.Scatter(
    #         x=x,
    #         y=all_rolling_metrics[col]["Rolling Volatility"],
    #         mode="lines",
    #         name="Rolling Volatility",
    #         # line=dict(color="green"),
    #     ),
    #     row=3,
    #     col=1,
    # )

fig.update_layout(
    title_text="Performance Metrics",
    height=1500,
    width=1500,
    showlegend=False,
)

# Show the figure
fig.show()



dfs = [
    pl.read_csv(file).with_columns(pl.Series(name="file", values=[file] * 150))
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


