import math

import numpy as np
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
import plotly.io as pio
import polars as pl
from plotly.subplots import make_subplots

pio.templates.default = "plotly_dark"


class risk:
    def __init__(self, returns: list[pl.Series]) -> None:

        self.returns = [r.to_numpy() for r in returns]
        self.name = [r.name for r in returns]
        self.n = len(returns)
        self.var_dict = {}

    def compute_var(self, var_percentile: int) -> pl.DataFrame:

        for i in range(self.n):
            self.var_dict[self.name[i]] = np.percentile(
                self.returns[i], 100 - var_percentile
            )

        var_df = (
            pl.from_dict(self.var_dict)
            .transpose(include_header=True)
            .rename({"column": "strategy", "column_0": f"{var_percentile}_var"})
            .with_columns(
                pl.col(f"{var_percentile}_var") * np.sqrt(10)
            )
        )
        return var_df

    def visualize_returns(
        self, bins: int, title: str, n_rows: int, height: int, width: int
    ):

        n_rows = n_rows
        n_cols = math.ceil(self.n / n_rows)
        var_keys = list(self.var_dict.keys())
        lower = np.min([np.concatenate([i for i in self.returns])])
        upper = np.max([np.concatenate([i for i in self.returns])])

        fig = make_subplots(
            rows = n_rows, 
            cols = n_cols,
            shared_xaxes = True,
            vertical_spacing = 0.1,
            subplot_titles = self.name, 
        )

        for i in range(n_rows):
            for j in range(n_cols):
                index = i * n_cols + j
                if index < self.n:
                    fig.add_trace(
                        go.Histogram(
                            x=self.returns[index],
                            marker_color="#636EFA",
                            xbins=dict(start=lower, end=upper, size=bins),
                        ),
                        row=i + 1,
                        col=j + 1,
                    )

                    (
                        fig.update_traces(
                            marker=dict(line=dict(color="white", width=0.5))
                        )
                    )

                    fig.add_vline(
                        x=self.var_dict[var_keys[index]],
                        line_color="red",
                        annotation_text=f'VaR {"{:.2%}".format(self.var_dict[var_keys[index]])}',
                        row=i + 1,
                        col=j + 1,
                    )

                    fig.update_xaxes(
                        tickformat=".0%", showgrid=False, row=i + 1, col=j + 1
                    )

        fig.update_xaxes(range=[lower, upper])

        fig.update_layout(
            height=height, width=width, title=title, title_x=0.5, showlegend=False
        )

        distplot = ff.create_distplot(self.returns, self.name, show_hist=False)

        distplot.update_xaxes(
            tickformat=".0%",
        )

        distplot.update_layout(
            height=height,
            width=width,
            title=title,
            title_x=0.5,
        )
        
        # Show figures
        fig.show()
        distplot.show()
        
        # Save figures as images
        fig_path = "histogram_plot.png"
        distplot_path = "distribution_plot.png"
        pio.write_image(fig, fig_path)
        pio.write_image(distplot, distplot_path)
        
        print(f"Plots saved as '{fig_path}' and '{distplot_path}'")

        
