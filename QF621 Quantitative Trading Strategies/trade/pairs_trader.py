import polars as pl
import numpy as np
from numba import njit, prange, cuda
from typing import Any, Dict, Tuple

from data.market_data import market_data
from utils.params import PARAMS
from utils.market_time import market_hours


class PairsTrader:
    """
    Class for executing a pairs trading strategy.

    Parameters
    ----------
    data : market_data
        The market data source containing price and timestamp information.
    pairs : list
        List of tuples representing the asset pairs to trade.
    params : dict
        Dictionary containing strategy parameters for each pair.
    trade_hour : market_hours, optional
        Hours during which trading is allowed.
    """

    def __init__(
        self,
        data: market_data,
        pairs: list[tuple[str, str]],
        params: Dict[Any, Any],
        trade_hour: market_hours = None,
    ):
        self.params = params
        self.data = data
        self.trade_hour = trade_hour
        self.df = data.filter_hours(hours=self.trade_hour).select(["date", "time"])

        self.pairs = pairs

    def update_data(self, data: market_data):
        """
        Updates the internal data and filters by trading hours.

        Parameters
        ----------
        data : market_data
            The new market data.
        """
        self.data = data
        self.df = data.filter_hours(hours=self.trade_hour).select(["date", "time"])

    def compute_beta(
        self,
    ):
        """
        Computes rolling beta for the selected pair using rolling covariance and variance.

        Sets a new column in `self.resampled_df` with the computed beta.
        """
        self.resampled_df = self.resampled_df.with_columns(
            (
                pl.rolling_cov(
                    pl.col(self.p1),
                    pl.col(self.p2),
                    window_size=self.this_param[PARAMS.beta_win],
                    min_periods=100,
                )
                / pl.col(self.p2).rolling_var(
                    window_size=self.this_param[PARAMS.beta_win], min_periods=100
                )
            ).alias(f"BETA_{self.p1}_ON_{self.p2}")  # p1 (Y) = b * p2 (X)
        )

    def compute_spread(self):
        """
        Computes the spread between the two assets in a pair.

        Sets a new column in `self.resampled_df` with the computed spread.
        """
        self.resampled_df = self.resampled_df.with_columns(
            (
                pl.col(self.p1)
                - pl.col(self.p2) * pl.col(f"BETA_{self.p1}_ON_{self.p2}")
            ).alias(f"SPREAD_{self.p1}_ON_{self.p2}")  # p1 (Y) = b * p2 (X)
        )

    def compute_z_score(self):
        """
        Computes the z-score of the spread using a rolling window.

        Sets a new column in `self.resampled_df` with the z-score.
        """
        self.resampled_df = self.resampled_df.with_columns(
            (
                (
                    pl.col(f"SPREAD_{self.p1}_ON_{self.p2}")
                    - pl.col(f"SPREAD_{self.p1}_ON_{self.p2}").rolling_mean(
                        window_size=self.this_param[PARAMS.z_win], min_periods=100
                    )
                )
                / pl.col(f"SPREAD_{self.p1}_ON_{self.p2}").rolling_std(
                    window_size=self.this_param[PARAMS.z_win], min_periods=100
                )
            ).alias(f"Z_{self.p1}_ON_{self.p2}")
        ).with_columns(
            pl.col(f"Z_{self.p1}_ON_{self.p2}")
            .rolling_std(window_size=self.this_param[PARAMS.z_win], min_periods=100)
            .alias(f"Z_VOL_{self.p1}_ON_{self.p2}")
        )

    @staticmethod
    @njit
    def hurst_exponent_fast(ts):
        lags = np.arange(2, 100)
        n_lags = lags.size
        tau = np.empty(n_lags)

        for i in prange(n_lags):
            lag = lags[i]
            diff = ts[lag:] - ts[:-lag]
            tau[i] = np.sqrt(np.std(diff))

        log_lags = np.log(lags)
        log_tau = np.log(tau)
        log_tau = np.where((np.isnan(log_tau)) | (np.isinf(log_tau)), 0.0, log_tau)

        # Linear regression using least squares
        A = np.vstack((log_lags, np.ones_like(log_lags))).T
        slope, _ = np.linalg.lstsq(A, log_tau)[0]

        return slope * 2.0

    @staticmethod
    @njit
    def compute_rolling_hurst(ts, window_size, hurst_func):
        n = len(ts)
        hursts = np.zeros(n)
        for i in prange(window_size - 1, n):
            window = ts[i - window_size + 1 : i + 1]
            hursts[i] = hurst_func(window)
        return hursts

    def compute_stock_returns(self) -> pl.LazyFrame:
        """
        Computes log returns of all stocks excluding the date and time columns.

        Returns
        -------
        pl.LazyFrame
            LazyFrame containing the log returns of all assets.
        """
        returns_df = self.data.filter_hours(hours=self.trade_hour)
        returns_df = returns_df.with_columns(
            pl.all().exclude(["date", "time"]).log().diff()
        )
        return returns_df

    @staticmethod
    @njit
    def simulate_trades(
        n_pairs: int,
        price_arr: np.ndarray,
        beta_arr: np.ndarray,
        Z_arr: np.ndarray,
        hurst_arr: np.ndarray,
        z_entry_arr: np.ndarray,
        z_vol_arr: np.ndarray,
        z_exit_arr: np.ndarray,
        z_stop_arr: np.ndarray,
        cooldown_arr: np.ndarray,
        market_close_flag: np.ndarray,
        cost: float,
        stop_loss: np.ndarray,
        buffer_capital: float,
    ) -> Tuple[
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
    ]:
        """
        Simulates the execution of pair trading strategies using z-score-based mean reversion logic.

        Parameters
        ----------
        n_pairs : int
            Number of trading pairs.
        price_arr : np.ndarray
            Price time series for all assets, shape (n_rows, 2 * n_pairs).
        beta_arr : np.ndarray
            Estimated hedge ratios (betas) between paired assets, shape (n_rows, n_pairs).
        Z_arr : np.ndarray
            Z-score time series representing the spread between pairs, shape (n_rows, n_pairs).
        z_entry_arr : np.ndarray
            Entry threshold for z-score to open a position, shape (n_pairs,).
        z_vol_arr : np.ndarray
            Volatility-adjusted scaling factor for z-score thresholds, shape (n_rows,).
        z_exit_arr : np.ndarray
            Exit threshold for z-score to close a position, shape (n_pairs,).
        z_stop_arr : np.ndarray
            Hard stop threshold for the z-score to force exit, shape (n_rows,).
        cooldown_arr : np.ndarray
            Cooldown periods after a stop-loss before a pair can trade again, shape (n_pairs,).
        market_close_flag : np.ndarray
            Binary indicator (1 = close market), forcing all positions to close at that step, shape (n_rows,).
        cost : float
            Proportional transaction cost per trade (e.g., 0.001 for 0.1%).
        stop_loss : np.ndarray
            Maximum allowed drawdown (negative return) for each pair before triggering stop trading, shape (n_pairs,).
        buffer_capital : float
            Fraction of capital to keep as a buffer and not allocate to trades (e.g., 0.1 for 10%).

        Returns
        -------
        signal_arr : np.ndarray
            Entry signals per pair (-2: strong short, -1: short, 0: none, 1: long, 2: strong long), shape (n_rows, n_pairs).
        pos_arr : np.ndarray
            Position state per pair (-1: short, 0: flat, 1: long), shape (n_rows, n_pairs).
        pos_beta_arr : np.ndarray
            Hedge ratio (beta) held during each position, 0 if flat, shape (n_rows, n_pairs).
        capital_allocation_arr : np.ndarray
            Capital allocated to each pair at each timestep, shape (n_rows, n_pairs).
        remaining_capital : np.ndarray
            Capital not allocated to any trades (i.e., free capital), shape (n_rows,).
        pair_base : np.ndarray
            Baseline price level used for return normalization, shape (n_rows, n_pairs).
        pair_return : np.ndarray
            Calculated return of the pair’s position based on price changes, shape (n_rows, n_pairs).
        SL_arr : np.ndarray
            Binary indicator (1 = stop-loss triggered) for each pair at each timestep, shape (n_rows, n_pairs).
        loss_arr : np.ndarray
            Trailing drawdown percentage for each pair, shape (n_rows, n_pairs).
        stop_trading_arr : np.ndarray
            Countdown of cooldown periods after stop-loss, shape (n_rows, n_pairs).
        """
        n_rows = Z_arr.shape[0]

        signal_arr = np.zeros((n_rows, n_pairs))  # shape: n rows, n pairs
        pos_arr = np.zeros((n_rows, n_pairs))  # shape: n rows, n pairs
        pos_beta_arr = np.zeros((n_rows, n_pairs))  # shape: n rows, n pairs

        pair_base = np.zeros((n_rows, n_pairs))
        pair_return = np.zeros((n_rows, n_pairs))
        capital_allocation_arr = np.zeros((n_rows, n_pairs))  # shape: n rows, n pairs
        remaining_capital = np.ones(n_rows)
        loss_arr = np.zeros((n_rows, n_pairs))
        SL_arr = np.zeros((n_rows, n_pairs))
        stop_trading_arr = np.zeros((n_rows, n_pairs))

        for i in range(1, n_rows):
            is_MR = hurst_arr[i] < 0.5

            ########## GENERATE SIGNAL ##########
            long_cond = Z_arr[i] < -z_entry_arr * (1 + z_vol_arr[i])
            short_cond = Z_arr[i] > z_entry_arr * (1 + z_vol_arr[i])

            signal_arr[i] = np.where(
                (long_cond) & (~np.isnan(Z_arr[i])) & (is_MR),
                2,
                np.where(
                    (long_cond) & (~np.isnan(Z_arr[i])),
                    1,
                    np.where(
                        (short_cond) & (~np.isnan(Z_arr[i])) & (is_MR),
                        -2,
                        np.where((short_cond) & (~np.isnan(Z_arr[i])), -1, 0),
                    ),
                ),
            )

            ########## CHECK EXITS OR STOP LOSS ##########
            exit_long_cond = Z_arr[i - 1] > z_exit_arr * (1 + z_vol_arr[i])
            exit_short_cond = Z_arr[i - 1] < -z_exit_arr * (1 + z_vol_arr[i])

            pos_arr[i] = np.where(
                (
                    (
                        # if long and Z reverts below exit and not NA
                        (pos_arr[i - 1] == 1)
                        & (exit_long_cond)
                        & (~np.isnan(Z_arr[i - 1]))
                    )
                    | (
                        # if short and Z reverts above exit and not NA
                        (pos_arr[i - 1] == -1)
                        & (exit_short_cond)
                        & (~np.isnan(Z_arr[i - 1]))
                    )
                    | (market_close_flag[i] == 1)  # market close flatten
                ),
                0,
                np.where(
                    # if no pos and short spread and market not close
                    (pos_arr[i - 1] == 0)
                    & (signal_arr[i - 1] < 0)
                    & (~np.isnan(beta_arr[i - 1]))
                    & (
                        np.sum(market_close_flag[i - 11 : i + 1]) == 0
                    )  # dont enter at first 10mins open
                    & (np.abs(beta_arr[i - 1]) <= 2)  # restrict beta
                    & (stop_trading_arr[i - 1] == 0),
                    -1,
                    np.where(
                        # if no pos and long spread and market not close
                        (pos_arr[i - 1] == 0)
                        & (signal_arr[i - 1] > 0)
                        & (~np.isnan(beta_arr[i - 1]))
                        & (
                            np.sum(market_close_flag[i - 11 : i + 1]) == 0
                        )  # dont enter at 10mins open
                        & (np.abs(beta_arr[i - 1]) <= 2)
                        & (stop_trading_arr[i - 1] == 0),
                        1,
                        pos_arr[i - 1],  # unchanged pos
                    ),
                ),
            )

            ########## OPEN/CLOSE POSITION HANDLING ##########
            new_pos = ((pos_arr[i - 1] == 0) & (pos_arr[i] != 0)).astype(np.int32)
            close_pos = ((pos_arr[i - 1] != 0) & (pos_arr[i] == 0)).astype(np.int32)

            for pair in prange(n_pairs):
                ########## ENTRY BETA ##########
                if new_pos[pair]:
                    # if new long / short then beta
                    pos_beta_arr[i][pair] = beta_arr[i - 1][pair]
                elif close_pos[pair]:
                    # if exit, beta = 0
                    pos_beta_arr[i][pair] = 0
                else:
                    pos_beta_arr[i][pair] = pos_beta_arr[i - 1][pair]

                ########## PAIR RETURN COMPUTATION ##########
                if new_pos[pair] == 1:
                    pair_base[i - 1][pair] = price_arr[i - 1][2 * pair] + price_arr[
                        i - 1
                    ][2 * pair + 1] * np.abs(pos_beta_arr[i][pair])

                if pos_arr[i][pair] == 1:
                    prev_mv = (
                        price_arr[i - 1][2 * pair]  # long y
                        - price_arr[i - 1][2 * pair + 1]
                        * pos_beta_arr[i][pair]  # short Bx
                    )
                    curr_mv = (
                        price_arr[i][2 * pair]  # long y
                        - price_arr[i][2 * pair + 1] * pos_beta_arr[i][pair]  # short Bx
                    )

                elif pos_arr[i][pair] == -1:
                    prev_mv = (
                        -price_arr[i - 1][2 * pair]  # short y
                        + price_arr[i - 1][2 * pair + 1]
                        * pos_beta_arr[i][pair]  # long Bx
                    )
                    curr_mv = (
                        -price_arr[i][2 * pair]  # short y
                        + price_arr[i][2 * pair + 1] * pos_beta_arr[i][pair]  # long Bx
                    )
                else:
                    pair_base[i][pair] = 0
                    pair_return[i][pair] = 0
                    continue

                pair_base[i][pair] = price_arr[i][2 * pair] + price_arr[i][
                    2 * pair + 1
                ] * np.abs(pos_beta_arr[i][pair])
                pair_return[i][pair] = (curr_mv - prev_mv) / pair_base[i - 1][pair]

            ########## GET PAIRS TRAILING LOSS ##########
            for pair in prange(n_pairs):
                # if capital wasnt 0, check for cumulative returns
                check_loss_arr = capital_allocation_arr.T[pair]
                if check_loss_arr[i - 1] != 0:
                    for lookback in range(i - 1, -1, -1):
                        # find when capital was last 0
                        if (
                            check_loss_arr[lookback] == 0
                            and np.max(check_loss_arr[lookback + 1 : i]) != 0
                        ):
                            loss_arr[i][pair] = (
                                # trailing stop loss
                                check_loss_arr[i - 1]
                                / np.max(check_loss_arr[lookback + 1 : i])
                            ) - 1
                            break

            ########## CHECK STOP LOSS ##########
            SL_arr[i] = np.where(
                (loss_arr[i] <= -stop_loss)
                | (
                    (Z_arr[i - 1] < -z_stop_arr * (1 + z_vol_arr[i]))
                    & (pos_arr[i] == 1)
                )
                | (
                    (Z_arr[i - 1] > z_stop_arr * (1 + z_vol_arr[i]))
                    & (pos_arr[i] == -1)
                ),
                1,
                0,
            )

            this_remaining_capital = remaining_capital[i - 1]

            ########## CLOSE POSITIONS ##########
            if np.any(close_pos) or np.any(SL_arr[i]):
                # if close position or stoploss hit, return capital
                for pair in prange(n_pairs):
                    if close_pos[pair] == 1 or SL_arr[i][pair] == 1:
                        this_remaining_capital += (
                            (1 + pos_arr[i - 1][pair] * pair_return[i - 1][pair])
                            * capital_allocation_arr[i - 1][pair]
                            * (1 - cost)
                        )
                        capital_allocation_arr[i - 1][pair] = 0
                    if SL_arr[i][pair] == 1:
                        stop_trading_arr[i - 1][pair] = cooldown_arr[pair]

            ########## OPEN POSITIONS ##########
            if np.any(new_pos):
                # if multiple signals, then equally divide capital
                deployable_capital = (
                    (this_remaining_capital)
                    / (sum(new_pos * np.abs(signal_arr[i - 1])))
                    * (1 - buffer_capital)
                )
                for j in prange(n_pairs):
                    if new_pos[j] == 1:
                        allocation = (
                            deployable_capital
                            * new_pos[j]
                            * np.abs(signal_arr[i - 1][j])
                        )
                        capital_allocation_arr[i - 1][j] = allocation * (1 - cost)
                        this_remaining_capital -= allocation
            # float capital returns
            capital_allocation_arr[i] = (1 + pair_return[i]) * capital_allocation_arr[
                i - 1
            ]
            remaining_capital[i - 1] = this_remaining_capital
            remaining_capital[i] = this_remaining_capital

            stop_trading_arr[i] = np.array(
                [max(time - 1, 0) for time in stop_trading_arr[i - 1]]
            )

        return (
            signal_arr,
            pos_arr,
            pos_beta_arr,
            capital_allocation_arr,
            remaining_capital,
            pair_base,
            pair_return,
            SL_arr,
            loss_arr,
            stop_trading_arr,
        )

    def generate_backtest_df(self) -> pl.DataFrame:
        """
        Generate a backtest dataframe by computing beta, spread, and z-score for each pair.

        Resamples the raw market data for each pair's trading frequency,
        calculates indicators, and joins them into a unified dataframe.

        Returns
        -------
        pl.DataFrame
            A merged dataframe containing all computed columns across pairs.
        """
        df = self.df
        # each pair has different trading freq, loop and resample to compute beta and Zs
        prices = self.data.filter(
            resample_freq="1m",
            hours=self.trade_hour,
        )
        for pair in self.pairs:
            self.p1, self.p2 = pair[0], pair[1]
            price_df = prices.select(["date", "time", self.p1, self.p2])

            price_df = price_df.rename(
                {
                    self.p1: f"PRICE_{self.p1}_{self.p1}_ON_{self.p2}",
                    self.p2: f"PRICE_{self.p2}_{self.p1}_ON_{self.p2}",
                }
            )
            self.resampled_df = self.data.filter(
                resample_freq=self.params[(self.p1, self.p2)][PARAMS.trade_freq],
                hours=self.trade_hour,
            ).select(["date", "time", self.p1, self.p2])

            self.this_param = self.params[(self.p1, self.p2)]

            self.compute_beta()

            self.compute_spread()

            hurst = self.compute_rolling_hurst(
                ts=self.resampled_df.select(f"SPREAD_{self.p1}_ON_{self.p2}")
                .to_numpy()
                .flatten(),
                window_size=200,
                hurst_func=self.hurst_exponent_fast,
            )

            self.resampled_df = self.resampled_df.with_columns(
                pl.Series(name=f"HURST_{self.p1}_ON_{self.p2}", values=hurst)
            )
            self.compute_z_score()

            df = price_df.join(
                df.join(
                    self.resampled_df.drop([self.p1, self.p2]),
                    how="left",
                    left_on=["date", "time"],
                    right_on=["date", "time"],
                ),
                how="left",
                left_on=["date", "time"],
                right_on=["date", "time"],
            )

            del self.resampled_df

        return df

    def backtest(
        self,
        start: pl.Expr,
        end: pl.Expr,
        cost: float = 0.0005,
        stop_loss: np.ndarray = None,
        buffer_capital: float = 0.1,
    ) -> pl.DataFrame:
        """
        Run the pairs trading backtest using defined strategy parameters and signals.

        Parameters
        ----------
        start : pl.Expr
        Polars expression for start filter (e.g., pl.col("date") >= some_date).
        end : pl.Expr
            Polars expression for end filter (e.g., pl.col("date") <= some_date).
        cost : float, optional
            Transaction cost per entry/exit (default is 0.0005, or 0.05%).
        stop_loss : np.ndarray
            interval returns stop loss, stop trading the pair for the month if hit (e.g. 0.001 for 0.1%).

        Returns
        -------
        pl.DataFrame
            The final dataframe containing trades, positions, returns, and capital evolution.
        """
        df = self.generate_backtest_df()

        # market close flag, this is to flatten position and avoid gap risk
        last_ = (
            df.group_by("date", maintain_order=True)
            .last()
            .with_columns(pl.col("time").cast(pl.Time))
        )
        df = df.with_columns(
            pl.when(
                pl.col("date").is_in(last_["date"])
                & pl.col("time").is_in(last_["time"])
            )
            .then(1)
            .otherwise(0)
            .alias("market_close")
        ).filter(pl.col("date").is_between(start, end))

        Z_arr = df.select(
            # select reorders the columns
            [f"Z_{p1}_ON_{p2}" for p1, p2 in self.pairs]
        ).to_numpy()  # shape: n rows, n pairs

        beta_arr = df.select(
            # select reorders the columns
            [f"BETA_{p1}_ON_{p2}" for p1, p2 in self.pairs]
        ).to_numpy()  # shape: n rows, n pairs

        z_vol_arr = df.select(
            [f"Z_VOL_{p1}_ON_{p2}" for p1, p2 in self.pairs]
        ).to_numpy()

        hurst_arr = df.select(
            # select reorders the columns
            [f"HURST_{p1}_ON_{p2}" for p1, p2 in self.pairs]
        ).to_numpy()  # shape: n rows, n pairs

        market_close_flag = df.select("market_close").to_numpy().flatten()

        z_entry_arr = np.array(
            [self.params[pair][PARAMS.z_entry] for pair in self.pairs]
        )
        z_exit_arr = np.array([self.params[pair][PARAMS.z_exit] for pair in self.pairs])
        z_stop_arr = z_entry_arr * (
            np.array([self.params[pair][PARAMS.z_stop_scaler] for pair in self.pairs])
        )
        cooldown_arr = (
            np.array(
                [
                    int(str.replace(self.params[pair][PARAMS.trade_freq], "m", ""))
                    for pair in self.pairs
                ]
            )
            * 10
        )

        price_list = [
            [f"PRICE_{p1}_{p1}_ON_{p2}", f"PRICE_{p2}_{p1}_ON_{p2}"]
            for p1, p2 in self.pairs
        ]
        price_list = [item for sublist in price_list for item in sublist]
        price_arr = df.select(
            # select reorders the columns
            price_list
        ).to_numpy()

        if stop_loss is None:
            stop_loss = np.array([1e6] * len(self.pairs))

        (
            signal_arr,
            pos_arr,
            pos_beta_arr,
            capital_allocation_arr,
            remaining_capital,
            pair_base,
            pair_return,
            SL_arr,
            loss_arr,
            stop_trading_arr,
        ) = self.simulate_trades(
            n_pairs=len(self.pairs),
            price_arr=price_arr,
            beta_arr=beta_arr,
            Z_arr=Z_arr,
            hurst_arr=hurst_arr,
            z_entry_arr=z_entry_arr,
            z_vol_arr=z_vol_arr,
            z_exit_arr=z_exit_arr,
            z_stop_arr=z_stop_arr,
            cooldown_arr=cooldown_arr,
            market_close_flag=market_close_flag,
            cost=cost,
            stop_loss=stop_loss,
            buffer_capital=buffer_capital,
        )

        backtest_df = pl.concat(
            [
                df,
                pl.DataFrame(
                    signal_arr, schema=[f"SIGNAL_{p1}_ON_{p2}" for p1, p2 in self.pairs]
                ),
                pl.DataFrame(
                    pos_arr, schema=[f"POS_{p1}_ON_{p2}" for p1, p2 in self.pairs]
                ),
                pl.DataFrame(
                    pos_beta_arr,
                    schema=[f"POS_BETA_{p1}_ON_{p2}" for p1, p2 in self.pairs],
                ),
                pl.DataFrame(
                    pair_base,
                    schema=[f"PAIR_BASE_{p1}_ON_{p2}" for p1, p2 in self.pairs],
                ),
                pl.DataFrame(
                    pair_return,
                    schema=[f"PAIR_RET_{p1}_ON_{p2}" for p1, p2 in self.pairs],
                ),
                pl.DataFrame(
                    SL_arr,
                    schema=[f"SL_{p1}_ON_{p2}" for p1, p2 in self.pairs],
                ),
                pl.DataFrame(
                    loss_arr,
                    schema=[f"LOSS_{p1}_ON_{p2}" for p1, p2 in self.pairs],
                ),
                pl.DataFrame(
                    stop_trading_arr,
                    schema=[f"COOLDOWN_{p1}_ON_{p2}" for p1, p2 in self.pairs],
                ),
                pl.DataFrame(
                    capital_allocation_arr,
                    schema=[f"CAPITAL_{p1}_ON_{p2}" for p1, p2 in self.pairs],
                ),
                pl.DataFrame(remaining_capital, schema=["REMAINING_CAPITAL"]),
            ],
            how="horizontal",
        ).with_columns(
            pl.sum_horizontal(
                [f"CAPITAL_{p1}_ON_{p2}" for p1, p2 in self.pairs]
                + ["REMAINING_CAPITAL"]
            ).alias("CAPITAL")
        )

        return backtest_df
