import polars as pl
import pandas as pd

class indicators:
    def __init__(self, df: pd.DataFrame, tickers: list) -> None:
        """
        Computes technical indicators

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame of prices with date as index
        """
        self.df = pl.from_pandas(df)
        self.price = self.df[tickers]
        self.tickers = tickers

    def SMA(self, windows: list[int]) -> pd.DataFrame:
        """
        Compute simple moving average indicator

        Parameters
        ----------
        windows : list[int]
            Rolling windows

        Returns
        -------
        pd.DataFrame
            Moving Average DataFrame

        Raises
        ------
        TypeError
            If windows are not integer
        """
        if not isinstance(windows, list):
            raise AttributeError("Expected a list of windows")

        if any(not isinstance(window, int) for window in windows):
            raise TypeError("Specify integer windows")

        SMA = self.price.with_columns(
            *[
                pl.col(ticker)
                .rolling_mean(window_size=window, min_periods=1)
                .alias(f"SMA_{window}_{ticker}")
                for window in windows
                for ticker in self.tickers
            ]
        ).drop(self.tickers)

        return SMA

    def EWMA(self, spans: list[int]) -> pd.DataFrame:
        """
        Compute exponentially weighted moving average

        Parameters
        ----------
        spans : list[int]
            windows

        Returns
        -------
        pd.DataFrame
            EWMA DataFrame

        Raises
        ------
        TypeError
            If spans are not integer
        """
        if not isinstance(spans, list):
            raise AttributeError("Expected a list of spans")

        if any(not isinstance(span, int) for span in spans):
            raise TypeError("Specify integer spans")

        EWMA = self.price.with_columns(
            *[
                pl.col(ticker)
                .ewm_mean(span=span, min_periods=1)
                .alias(f"EWMA_{span}_{ticker}")
                for span in spans
                for ticker in self.tickers
            ]
        ).drop(self.tickers)

        return EWMA

    def RSI(self, n: int) -> pd.DataFrame:
        """
        Relative strength index

        Parameters
        ----------
        n : int
            window

        Returns
        -------
        pd.DataFrame
            RSI DataFrame

        Raises
        ------
        TypeError
            If n is not integer
        """
        if not isinstance(n, int):
            raise TypeError("Specify integer window")

        delta = self.price.with_columns(pl.all().diff())

        gain = delta.clone().with_columns(
            *[
                pl.when(pl.col(ticker) < 0)
                .then(0)
                .otherwise(pl.col(ticker))
                .rolling_mean(window_size=n)
                .alias(ticker)
                for ticker in self.tickers
            ]
        )

        loss = delta.clone().with_columns(
            *[
                pl.when(pl.col(ticker) > 0)
                .then(0)
                .otherwise(pl.col(ticker))
                .abs()
                .rolling_mean(window_size=n)
                .alias(ticker)
                for ticker in self.tickers
            ]
        )

        RS = gain / loss

        RSI = RS.with_columns(
            *[
                (100 - 100 / (1 + pl.col(ticker))).alias(ticker)
                for ticker in self.tickers
            ]
        )

        RSI.columns = [f"RSI_{n}_{ticker}" for ticker in self.tickers]

        return RSI

    def MACD(self, short: int, long: int, signal: int) -> pd.DataFrame:
        """
        Moving average convergence divergence

        Parameters
        ----------
        short : int
            Short Window
        long : int
            Long Window
        signal : int
            MACD window

        Returns
        -------
        pd.DataFrame
            MACD + Signal Line DataFrame

        Raises
        ------
        TypeError
            If any short, long or signal is not integer
        """
        if any([not isinstance(n, int) for n in [short, long, signal]]):
            raise TypeError("Specify integer window")

        ewma = self.price.with_columns(
            *[
                pl.col(ticker)
                .ewm_mean(span=short, min_periods=1)
                .alias(f"EWMA_{short}_{ticker}")
                for ticker in self.tickers
            ],
            *[
                pl.col(ticker)
                .ewm_mean(span=long, min_periods=1)
                .alias(f"EWMA_{long}_{ticker}")
                for ticker in self.tickers
            ],
        ).drop(self.tickers)

        MACD = ewma.with_columns(
            *[
                (
                    pl.col(f"EWMA_{short}_{ticker}") - pl.col(f"EWMA_{long}_{ticker}")
                ).alias(f"MACD_{short}_{long}_{signal}_{ticker}")
                for ticker in self.tickers
            ]
        )

        signal_line = MACD.with_columns(
            *[
                (
                    pl.col(f"MACD_{short}_{long}_{signal}_{ticker}").ewm_mean(
                        span=signal,
                    )
                ).alias(f"signal_line_{short}_{long}_{signal}_{ticker}")
                for ticker in self.tickers
            ]
        ).drop(ewma.columns)

        return signal_line

    def ROC(self, n: int) -> pd.DataFrame:
        """
        Rate of Change

        Parameters
        ----------
        n : int
            Window

        Returns
        -------
        pd.DataFrame
            ROC DataFrame

        Raises
        ------
        TypeError
            n must be integer
        """
        if not isinstance(n, int):
            raise TypeError("Specify integer n")

        ROC = self.price.with_columns(
            *[
                (pl.col(ticker).diff(n - 1) / pl.col(ticker).shift(n - 1)).alias(
                    f"ROC_{n}_{ticker}"
                )
                for ticker in self.tickers
            ]
        )

        return ROC.drop(self.tickers)

    def MOM(self, n: int) -> pd.DataFrame:
        """
        Momentum

        Parameters
        ----------
        n : int
            Window

        Returns
        -------
        pd.DataFrame
            MOM DataFrame

        Raises
        ------
        TypeError
            n must be integer
        """
        if not isinstance(n, int):
            raise TypeError("Specify integer n")

        MOM = self.price.with_columns(
            *[
                pl.col(ticker).diff(n).alias(f"MOM_{n}_{ticker}")
                for ticker in self.tickers
            ]
        )

        return MOM.drop(self.tickers)

    def STOK(
        self, close: pd.DataFrame, low: pd.DataFrame, high: pd.DataFrame, n: int
    ) -> pd.DataFrame:
        """
        Stochastic K

        Parameters
        ----------
        close : pd.DataFrame
            Close prices
        low : pd.DataFrame
            Low prices
        high : pd.DataFrame
            High prices
        n : int
            window

        Returns
        -------
        pd.DataFrame
            STOK DataFrame

        Raises
        ------
        ValueError
            Unequal length of DFs
        TypeError
            n must be integer
        """

        if len(close) != len(self.price) != len(low) != len(high):
            raise ValueError("length of df not equal")
        if not isinstance(n, int):
            raise TypeError("Specify integer n")

        close = pl.from_pandas(close)
        low = pl.from_pandas(low)
        high = pl.from_pandas(high)

        STOK = (
            (
                close
                - low.with_columns(
                    *[
                        pl.col(ticker).rolling_min(window_size=n)
                        for ticker in self.tickers
                    ]
                )
            )
            / (
                high.with_columns(
                    *[
                        pl.col(ticker).rolling_max(window_size=n)
                        for ticker in self.tickers
                    ]
                )
                - low.with_columns(
                    *[
                        pl.col(ticker).rolling_min(window_size=n)
                        for ticker in self.tickers
                    ]
                )
            )
        ) * 100

        STOK.columns = [f"STOK_{n}_{ticker}" for ticker in self.tickers]

        return STOK

    def STOD(
        self, close: pd.DataFrame, low: pd.DataFrame, high: pd.DataFrame, n: int
    ) -> pd.DataFrame:
        """
        Stochastic D

        Parameters
        ----------
        close : pd.DataFrame
            Close prices
        low : pd.DataFrame
            Low prices
        high : pd.DataFrame
            High prices
        n : int
            window

        Returns
        -------
        pd.DataFrame
            STOD DataFrame

        Raises
        ------
        ValueError
            Unequal length of DFs
        TypeError
            n must be integer
        """

        if len(close) != len(self.price) != len(low) != len(high):
            raise ValueError("length of df not equal")
        if not isinstance(n, int):
            raise TypeError("Specify integer n")

        STOK = self.STOK(close=close, low=low, high=high, n=n)

        STOD = STOK.with_columns(
            *[
                pl.col(f"STOK_{n}_{ticker}").rolling_mean(window_size=3)
                for ticker in self.tickers
            ]
        )

        STOD.columns = [f"STOD_{n}_{ticker}" for ticker in self.tickers]

        return STOD

    def compute(self, indicator: str, **kwargs) -> None:
        """
        Computes specified indicators

        Parameters
        ----------
        indicator : str
            Name of indicator to compute

        Raises
        ------
        ValueError
            If indicator is not recognized
        """
        indicator = indicator.upper()

        if hasattr(self, indicator):
            TA = getattr(self, indicator)(**kwargs)
            self.df = pl.concat([self.df, TA], how="horizontal")

        else:
            raise ValueError(f"indicator '{indicator}' is not recognized.")
