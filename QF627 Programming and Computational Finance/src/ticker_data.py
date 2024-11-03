import pandas as pd
import numpy as np
import yfinance as yf

class ticker_info:
    def __init__(
            self,
            tickers: list[str]
        ) -> None:
        """
        Retrieves ticker related information

        Parameters
        ----------
        tickers : list[str]
            List of tickers
        """
        
        self.tickers = tickers
        self.price = None

    def download(
        self, 
        start_date: str, 
        end_date: str,
        variable: str
    ) -> None:
        """
        Download Adj Close from Yahoo Finance
        Updates self.price variable

        Parameters
        ----------
        start_date : str
            Start Date
        end_date : str
            End Date
        variable : str
            Variable to download ('Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume')
        """
        self.price = (
            yf.download(
                tickers = self.tickers, 
                start = start_date, 
                end = end_date
            )
            [variable]
        )
        if len(self.tickers) == 1:
            self.price = (
                self.price
                .to_frame()
                .rename(
                    columns = {
                        variable : self.tickers[0]
                    }
                )
            )
    
    def compute_returns(
        self,
        return_type: str
    ) -> pd.DataFrame:
        """
        Calculate Returns

        Parameters
        ----------
        return_type : str
            'simple' or 'log'
            
        Returns
        -------
        pd.DataFrame
            Returns DF based on specified return calculation

        Raises
        ------
        TypeError
            If price variable is None
        """
        return_type = return_type.upper()
        
        if self.price is None:
            raise ValueError('Price data is not available. Run `download()` first')
        
        if return_type == 'SIMPLE':
            returns = (
                self.price
                .pct_change()
            )
        elif return_type == 'LOG':
            returns = (
                np.log(
                    self.price
                )
                .diff()
            )
        else:
            raise ValueError('Invalid return type. Use "simple" or "log".')
        
        return returns