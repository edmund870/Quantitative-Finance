import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

plt.style.use("ggplot")

mpl.rcParams["axes.grid"] = True
mpl.rcParams["grid.color"] = "grey"
mpl.rcParams["grid.alpha"] = 0.25

mpl.rcParams["axes.facecolor"] = "white"

mpl.rcParams["legend.fontsize"] = 14


class plotting:
    def __init__(self, df: pd.DataFrame) -> None:
        """
        Plotting class

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to plot
        """
        self.df = df

    def signal(
        self, ticker: str, y: list[str], color: list[str], plot_type: str
    ) -> None:
        if not isinstance(y, list):
            raise AttributeError("Expected a list of y")
        if not any(v for v in y if v in self.df.columns):
            raise KeyError(f"{y} not in DataFrame")
        if plot_type not in self.df.columns:
            raise KeyError(f"Define {plot_type} first")
        if len(y) != len(color):
            raise ValueError("Length of `y` must be equal to the length of `color`")

        indicators = self.df[plot_type].unique()

        long = indicators[indicators > 0].item()
        short = indicators[indicators < 0].item()

        (self.df[y].plot(figsize=(16, 6), color=color))

        # BUY signal
        (
            plt.scatter(
                self.df.loc[self.df[plot_type] == long].index,
                self.df[self.df[plot_type] == long][y[0]],
                marker="^",
                s=100,
                color="green",
            )
        )

        # SELL signal
        (
            plt.scatter(
                self.df.loc[self.df[plot_type] == short].index,
                self.df[self.df[plot_type] == short][y[0]],
                marker="v",
                s=100,
                color="red",
            )
        )

        plt.title(f"{ticker} {plot_type}")
