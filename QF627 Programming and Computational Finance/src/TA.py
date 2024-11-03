import pandas as pd

class indicators:
    def __init__(
        self,
        df: pd.DataFrame,
        tickers: list
    ) -> None:
        """
        Computes technical indicators

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame of prices with date as index
        """
        self.price = df[tickers]
        self.df = df
        self.tickers = tickers
    
    def SMA(
        self,
        windows: list[int]
    ) -> pd.DataFrame:
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
            raise AttributeError('Expected a list of windows')
                    
        if any(not isinstance(window, int) for window in windows):
            raise TypeError('Specify integer windows')
        
        SMA = (
            pd.concat(
                [
                    self.price
                    .rolling(window = window, min_periods = window)
                    .mean()
                    .rename(
                        columns = {
                            ticker : f'SMA_{window}_{ticker}'
                            for ticker in self.tickers
                        }
                    )
                    for window in windows
                ],
                axis = 1
            )
        )
        
        return SMA
        
    def EWMA(
        self,
        spans: list[int]
    ) -> pd.DataFrame:
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
            raise AttributeError('Expected a list of spans')
            
        if any(not isinstance(span, int) for span in spans):
            raise TypeError('Specify integer spans')
        
        EWMA = (
            pd.concat(
                [
                    self.price
                    .ewm(span = span, min_periods = span)
                    .mean()
                    .rename(
                        columns = {
                            ticker : f'EWMA_{span}_{ticker}'
                            for ticker in self.tickers
                        }
                    )
                    for span in spans
                ],
                axis = 1
            )
        )
        
        return EWMA
    
    def RSI(
        self,
        n: int
    ) -> pd.DataFrame:
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
            raise TypeError('Specify integer window')
        
        delta = (
            self.price
            .diff()
        )
        
        gain = (
            delta
            .where(
                delta > 0,
                0
            )
            .rolling(window = n)
            .mean()
        )
        
        loss = (
            delta
            .where(
                delta < 0,
                0
            )
            .abs()
            .rolling(window = n)
            .mean()
        )
        
        RS = gain / loss
        
        RSI = 100 - 100 / (1 + RS)
        
        RSI = (
            RSI
            .rename(
                columns = {
                    ticker : f'RSI_{n}_{ticker}'
                    for ticker in self.tickers
                }
            )
        )

        return RSI
        
    def MACD(
        self,
        short: int,
        long: int,
        signal: int
        ) -> pd.DataFrame:
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
            raise TypeError('Specify integer window')
        
        short_ewma = (
            self.price
            .ewm(span = short)
            .mean()
        )
        
        long_ewma = (
            self.price
            .ewm(span = long)
            .mean()
        )
        
        MACD = short_ewma - long_ewma
        
        MACD = (
            MACD
            .rename(
                columns = {
                    ticker : f'MACD_{ticker}'
                    for ticker in self.tickers
                }
            )
        )
        
        signal_line = (
            MACD
            .ewm(span = signal)
            .mean()
            .rename(
                columns = {
                    f'MACD_{ticker}' : f'signal_line_{ticker}'
                    for ticker in self.tickers
                }
            )
        )
        
        MACD = (
            pd.concat(
                [
                    MACD,
                    signal_line
                ],
                axis = 1
            )
        )
        
        return MACD
        
    def ROC(
        self, 
        n: int
    ) -> pd.DataFrame:
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
            raise TypeError('Specify integer n')
        
        M = self.price.diff(n - 1)
        N = self.price.shift(n - 1)
        ROC = (
            (M / N * 100)
            .rename(
                columns = {
                    f'{ticker}' : f'ROC_{n}_{ticker}'
                    for ticker in self.tickers
                }
            )
        )
        
        return ROC
        
    def MOM(
        self,
        n: int
    ) -> pd.DataFrame:
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
            raise TypeError('Specify integer n')
        
        MOM = (
            self.price
            .diff(n)
            .rename(
                columns = {
                    f'{ticker}' : f'MOM_{n}_{ticker}'
                    for ticker in self.tickers
                }
            )
        )
        
        return MOM
    
    def STOK(
        self,
        close: pd.DataFrame, 
        low: pd.DataFrame, 
        high: pd.DataFrame, 
        n: int
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
            raise ValueError('length of df not equal')
        if not isinstance(n, int):
            raise TypeError('Specify integer n')
        
        STOK = (
            (
                (close - low.rolling(n).min()) 
                / 
                (high.rolling(n).max() - low.rolling(n).min())
                * 100
            ) 
            .rename(
                columns = {
                    f'{ticker}' : f'STOK_{n}_{ticker}'
                    for ticker in self.tickers
                }
            )
        )
        
        return STOK

    def STOD(
        self,
        close, 
        low, 
        high, 
        n
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
            raise ValueError('length of df not equal')
        if not isinstance(n, int):
            raise TypeError('Specify integer n')
        
        STOK = (
            (
                (close - low.rolling(n).min()) 
                / 
                (high.rolling(n).max() - low.rolling(n).min())
                * 100
            ) 
            .rename(
                columns = {
                    f'{ticker}' : f'STOD_{n}_{ticker}'
                    for ticker in self.tickers
                }
            )
        )
        
        STOD = STOK.rolling(3).mean()
        
        return STOD
    
    def compute(
        self, 
        indicator: str,
        **kwargs
    ) -> None:
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
            self.df = (
                pd.concat(
                    [
                        self.df,
                        TA
                    ],
                    axis = 1
                )
            )
        else:
            raise ValueError(f"indicator '{indicator}' is not recognized.")