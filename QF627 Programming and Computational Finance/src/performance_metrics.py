import numpy as np
import pandas as pd


class performance:
    def __init__(self, df: pd.DataFrame, trading_days: int, return_type: str) -> None:
        self.df = df
        self.trading_days = trading_days
        self.n_years = trading_days / len(df)
        self.return_type = return_type.upper()

        if self.return_type not in ["SIMPLE", "GEOMETRIC"]:
            raise ValueError('Invalid return type. Use "simple" or "geometric".')
        if "returns" not in df.columns:
            raise KeyError("returns column not found")

        self.returns = df["returns"].values
        self.df["cumulative_returns"] = (1 + self.df["returns"]).cumprod()

    def annualized_returns(self) -> float:
        """
        Computes annualized returns using simple or geometric

        Returns
        -------
        float
            annualized returns
        """
        if self.return_type == "GEOMETRIC":
            annualized_return = (
                np.power(np.prod(1 + self.returns), (1 / self.n_years)) - 1
            )

        elif self.return_type == "SIMPLE":
            annualized_return = self.returns.mean() * self.trading_days

        return annualized_return

    def annualized_volatility(self) -> float:
        """
        Computes annualzied volatility

        Returns
        -------
        float
            annualized volatility
        """
        vol = self.returns.std() * np.sqrt(self.trading_days)
        return vol

    def sharpe(
        self,
    ) -> float:
        """
        Computes annualized sharpe

        Returns
        -------
        float
            annualized sharpe
        """
        returns = self.annualized_returns()
        vol = self.annualized_volatility()

        annualized_sharpe = returns / vol

        return annualized_sharpe

    def drawdown(self) -> dict[float, int]:
        """
        computes list of drawdowns

        Returns
        -------
        dict[float, int]
            Dictionary with drawdown respective drawdown days
            sorted by highest drawdwon first
        """
        self.df["max_gross_return"] = self.df["cumulative_returns"].cummax()
        self.df["drawdown"] = (self.df["cumulative_returns"] / self.df["max_gross_return"]) - 1

        drawdown_reset = self.df[self.df["drawdown"] == 0].index
        drawdown_reset = np.append(drawdown_reset, self.df.index[-1:])

        drawdowns = {
            "Max Drawdown": [],
            "Duration (in Days)": [],
            "Duration (in Trading Days)": [],
            "Start": [],
            "End": [],
        }
        for i in range(1, len(drawdown_reset)):
            filtered_df = self.df[
                (self.df.index >= drawdown_reset[i - 1]) & (self.df.index < drawdown_reset[i])
            ]

            mdd = filtered_df["drawdown"].min()
            duration_days = filtered_df.index.max() - filtered_df.index.min()

            duration_trade_days = pd.Timedelta(len(filtered_df) - 1, "d")

            drawdowns["Max Drawdown"].append(mdd)
            drawdowns["Duration (in Days)"].append(duration_days)
            drawdowns["Duration (in Trading Days)"].append(duration_trade_days)
            drawdowns["Start"].append(drawdown_reset[i])
            drawdowns["End"].append(drawdown_reset[i - 1])

        return drawdowns

    def annual_returns(self) -> pd.DataFrame:
        """
        Computes portfolio annual returns

        Returns
        -------
        pd.DataFrame
            DataFrame with annual returns and average annual returns
        """
        self.df["year"] = self.df.index.year

        portfolio_by_year = self.df.groupby("year").agg(
            end=("cumulative_returns", "last")
        )

        portfolio_by_year["returns"] = portfolio_by_year["end"].pct_change()

        portfolio_by_year["avg"] = portfolio_by_year["returns"].mean()

        return portfolio_by_year
