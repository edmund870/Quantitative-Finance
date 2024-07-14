import pandas as pd
import numpy as np
from scipy.stats import rankdata
from datetime import timedelta
from backtest import backtest
from performance import performance
from trend_indicators import trend_indicators

class strategy(backtest):
    '''
    Strategy condition to generate weights
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.weights = {}

    def compute_equal_weights(self, long_short: np.array) -> np.array:
               
        n_longs = len(long_short[long_short > 0])
        n_shorts = len(long_short[long_short < 0])

        if n_shorts > 0 and n_longs > 0:
            long_short = np.where(long_short > 0, (self.leverage + self.max_short_weight) / n_longs,
                              np.where(long_short < 0, -self.max_short_weight / n_shorts, 0)) # maintain 200% long, -100% short
        elif n_shorts == 0 and n_longs > 0:
            long_short = np.where(long_short > 0, (self.leverage) / n_longs, 0) # 100% long
        elif n_shorts > 0 and n_longs == 0:
            long_short = np.where(long_short < 0, -self.max_short_weight / n_shorts, 0)
        
        long_short = np.concatenate([long_short, np.array([1 - long_short.sum()])]) # add risk free weight to simulate borrowing / lending

        return long_short
    
    def compute_ranked_weights(self, long_short: np.array) -> np.array:
        
        r = rankdata(long_short, method = 'min')
        n = len(long_short)
        long_short = np.where(r > n/2, 
                              r - n/2, 
                              r - n/2 - 1) 
        long_short /= sum(abs(long_short))
        long_short *= 2 # make 50/50 100/100
        long_short = np.where(long_short > 0,  (self.leverage + 1) * long_short, long_short)
        long_short = np.concatenate([long_short, np.array([1 - long_short.sum()])]) # add risk free weight to simulate borrowing / lending

        return long_short
    
    def compute_vol_target_weights(self, vol: np.array, long_short: np.array, vol_target: float) -> np.array:
        
        scaler = vol_target / vol # Over (under) weight asset/ portfolio during low (high) volatility
        long_short_scaled = long_short * scaler

        total_longs = long_short_scaled[long_short_scaled > 0].sum() # sum long weights
        total_shorts = long_short_scaled[long_short_scaled < 0].sum() # sum short weights

        if total_shorts < 0 and total_longs > 0:
            normalized_long_short = np.where(long_short_scaled > 0, long_short_scaled / total_longs * (self.leverage + self.max_short_weight), 
                                             np.where(long_short_scaled < 0, -long_short_scaled / total_shorts, 0)) # maintain 200% long, -100% short
        elif total_shorts == 0 and total_longs > 0:
            normalized_long_short = np.where(long_short_scaled > 0, long_short_scaled / total_longs * (self.leverage), 0) # 100% long
        elif total_shorts < 0 and total_longs == 0:
            normalized_long_short = np.where(long_short_scaled < 0, -long_short_scaled / total_shorts, 0) # -100% short
        else:
            print(total_longs, total_shorts)
            
        normalized_long_short = np.concatenate([normalized_long_short, np.array([1 - normalized_long_short.sum()])]) # add risk free weight to simulate borrowing / lending

        return normalized_long_short
    
    def moving_avg_strat(
            self, 
            window_1: int, 
            window_2: int
            ) -> dict:
        '''
        Long if spot > window_1 and spot > window_2
        Short otherwise
        '''

        for date in self.rebal_dates:

            date_from = (pd.to_datetime(date) + timedelta(days = -2 * max(window_1, window_2))) # NOTE: days is total days not trading days so days must be sufficient
            hist_df = self.spot[(self.spot.index >= date_from) & (self.spot.index < date)] # filter for the period
            
            MA = trend_indicators(hist_df)          
            MA_1 = MA.compute_moving_average(window_1)[-1]
            MA_2 = MA.compute_moving_average(window_2)[-1]
            
            rebal_day_spot = hist_df.to_numpy()[-1]

            weights = np.where((rebal_day_spot >= MA_1) & (rebal_day_spot >= MA_2), 1, -1)
            weights = self.compute_equal_weights(weights)
            self.weights[date] = weights

        return self.weights
    
    def moving_avg_crossover(
            self, 
            window_1: int, 
            window_2: int,
            weighting: str,
            vol_target: float = 0
            ) -> dict:
        '''
        Long if window_1 > window_2
        Short otherwise
        '''

        for date in self.rebal_dates:

            date_from = (pd.to_datetime(date) + timedelta(days = -2 * max(window_1, window_2))) # NOTE: days is total days not trading days so days must be sufficient
            hist_df = self.spot[(self.spot.index >= date_from) & (self.spot.index < date)] # filter for the period
            
            MA = trend_indicators(hist_df)          
            MA_1 = MA.compute_moving_average(window_1)[-1]
            MA_2 = MA.compute_moving_average(window_2)[-1]
            
            if weighting == 'EQUAL':
                weights = np.where(MA_1 >= MA_2, 1, -1)
                weights = self.compute_equal_weights(weights)
            elif weighting == 'RANKED':
                weights = MA_1 - MA_2
                weights = self.compute_ranked_weights(weights)
            elif weighting == 'VOL_TARGET':
                weights = np.where(MA_1 >= MA_2, 1, -1)
                vol = (hist_df.rolling(len(hist_df)).std() * np.sqrt(252)).iloc[-1].to_numpy()
                weights = self.compute_vol_target_weights(vol, weights, vol_target)

            self.weights[date] = weights

        return self.weights

    def trailing_rets(
            self, 
            lookback: int, 
            weighting: str,
            vol_target: float = 0
            ) -> dict:
        '''
        Long if past Q returns > median
        Short otherwise
        '''
        for date in self.rebal_dates:
            date_from = (pd.to_datetime(date) + timedelta(days = lookback))
            hist_df = self.spot_ret[(self.spot_ret.index >= date_from) & (self.spot_ret.index < date)].drop(columns = 'RF') # filter for the period

            period_ret = (hist_df + 1).prod() - 1

            if weighting == 'EQUAL':
                weights = np.where(period_ret.values > np.median(period_ret.values), 1, -1)
                weights = self.compute_equal_weights(weights)
            elif weighting == 'RANKED':
                weights = period_ret.values - np.median(period_ret.values)
                weights = self.compute_ranked_weights(weights)
            elif weighting == 'VOL_TARGET':
                weights = np.where(period_ret.values > np.median(period_ret.values), 1, -1)
                vol = (hist_df.rolling(len(hist_df)).std() * np.sqrt(252)).iloc[-1].to_numpy()
                weights = self.compute_vol_target_weights(vol, weights, vol_target)

            self.weights[date] = weights
               
        return self.weights
    
    def strategy_2(self) -> None:
        pass