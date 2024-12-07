import polars as pl


class hedging:
    def __init__(
        self,
        hedge_date: str,
        holding_period: int,
        options: pl.DataFrame,
        min_dte: int,
        close: float,
    ) -> None:
        """
        Hedging class

        Parameters
        ----------
        hedge_date : str
            Date of hedging
        holding_period : int
            Holding period total days (include non-trading days)
        options : pl.DataFrame
            Options chain
        min_dte : int
            Minimum days to expiry
        close : float
            Price of underlying on hedge date
        """

        self.hedge_date = pl.lit(hedge_date).str.strptime(pl.Date, "%Y-%m-%d")
        self.holding_period = holding_period
        self.options = options
        self.min_dte = min_dte
        self.close = close

    def get_strike(self, option_chain: pl.DataFrame, price: float) -> int:
        """
        Computes closest strike price

        Parameters
        ----------
        option_chain : pl.DataFrame
            filtered day options chain
        price : float
            price to get closest strike

        Returns
        -------
        int
            strike price
        """
        strike = (
            option_chain.with_columns((pl.col("strike") - price).abs().alias("diff"))
            .sort("diff", descending=False)
            .select("strike")[0]
            .item()
        )

        return strike

    def get_dte(self, option_chain: pl.DataFrame, strike: int) -> int:
        """
        Computes closest day to expiry to `min_dte` for given strike price

        Parameters
        ----------
        option_chain : pl.DataFrame
            filtered day options chain
        strike : int
            strike price

        Returns
        -------
        int
            days to expiry
        """
        dte = (
            option_chain.filter(pl.col("strike") == strike)
            .with_columns((pl.col("days_to_expiry") - self.min_dte).abs().alias("diff"))
            .sort("diff", descending=False)
            .select("days_to_expiry")[0]
            .item()
        )

        return dte

    def get_symbol(self, option_chain: pl.DataFrame, strike: int, dte: int) -> str:
        """_summary_

        Parameters
        ----------
        option_chain : pl.DataFrame
            filtered day options chain
        strike : int
            strike price
        dte : int
            days to expiry

        Returns
        -------
        str
            Option symbol
        """
        return option_chain.filter(
            pl.col("strike") == strike, pl.col("days_to_expiry") == dte
        ).select("symbol")[0]

    def option_value(self, symbol: str) -> pl.DataFrame:
        """
        Get option value of desired symbol

        Parameters
        ----------
        symbol : str
            symbol for option

        Returns
        -------
        pl.DataFrame
            option value over holding period
        """
        return self.options.filter(
            pl.col("date") >= self.hedge_date,
            pl.col("symbol") == symbol,
        )[ : self.holding_period]

    def buy_put(self) -> pl.DataFrame:
        """
        Long Put

        Returns
        -------
        pl.DataFrame
            Daily value of puts
        """
        day_option_chain = self.options.filter(
            pl.col("date") == self.hedge_date,
            pl.col("days_to_expiry") > self.min_dte,
            pl.col("cp_flag") == "P",
        )

        strike = self.get_strike(option_chain=day_option_chain, price=self.close)

        dte = self.get_dte(option_chain=day_option_chain, strike=strike)

        symbol = self.get_symbol(option_chain=day_option_chain, strike=strike, dte=dte)

        long_put = self.option_value(symbol=symbol)

        daily_value = (
            long_put.select("date", "strike", "days_to_expiry", "best_bid")
            .with_columns(pl.col("best_bid") * 100)
            .rename({"best_bid": "hedge_value"})
        )

        return daily_value

    def short_call(self) -> pl.DataFrame:
        """
        Short Call

        Returns
        -------
        pl.DataFrame
            Daily value of short call
        """
        day_option_chain = self.options.filter(
            pl.col("date") == self.hedge_date,
            pl.col("days_to_expiry") > self.min_dte,
            pl.col("cp_flag") == "C",
        )

        strike = self.get_strike(option_chain=day_option_chain, price=self.close)

        dte = self.get_dte(option_chain=day_option_chain, strike=strike)

        symbol = self.get_symbol(option_chain=day_option_chain, strike=strike, dte=dte)

        short_call = self.option_value(symbol=symbol)

        daily_value = (
            short_call.select("date", "strike", "days_to_expiry", "best_offer")
            .with_columns(-pl.col("best_offer") * 100)
            .rename({"best_offer": "hedge_value"})
        )

        return daily_value

    def bear_put_spread(self, strike2: int) -> pl.DataFrame:
        """_summary_

        Parameters
        ----------
        strike2 : int
            option to short, strike2 < self.close

        Returns
        -------
        pl.DataFrame
            value of the legs of the bear put spread
        """
        day_option_chain = self.options.filter(
            pl.col("date") == self.hedge_date,
            pl.col("days_to_expiry") > self.min_dte,
            pl.col("cp_flag") == "P",
        )

        strike = self.get_strike(option_chain=day_option_chain, price=self.close)

        dte = self.get_dte(option_chain=day_option_chain, strike=strike)

        strike2 = self.get_strike(option_chain=day_option_chain, price=strike2)

        dte2 = self.get_dte(option_chain=day_option_chain, strike=strike2)

        symbol = self.get_symbol(option_chain=day_option_chain, strike=strike, dte=dte)

        symbol2 = self.get_symbol(
            option_chain=day_option_chain, strike=strike2, dte=dte2
        )

        long_put = (
            self.option_value(symbol=symbol)
            .select("date", "strike", "days_to_expiry", "best_bid")
            .rename({"strike": "long_strike", "days_to_expiry": "long_days_to_expiry"})
        )

        short_put = (
            self.option_value(symbol=symbol2)
            .select("date", "strike", "days_to_expiry", "best_offer")
            .rename(
                {"strike": "short_strike", "days_to_expiry": "short_days_to_expiry"}
            )
        )

        bear_put_values = long_put.join(
            short_put, how="left", left_on="date", right_on="date"
        )

        daily_value = bear_put_values.with_columns(
            -pl.col("best_offer") * 100,
            pl.col("best_bid") * 100,
            ((pl.col("best_bid") + pl.col("best_offer")) * 100).alias("hedge_value"),
        )

        return daily_value
