from typing import Optional

import polars as pl


class portfolio:
    def __init__(self, hedge_date: str, holding_value: pl.DataFrame) -> None:
        """
        Consolidate portfolio of holding and hedging

        Parameters
        ----------
        hedge_date : str
            Date of hedging
        holding_value : pl.DataFrame
            Value of underlying portfolio without hedging
        """

        self.hedge_date = hedge_date
        self.holding_value = holding_value

    def compute_portfolio(
        self, hedge_value: Optional[pl.DataFrame] = None
    ) -> pl.DataFrame:
        """
        Consolidate portfolio

        Parameters
        ----------
        hedge_value : Optional[pl.DataFrame], optional
            Value of hedging strategy holdings, by default None

        Returns
        -------
        pl.DataFrame
            portfolio comprising
            1. Underlying holdings vale
            2. Hedged holdings value
            3. Total portfolio value
            4. Total portfolio returns
        """
        holding = self.holding_value.filter(
            pl.col("Date") >= pl.lit(self.hedge_date).str.strptime(pl.Date, "%Y-%m-%d")
        )

        if hedge_value is not None:
            portfolio = (
                hedge_value.join(holding, how="left", left_on="date", right_on="Date")
                .with_columns(
                    # Net change in hedge and holdings
                    (pl.col("hedge_value").diff() + pl.col("Holding").diff()).alias(
                        "net_change"
                    ),
                    # Portfolio value
                    pl.when(pl.col("hedge_value") < 0)
                    .then(
                        # if short, hedge value is negative
                        (pl.col("Holding") - pl.col("hedge_value"))
                    )
                    .otherwise(
                        # if long
                        (pl.col("Holding") + pl.col("hedge_value"))
                    )
                    .alias("port_value"),
                )
                .with_columns(
                    pl.when(pl.col("net_change").is_null())
                    .then(pl.col("port_value"))
                    .otherwise(pl.col("net_change"))
                    .cum_sum()
                )
                .with_columns(pl.col("port_value").pct_change().alias("returns"))
            )
        else:
            portfolio = (
                holding.clone()
                .rename({"Holding": "port_value"})
                .with_columns(pl.col("port_value").pct_change().alias("returns"))
            )

        return portfolio
