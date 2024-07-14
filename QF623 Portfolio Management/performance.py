import pandas as pd
import numpy as np

class performance:
    def __init__(
            self,
            portfolio_ret: np.array,
            risk_free: float,
            years: int
        ) -> None:

        self.years = years
        self.trade_days = 252
        self.timeframe = self.years * self.trade_days
        
        self.risk_free = risk_free[-self.timeframe : ]
        self.portfolio_ret = portfolio_ret[-self.timeframe : ]
        self.excess_return = self.portfolio_ret - self.risk_free

        self.rolling = portfolio_ret
        self.rolling_rf = risk_free
        self.rolling_excess_return = self.rolling - self.rolling_rf

    def compute_cum_rets(self) -> np.array:
        return np.cumprod(self.rolling + 1)
    
    def compute_annualized_rets(self) -> float:
        annualized_return = np.prod(1 + self.portfolio_ret) ** (self.trade_days / self.timeframe) - 1
        return round(annualized_return * 100, 2)

    def compute_sharpe(self) -> float:
        sharpe = self.excess_return.mean(axis = 0) / self.excess_return.std(axis = 0) * np.sqrt(self.trade_days)
        return np.round(sharpe, 2)
    
    def compute_rolling_sharpe(self) -> list[float]:
        pad = np.zeros(self.timeframe - 1)
        rolling_mean = np.convolve(self.rolling_excess_return, np.ones(self.timeframe) / self.timeframe, mode='valid')
        rolling_mean = np.concatenate((pad, rolling_mean), axis = 0)
        rolling_std = pd.Series(self.rolling_excess_return).rolling(self.timeframe).std().to_numpy()

        rolling_sharpe = (rolling_mean / rolling_std) * np.sqrt(self.trade_days)
        return np.round(rolling_sharpe, 2)

    def compute_sortino(self, downside_risk: float) -> float:
        downside_ret = np.where(self.portfolio_ret < downside_risk, self.portfolio_ret, 0)
        downside_std = downside_ret.std(axis = 0)
        sortino = self.portfolio_ret.mean(axis = 0) / downside_std * np.sqrt(self.trade_days)
        return np.round(sortino, 2)
    
    def compute_rolling_sortino(self, downside_risk: float) -> list[float]:
        pad = np.zeros(self.timeframe - 1)
        rolling_mean = np.convolve(self.rolling, np.ones(self.timeframe) / self.timeframe, mode='valid')
        rolling_mean = np.concatenate((pad, rolling_mean), axis = 0)

        downside_ret = np.where(self.rolling < downside_risk, self.rolling, 0)
        rolling_downside_ret = pd.Series(downside_ret).rolling(self.timeframe).std().to_numpy()

        rolling_sortino = (rolling_mean / rolling_downside_ret) * np.sqrt(self.trade_days)
        
        return np.round(rolling_sortino, 2)

    def compute_max_dd(self) -> float:
        cum_ret = np.cumprod(1 + self.portfolio_ret)   
        cum_roll_max = np.maximum.accumulate(cum_ret)
        drawdowns = cum_roll_max - cum_ret
        max_drawdown = np.max(drawdowns / cum_roll_max)
        return round(max_drawdown * 100, 2)
    
    def compute_drawdown(self) -> list[float]:
        cum_ret = np.cumprod(1 + self.portfolio_ret)
        peak = cum_ret.cummax()
        
        return cum_ret / peak - 1
    
    def compute_volatility(self) -> float:
        vol = self.portfolio_ret.std() * np.sqrt(self.trade_days)
        return np.round(vol * 100, 2)  
    
    def compute_rolling_volatility(self) -> float:
        vol = pd.Series(self.rolling).rolling(self.timeframe).std() * np.sqrt(self.trade_days)
        return np.round((vol * 100).to_numpy(), 2)  
    
    def compute_information_ratio(self, benchmark) -> float:
        benchmark_ret = benchmark[-self.timeframe : ]
        excess_return = self.portfolio_ret - benchmark_ret
        tracking_error = excess_return.std()
        information_ratio = (excess_return).mean() / tracking_error * np.sqrt(self.trade_days)

        return np.round(information_ratio, 2)
    
    def compute_rolling_information_ratio(self, benchmark) -> list[float]:
        pad = np.zeros(self.timeframe - 1)
        rolling_mean = np.convolve(self.rolling, np.ones(self.timeframe) / self.timeframe, mode='valid')
        rolling_benchmark = np.convolve(benchmark, np.ones(self.timeframe) / self.timeframe, mode='valid')
        rolling_mean = np.concatenate((pad, rolling_mean), axis = 0)
        rolling_benchmark = np.concatenate((pad, rolling_benchmark), axis = 0)

        excess_return = rolling_mean - rolling_benchmark

        tracking_error = self.rolling - benchmark
        rolling_tracking_error = pd.Series(tracking_error).rolling(self.timeframe).std().to_numpy()

        rolling_information_ratio = excess_return / rolling_tracking_error * np.sqrt(self.trade_days)

        return np.round(rolling_information_ratio, 2) 

    def compute_rolling_beta(self, benchmark) -> list[float]:
        
        X = pd.Series(benchmark - self.rolling_rf)
        y = pd.Series(self.rolling - self.rolling_rf)

        rolling_beta = X.rolling(self.timeframe).cov(y) / X.rolling(self.timeframe).var() # COV(X,Y) / VAR(X)
    
        return rolling_beta.to_numpy()