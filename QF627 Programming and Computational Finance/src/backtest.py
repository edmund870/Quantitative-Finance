import numpy as np
import pandas as pd

class backtest:
    def __init__(
        self,
        dates: np.array,
        capital: int,
        commissions: int,
        positions_arr: np.array,
        prices_arr: np.array
    ) -> None:
        self.capital = capital
        self.commissions = commissions
        self.date = dates
        self.position = positions_arr
        self.prices = prices_arr
        self.trade_days = len(prices_arr)
        
        if len(positions_arr) != len(prices_arr):
            raise ValueError('check length of positions and prices')
        
    def run(
        self,
        shares_to_buy: int = None
    ) -> pd.DataFrame:
        """
        compute portfolio value

        Parameters
        ----------
        shares_to_buy : int, optional
            indicate shares to buy else entire capital will be used, by default None

        Returns
        -------
        pd.DataFrame
            portfolio
        """
        cash = np.zeros(self.trade_days)
        shares = np.zeros(self.trade_days)
        holdings = np.zeros(self.trade_days)
        commissions = np.zeros(self.trade_days)
        total = np.zeros(self.trade_days)
        
        cash[0] = self.capital
        total[0] = self.capital
        
        for i in range(1, self.trade_days):
            if self.position[i] == 1 and self.position[i - 1] == 0:
                shares[i] = (cash[i - 1] - self.commissions) / self.prices[i] if shares_to_buy is None else shares_to_buy
                commissions[i] = commissions[i - 1] + self.commissions
                cash[i] = cash[i - 1] - shares[i] * self.prices[i]
            elif self.position[i] == -1 and self.position[i - 1] == 0:
                shares[i] = -(cash[i - 1] - self.commissions) / self.prices[i] if shares_to_buy is None else -shares_to_buy
                commissions[i] = commissions[i - 1] + self.commissions
                cash[i] = cash[i - 1] - shares[i] * self.prices[i]

            elif self.position[i] == 0 and self.position[i - 1] == 1:
                commissions[i] = commissions[i - 1] + self.commissions
                cash[i] = cash[i - 1] + shares[i - 1] * self.prices[i]
                shares[i] = 0
            elif self.position[i] == 0 and self.position[i - 1] == -1:
                commissions[i] = commissions[i - 1] + self.commissions
                cash[i] = cash[i - 1] + shares[i - 1] * self.prices[i]
                shares[i] = 0
                                
            elif self.position[i] == 1 and self.position[i - 1] == -1:
                cash[i] = cash[i - 1] + shares[i - 1] * self.prices[i]
                shares[i] = (cash[i] - self.commissions) / self.prices[i] if shares_to_buy is None else shares_to_buy
                commissions[i] = commissions[i - 1] + self.commissions
                cash[i] = cash[i] - shares[i] * self.prices[i]  
            elif self.position[i] == -1 and self.position[i - 1] == 1:
                cash[i] = cash[i - 1] + shares[i - 1] * self.prices[i]
                shares[i] = -(cash[i] - self.commissions) / self.prices[i] if shares_to_buy is None else -shares_to_buy
                commissions[i] = commissions[i - 1] + self.commissions
                cash[i] = cash[i] - shares[i] * self.prices[i]
                
            else:
                cash[i] = cash[i - 1]
                shares[i] = shares[i - 1]
                holdings[i] = shares[i] * self.prices[i]
                commissions[i] = commissions[i - 1]
            
            holdings[i] = shares[i] * self.prices[i]
            total[i] = cash[i] + holdings[i] - commissions[i]
            
        result = (
            pd.DataFrame(
                {
                    'Date': self.date,
                    'price': self.prices,
                    'trading_direction': self.position,
                    'our_cash': cash,
                    'shares': shares,
                    'our_holdings': holdings,
                    'commissions': commissions,
                    'total': total
                }
            )
        )
        
        result['returns'] = (
            result
            ['total']
            .pct_change()
            .fillna(0)
        )
        
        result['cumulative_returns'] = (
            (
                result['returns']
                + 1
            )
            .cumprod()
        )
        
        result = result.set_index('Date')
        
        return result
        