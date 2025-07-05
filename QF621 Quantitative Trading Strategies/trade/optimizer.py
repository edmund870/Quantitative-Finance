import optuna
from optuna.samplers import TPESampler
import optuna.study.study
import polars as pl
import numpy as np

from utils.params import PARAMS
from utils.market_time import market_hours

from data.market_data import market_data
from pairs_finding.pairs_identification import cointegration_pairs
from trade.pairs_trader import PairsTrader


class optimizer:
    """
    Hyperparameter optimizer for a pairs trading strategy using Optuna.

    Parameters
    ----------
    backtester : PairsTrader
        The backtesting engine used to evaluate strategy performance.
    find_pairs : cointegration_pairs
        The object responsible for identifying cointegrated pairs.
    start : pl.Expr
        Polars expression for start filter (e.g., pl.col("date") >= some_date).
    end : pl.Expr
        Polars expression for end filter (e.g., pl.col("date") <= some_date).
    """

    def __init__(
        self,
        data: market_data,
        cost: float,
        find_pairs: cointegration_pairs,
        start: pl.Expr,
        end: pl.Expr,
    ):
        self.find_pairs = find_pairs
        self.start, self.end = start, end
        self.data = data
        self.cost = cost

    def objective(self, trial: optuna.trial.Trial) -> float:
        """
        Objective function to optimize with Optuna.

        Parameters
        ----------
        trial : optuna.trial.Trial
            A trial object that suggests hyperparameter values.

        Returns
        -------
        float
            The Sharpe ratio resulting from the backtest using suggested parameters.
        """
        trade_n_pairs = trial.suggest_int("pairs_to_trade", 1, 10)
        pairs = self.find_pairs.get_top_pairs(n=trade_n_pairs)

        trader = PairsTrader(
            data=self.data,
            pairs=pairs,  # list(params.keys()),  # pairs_to_trade
            params=None,
            trade_hour=market_hours.MARKET,
        )

        params = {
            (p1, p2): {
                PARAMS.beta_win: trial.suggest_int(
                    f"{p1}_{p2}_{PARAMS.beta_win}", 2**10, 2**13, step=2**3
                ),
                PARAMS.z_win: trial.suggest_int(
                    f"{p1}_{p2}_{PARAMS.z_win}", 2**7, 2**10, step=2**3
                ),
                PARAMS.z_entry: trial.suggest_float(
                    f"{p1}_{p2}_{PARAMS.z_entry}", 1.0, 3.0, step=0.2
                ),
                PARAMS.z_exit: trial.suggest_float(
                    f"{p1}_{p2}_{PARAMS.z_exit}", 0.0, 1.0, step=0.2
                ),
                PARAMS.z_stop_scaler: (
                    trial.suggest_float(
                        f"{p1}_{p2}_{PARAMS.z_stop_scaler}", 0.5, 2.0, step=0.5
                    )
                ),
                PARAMS.trade_freq: trial.suggest_categorical(
                    f"{p1}_{p2}_{PARAMS.trade_freq}",
                    [str(i) + "m" for i in range(2, 10, 1)],
                ),
                PARAMS.stop_loss: trial.suggest_float(
                    f"{p1}_{p2}_{PARAMS.stop_loss}", 0.01, 0.05, step=0.005
                ),
            }
            for p1, p2 in pairs
        }

        trader.params = params
        bt_df = trader.backtest(
            start=self.start,
            end=self.end,
            cost=self.cost,
            stop_loss=None,
            buffer_capital=trial.suggest_float(
                PARAMS.buffer_capital, 0.05, 0.5, step=0.05
            ),
        )
        returns = (
            bt_df.select("CAPITAL")
            .with_columns(pl.all().pct_change())
            .fill_null(0)
            .to_numpy()
            .flatten()
        )

        # cumulative_returns = (1 + returns).prod()

        # count_trades = bt_df.select([col for col in bt_df.columns if "CAPITAL_" in col])
        # if len(count_trades) == 0:
        #     return -99
        # pct_time_invested = count_trades.with_columns(
        #     pl.all().sign().abs()
        # ).sum_horizontal().sign().sum() / len(count_trades)

        # if np.nanstd(returns) == 0:
        #     return -1e2

        # # downside_vol = np.nanstd(returns[returns<0])

        # sharpe = (
        #     np.nanmean(returns) / np.nanstd(returns) * np.sqrt(390 * 252)
        # )  # min level

        return (1 + returns).prod()

    def optimize(
        self, study_name, output_file_name, n_trials: int = 200
    ) -> optuna.study.study:
        """
        Runs Optuna optimization over the defined search space.

        Parameters
        ----------
        n_trials : int, optional
            Number of trials to run, by default 200.

        Returns
        -------
        optuna.study.study
            study object
        """
        sampler = TPESampler(seed=621)
        study = optuna.create_study(
            study_name=study_name,
            storage=f"sqlite:///{output_file_name}",
            direction="maximize",
            sampler=sampler,
        )
        study.optimize(
            self.objective,
            n_trials=n_trials,
            show_progress_bar=True,
        )
        return study
