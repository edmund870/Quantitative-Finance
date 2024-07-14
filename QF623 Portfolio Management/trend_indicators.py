import pandas as pd
import numpy as np

class trend_indicators:
    def __init__(
            self,
            spot: pd.DataFrame
    ) -> None:
        '''
        Generates Trend Following Indicators
        '''
        self.spot = spot

    def compute_moving_average(self, window: int) -> pd.DataFrame:
        return self.spot.rolling(window).mean().to_numpy()