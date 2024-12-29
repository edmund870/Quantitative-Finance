import numpy as np
from numba import njit


class Performance:
    def __init__(
        self, portfolio_ret: np.ndarray, years: int, trade_days: int = 252
    ) -> None:
        """
        Compute Performance Metrics
        1. Cumulative Returns `compute_cum_rets`
        2. Annualized Returns `compute_annualized_rets`
        3. Sharpe + Rolling Sharpe `compute_sharpe` / `compute_rolling_sharpe`
        4. Sortino + Rolling Sortino `compute_sortino` / `compute_rolling_sortino`
        5. Max Drawdown + Rolling Drawdown `compute_max_dd` / `compute_drawdown`
        6. Volatility + Rolling Volatility `compute_volatility` / `compute_rolling_volatility`
        7. Information Ratio + Rolling Information Ratio `compute_information_ratio` / `compute_rolling_information_ratio`
        8. Rolling Beta + Rolling Beta `compute_beta` / `compute_rolling_beta`
        9. Rolling Alpha `compute_alpha` / `compute_rolling_alpha`
        10. M2 Measure `compute_M2`
        ...

        Parameters
        ----------
        portfolio_ret: np.ndarray
            Returns Array
        years: int
            Look back period
        trade_days: int
            Trading Days (set as 252)
        """

        self.years: int = years
        self.trade_days: int = trade_days
        self.timeframe: int = int(self.years * self.trade_days)

        self.portfolio_ret: np.ndarray = portfolio_ret[-self.timeframe :]
        self.rolling: np.ndarray = portfolio_ret

        self.rolling_mean, self.rolling_std = self.compute_stat()

    def compute_stat(self) -> tuple[np.ndarray, np.ndarray]:
        return self._compute_stat(rolling=self.rolling, timeframe=self.timeframe)

    def compute_cum_rets(self) -> np.ndarray:
        return self._compute_cum_rets(rolling=self.rolling)

    def compute_annualized_rets(self) -> float:
        return self._compute_annualized_rets(
            portfolio_ret=self.portfolio_ret,
            trade_days=self.trade_days,
            timeframe=self.timeframe,
        )

    def compute_sharpe(self) -> float:
        return self._compute_sharpe(
            portfolio_ret=self.portfolio_ret, trade_days=self.trade_days
        )

    def compute_rolling_sharpe(self) -> np.ndarray:
        return self._compute_rolling_sharpe(
            rolling_mean=self.rolling_mean,
            rolling_std=self.rolling_std,
            trade_days=self.trade_days,
        )

    def compute_sortino(self, downside_risk: float) -> float:
        return self._compute_sortino(
            portfolio_ret=self.portfolio_ret,
            downside_risk=downside_risk,
            trade_days=self.trade_days,
        )

    def compute_rolling_sortino(self, downside_risk: float) -> np.ndarray:
        return self._compute_rolling_sortino(
            rolling=self.rolling,
            rolling_mean=self.rolling_mean,
            downside_risk=downside_risk,
            timeframe=self.timeframe,
            trade_days=self.trade_days,
        )

    def compute_max_dd(self) -> float:
        return self._compute_max_dd(portfolio_ret=self.portfolio_ret)

    def compute_drawdown(self) -> np.ndarray:
        return self._compute_drawdown(rolling=self.rolling)

    def compute_volatility(self) -> float:
        return self._compute_volatility(
            portfolio_ret=self.portfolio_ret, trade_days=self.trade_days
        )

    def compute_rolling_volatility(self) -> float:
        return self._compute_rolling_volatilty(
            rolling_std=self.rolling_std, trade_days=self.trade_days
        )

    def compute_information_ratio(self, benchmark_ret: np.ndarray) -> float:
        return self._compute_information_ratio(
            portfolio_ret=self.portfolio_ret,
            benchmark_ret=benchmark_ret,
            trade_days=self.trade_days,
            timeframe=self.timeframe,
        )

    def compute_rolling_information_ratio(
        self, benchmark_ret: np.ndarray
    ) -> np.ndarray:
        return self._compute_rolling_information_ratio(
            rolling=self.rolling,
            rolling_mean=self.rolling_mean,
            benchmark_ret=benchmark_ret,
            trade_days=self.trade_days,
            timeframe=self.timeframe,
        )

    def compute_beta(self, benchmark_ret: np.ndarray) -> float:
        return self._compute_beta(
            portfolio_ret=self.portfolio_ret,
            benchmark_ret=benchmark_ret,
            timeframe=self.timeframe,
        )

    def compute_rolling_beta(self, benchmark_ret: np.ndarray) -> np.ndarray:
        return self._compute_rolling_beta(
            rolling=self.rolling, benchmark_ret=benchmark_ret, timeframe=self.timeframe
        )

    def compute_alpha(self, benchmark_ret: np.ndarray) -> float:
        return self._compute_alpha(
            beta=self.compute_beta(benchmark_ret=benchmark_ret),
            portfolio_ret=self.portfolio_ret,
            benchmark_ret=benchmark_ret,
        )

    def compute_rolling_alpha(self, benchmark_ret: np.ndarray) -> float:
        return self._compute_rolling_alpha(
            beta=self.compute_rolling_beta(benchmark_ret=benchmark_ret),
            rolling=self.rolling,
            benchmark_ret=benchmark_ret,
        )

    def compute_M2(self, benchmark_ret: np.ndarray) -> float:
        return self._compute_M2(
            sharpe=self.compute_sharpe(),
            benchmark_ret=benchmark_ret,
            timeframe=self.timeframe,
            trade_days=self.trade_days,
        )

    @staticmethod
    @njit(fastmath=True)
    def _compute_stat(
        rolling: np.ndarray, timeframe: int
    ) -> tuple[np.ndarray, np.ndarray]:
        pad: np.ndarray = np.zeros(timeframe - 1)
        rolling_mean: np.ndarray = np.convolve(
            rolling, np.ones(timeframe) / timeframe, mode="valid"
        )
        rolling_mean: np.ndarray = np.concatenate((pad, rolling_mean), axis=0)

        n: int = rolling.shape[0]
        rolling_std: np.ndarray = np.empty(n)

        for i in range(n):
            if i < timeframe - 1:
                rolling_std[i] = np.nan
            else:
                rolling_std[i] = np.std(rolling[i - timeframe + 1 : i + 1])

        return rolling_mean, rolling_std

    @staticmethod
    @njit(fastmath=True)
    def _compute_cum_rets(rolling: np.ndarray) -> np.ndarray:
        return np.cumprod(rolling + 1)

    @staticmethod
    @njit(fastmath=True)
    def _compute_annualized_rets(
        portfolio_ret: np.ndarray, trade_days: int, timeframe: int
    ) -> float:
        annualized_return: np.ndarray = (
            np.prod(1 + portfolio_ret) ** (trade_days / timeframe) - 1
        )

        return np.round(annualized_return * 100, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_sharpe(portfolio_ret: np.ndarray, trade_days: int) -> float:
        mean_return: float = portfolio_ret.mean()
        std_return: float = portfolio_ret.std()
        sharpe: float = mean_return / std_return * np.sqrt(trade_days)

        return np.round(sharpe, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_rolling_sharpe(
        rolling_mean: np.ndarray,
        rolling_std: np.ndarray,
        trade_days: int,
    ) -> np.ndarray:
        rolling_sharpe: np.ndarray = (rolling_mean / rolling_std) * np.sqrt(trade_days)

        return np.round(rolling_sharpe, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_sortino(
        portfolio_ret: np.ndarray, downside_risk: float, trade_days: int
    ) -> float:
        downside_ret: np.ndarray = np.where(
            portfolio_ret < downside_risk, portfolio_ret, 0
        )
        downside_std: float = downside_ret.std()
        sortino: float = portfolio_ret.mean() / downside_std * np.sqrt(trade_days)

        return np.round(sortino, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_rolling_sortino(
        rolling: np.ndarray,
        rolling_mean: np.ndarray,
        downside_risk: float,
        timeframe: int,
        trade_days: int,
    ) -> np.ndarray:
        downside_ret: np.ndarray = np.where(rolling < downside_risk, rolling, 0)
        rolling_downside_ret: np.ndarray = np.array(
            [
                np.std(downside_ret[i - timeframe + 1 : i + 1])
                if i >= timeframe - 1
                else np.nan
                for i in range(len(downside_ret))
            ]
        )

        rolling_sortino: np.ndarray = (rolling_mean / rolling_downside_ret) * np.sqrt(
            trade_days
        )

        return np.round(rolling_sortino, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_max_dd(portfolio_ret: np.ndarray) -> float:
        cum_ret: np.ndarray = np.cumprod(1 + portfolio_ret)

        n: int = cum_ret.shape[0]
        cum_roll_max: np.ndarray = np.empty(n)
        cum_roll_max[0] = cum_ret[0]
        for i in range(1, n):
            cum_roll_max[i] = max(cum_roll_max[i - 1], cum_ret[i])

        drawdowns: np.ndarray = cum_roll_max - cum_ret
        max_drawdown: float = np.max(drawdowns / cum_roll_max)

        return np.round(max_drawdown * 100, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_drawdown(rolling: np.ndarray) -> np.ndarray:
        cum_ret: np.ndarray = np.cumprod(1 + rolling)
        n: int = cum_ret.shape[0]
        peak: np.ndarray = np.empty(n)
        peak[0] = cum_ret[0]
        for i in range(1, n):
            peak[i] = max(peak[i - 1], cum_ret[i])

        return cum_ret / peak - 1

    @staticmethod
    @njit(fastmath=True)
    def _compute_volatility(portfolio_ret: np.ndarray, trade_days: int) -> float:
        vol: float = portfolio_ret.std() * np.sqrt(trade_days)

        return np.round(vol * 100, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_rolling_volatilty(
        rolling_std: np.ndarray, trade_days: int
    ) -> np.ndarray:
        return np.round(rolling_std * np.sqrt(trade_days) * 100, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_information_ratio(
        portfolio_ret: np.ndarray,
        benchmark_ret: np.ndarray,
        trade_days: int,
        timeframe: int,
    ) -> float:
        benchmark_ret: np.ndarray = benchmark_ret[-timeframe:]
        excess_return: np.ndarray = portfolio_ret - benchmark_ret
        tracking_error: float = excess_return.std()
        information_ratio: float = (excess_return.mean() / tracking_error) * np.sqrt(
            trade_days
        )

        return np.round(information_ratio, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_rolling_information_ratio(
        rolling: np.ndarray,
        rolling_mean: np.ndarray,
        benchmark_ret: np.ndarray,
        trade_days: int,
        timeframe: int,
    ) -> np.ndarray:
        pad: np.ndarray = np.zeros(timeframe - 1)
        rolling_benchmark: np.ndarray = np.convolve(
            benchmark_ret, np.ones(timeframe) / timeframe, mode="valid"
        )
        rolling_benchmark: np.ndarray = np.concatenate((pad, rolling_benchmark), axis=0)

        excess_return: np.ndarray = rolling_mean - rolling_benchmark
        tracking_error: np.ndarray = rolling - benchmark_ret
        rolling_tracking_error: np.ndarray = np.array(
            [
                np.std(tracking_error[i - timeframe + 1 : i + 1])
                if i >= timeframe - 1
                else np.nan
                for i in range(len(tracking_error))
            ]
        )

        rolling_information_ratio: np.ndarray = (
            excess_return / rolling_tracking_error
        ) * np.sqrt(trade_days)

        return np.round(rolling_information_ratio, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_beta(
        portfolio_ret: np.ndarray, benchmark_ret: np.ndarray, timeframe: int
    ) -> float:
        X: np.ndarray = benchmark_ret[-timeframe:]
        y: np.ndarray = portfolio_ret
        beta: float = np.cov(X, y)[0, 1] / np.var(X)

        return np.round(beta, 2)

    @staticmethod
    @njit(fastmath=True)
    def _compute_rolling_beta(
        rolling: np.ndarray, benchmark_ret: np.ndarray, timeframe: int
    ) -> np.ndarray:
        rolling_beta: np.ndarray = np.empty(benchmark_ret.shape[0])

        for i in range(benchmark_ret.shape[0]):
            if i < timeframe - 1:
                rolling_beta[i] = np.nan
            else:
                rolling_beta[i] = np.cov(
                    benchmark_ret[i - timeframe + 1 : i + 1],
                    rolling[i - timeframe + 1 : i + 1],
                )[0, 1] / np.var(benchmark_ret[i - timeframe + 1 : i + 1])

        return rolling_beta

    @staticmethod
    @njit(fastmath=True)
    def _compute_alpha(
        beta: float, portfolio_ret: np.ndarray, benchmark_ret: np.ndarray
    ) -> float:
        return np.nanmean(portfolio_ret) - beta * np.nanmean(benchmark_ret)

    @staticmethod
    @njit(fastmath=True)
    def _compute_rolling_alpha(
        beta: np.ndarray,
        rolling: np.ndarray,
        benchmark_ret: np.ndarray,
    ) -> np.ndarray:
        return rolling - beta * benchmark_ret

    @staticmethod
    @njit(fastmath=True)
    def _compute_M2(
        sharpe: float, benchmark_ret: np.ndarray, timeframe: int, trade_days: int
    ) -> float:
        benchmark_volatility: float = benchmark_ret[-timeframe:].std() * np.sqrt(
            trade_days
        )
        M2: float = sharpe * benchmark_volatility

        return np.round(M2 * 100, 2)


if __name__ == "__main__":
    import inspect

    ret = np.random.uniform(-0.1, 0.1, size=500)
    perf = Performance(portfolio_ret=ret, years=1, trade_days=252)
    metrics = {}
    metric_args = {
        "benchmark_ret": np.random.uniform(-0.1, 0.1, size=500),
        "downside_risk": 0,
    }

    for metric in dir(perf):
        attr = getattr(perf, metric)
        if callable(attr) and "_compute" not in metric and not metric.startswith("__"):
            args = inspect.getfullargspec(attr).args
            func_arg = []
            for arg in args:
                if arg != "self":
                    func_arg.append(metric_args.get(arg, ()))
            metrics[str(metric).replace("compute_", "")] = attr(*func_arg)
            print(metrics)

    print(metrics)
