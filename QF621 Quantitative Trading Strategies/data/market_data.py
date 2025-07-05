import datetime
import polars as pl
import numpy as np
from typing import List, Optional
from utils.market_time import market_hours


class market_data:
    """
    A class for managing market data, including reading from parquet files,
    preparing time-series data, and processing market timings for different sessions.

    Attributes:
    ----------
    file_path : str
        Path to the directory where the parquet files are stored.
    df : pl.LazyFrame | None
        Polars DataFrame containing market data.
    market_timing : dict
        Dictionary containing market timings for both 'daylight' and 'normal' sessions.
    times : dict
        Dictionary storing lists of times for 'daylight' and 'normal' sessions.
    full_date_time : pl.DataFrame | None
        DataFrame containing the full date and time information after processing.
    """

    def __init__(self, file_path: str):
        """
        Initializes the market_data object by setting the file path and preparing market session times.

        Parameters:
        ----------
        file_path : str
            Path to the directory where the parquet files are stored.
        """

        self.file_path = file_path
        self.pq_scanner = pl.scan_parquet(file_path, rechunk=True)
        self.df = None

        self.market_timing = {
            market_hours.DAYLIGHT: {
                market_hours.PRE: datetime.time(8, 0, 0),  # 4:00 AM ET
                market_hours.MARKET_OPEN: datetime.time(13, 30, 0),  # 9:30 AM ET
                market_hours.MARKET_CLOSE: datetime.time(20, 0, 0),  # 4:00 PM ET
                market_hours.POST: datetime.time(
                    0, 0, 0
                ),  # 8:00 PM ET (00:00 UTC next day)
            },
            market_hours.NORMAL: {
                market_hours.PRE: datetime.time(9, 0, 0),  # 4:00 AM ET
                market_hours.MARKET_OPEN: datetime.time(14, 30, 0),  # 9:30 AM ET
                market_hours.MARKET_CLOSE: datetime.time(21, 0, 0),  # 4:00 PM ET
                market_hours.POST: datetime.time(
                    1, 0, 0
                ),  # 8:00 PM ET (01:00 UTC next day)
            },
        }

        self.times = {market_hours.DAYLIGHT: [], market_hours.NORMAL: []}

        start = datetime.datetime.combine(datetime.date.today(), datetime.time(8, 0, 0))
        end = datetime.datetime.combine(datetime.date.today(), datetime.time(23, 59, 0))
        daylight_start = datetime.time(9, 0, 0)

        current = start
        while current <= end:
            time_only = current.time()
            self.times[market_hours.NORMAL].append(time_only)
            if time_only >= daylight_start:
                self.times[market_hours.DAYLIGHT].append(time_only)
            current += datetime.timedelta(minutes=1)

        self.times[market_hours.DAYLIGHT] = pl.LazyFrame(
            {"time": self.times[market_hours.DAYLIGHT]}
        )
        self.times[market_hours.NORMAL] = pl.LazyFrame(
            {"time": self.times[market_hours.NORMAL]}
        )

        self.full_date_time = None

        self.dst_dates = {
            2014: {"start": "2014-03-09", "end": "2014-11-02"},
            2015: {"start": "2015-03-08", "end": "2015-11-01"},
            2016: {"start": "2016-03-13", "end": "2016-11-06"},
            2017: {"start": "2017-03-12", "end": "2017-11-05"},
            2018: {"start": "2018-03-11", "end": "2018-11-04"},
            2019: {"start": "2019-03-10", "end": "2019-11-03"},
            2020: {"start": "2020-03-08", "end": "2020-11-01"},
            2021: {"start": "2021-03-14", "end": "2021-11-07"},
            2022: {"start": "2022-03-13", "end": "2022-11-06"},
            2023: {"start": "2023-03-12", "end": "2023-11-05"},
            2024: {"start": "2024-03-10", "end": "2024-11-03"},
            2025: {"start": "2025-03-09", "end": "2025-11-02"},
            2026: {"start": "2026-03-08", "end": "2026-11-01"},
            2027: {"start": "2027-03-14", "end": "2027-11-07"},
            2028: {"start": "2028-03-12", "end": "2028-11-05"},
            2029: {"start": "2029-03-11", "end": "2029-11-04"},
            2030: {"start": "2030-03-10", "end": "2030-11-03"},
            2031: {"start": "2031-03-09", "end": "2031-11-02"},
            2032: {"start": "2032-03-14", "end": "2032-11-07"},
            2033: {"start": "2033-03-13", "end": "2033-11-06"},
        }

    def read(self, cons: List[str], start: str, end: str) -> bool:
        """
        Reads market data from parquet files, filters by date range, and prepares the final DataFrame.

        Parameters:
        ----------
        cons : List[str]
            A list of symbols to filter the market data for.
        start : str
            Start date of the data in 'YYYY-MM-DD' format.
        end : str
            End date of the data in 'YYYY-MM-DD' format.

        Returns:
        -------
        bool
            True if read successfully
        """
        pl_start = pl.lit(start).str.strptime(pl.Date, "%Y-%m-%d")
        pl_end = pl.lit(end).str.strptime(pl.Date, "%Y-%m-%d")

        self.df = self.pq_scanner.select(
            [
                "t",
                "close",
                "symbol",
            ]
        ).with_columns(date=pl.col("t").dt.date(), time=pl.col("t").dt.time())

        self.df = (
            self.df.filter(
                (
                    pl.col("date").is_between(
                        lower_bound=pl_start
                        - pl.duration(
                            days=5
                        ),  # filter few days behind to get the ffill price
                        upper_bound=pl_end,
                    )
                    & (pl.col("symbol").is_in(cons))
                )
            )
            .collect(streaming=True)
            .pivot(on="symbol", index=["date", "time"], values="close")
            .sort(by=["date", "time"])
            .with_columns(
                year=pl.col("date").dt.year(),
                is_dst=pl.lit(0).cast(pl.Int16),
            )
            .lazy()
        )

        for year, dates in self.dst_dates.items():
            self.df = self.df.with_columns(
                pl.when(
                    (pl.col("year") == year)
                    & (
                        pl.col("date").is_between(
                            pl.lit(dates["start"]).str.strptime(pl.Date, "%Y-%m-%d"),
                            pl.lit(dates["end"]).str.strptime(pl.Date, "%Y-%m-%d"),
                        )
                    )
                )
                .then(1)
                .otherwise(pl.col("is_dst"))
                .alias("is_dst")
            )

        self.prep_time()

        self.df = (
            self.full_date_time.join(
                self.df, how="left", left_on=["date", "time"], right_on=["date", "time"]
            )
            .fill_null(strategy="forward")
            .filter(pl.col("date") >= pl_start)
            .drop(["year"])
        ).collect()

        return True

    def filter(self, resample_freq, hours):
        df = self.filter_hours(hours=hours)
        df = self.resample_df(df=df, resample_freq=resample_freq)
        remove_rows = (
            df.group_by("date", maintain_order=True)
            .agg(pl.all().pct_change().fill_null(0).sum())
            .filter(pl.all_horizontal(pl.all().exclude(["date", "time"]) == 0))
        )["date"].unique()

        return df.filter(~pl.col("date").is_in(remove_rows))

    def resample_df(
        self, df: pl.DataFrame = None, resample_freq: Optional[str] = None
    ) -> pl.DataFrame:
        """
        Resample the DataFrame (`self.df`) based on the specified frequency.

        Parameters
        ----------
        df : pl.DataFrame, optional
            DataFrame for filtering, if None, defaults to member variable
        resample_freq : str, optional
            The frequency to which the DataFrame should be resampled.
            If `None`, the DataFrame will not be resampled and the original DataFrame will be returned.
            Example frequencies include:
            - '1H' for hourly resampling
            - '30m' for 30-minute resampling
            - '15m' for 15-minute resampling
            - 'D' for daily resampling

        Returns
        -------
        pl.DataFrame
            A DataFrame with the time column adjusted to the new frequency.

        Raises
        ------
        ValueError
            If an invalid `resample_freq` is provided.

        Example
        -------
        # Resample the DataFrame to a frequency of 30 minutes
        resampled_df = market_data.resample_df("30m")

        # Display the resampled DataFrame
        print(resampled_df)
        """
        if df is None:
            df = self.df
        if resample_freq is not None:
            resampled_df = (
                df.with_columns(
                    pl.col("time").dt.to_string().str.to_datetime("%H:%M:%S")
                )
                .upsample(
                    time_column="time",
                    every=resample_freq,
                    group_by="date",
                    maintain_order=True,
                )
                .with_columns(pl.col("time").dt.time())
            )

            return resampled_df
        return df

    def filter_hours(
        self, df: pl.DataFrame = None, hours: market_hours = market_hours.MARKET
    ) -> pl.DataFrame:
        """
        Filter the DataFrame (`self.df`) based on the specified market hours.

        Parameters
        ----------
        df : pl.DataFrame, optional
            DataFrame for filtering, if None, defaults to member variable
        hours : str, optional
            Defines the time period for filtering:
            - 'MARKET' (default) : Filters data during normal market hours.
            - 'PRE' : Filters data during pre-market hours (before market open).
            - 'POST' : Filters data during post-market hours (after market close).

        Returns
        -------
        pl.DataFrame
            A filtered DataFrame containing only the rows where the `time` is within the
            specified market range based on the `min_time` column.

        Raises
        ------
        ValueError
            If the `hours` parameter is not one of 'MARKET', 'PRE', or 'POST'.
        """
        if df is None:
            df = self.df
        if hours == market_hours.MARKET:
            filtered_df = df.filter(
                (
                    pl.col("time")
                    >= pl.when(
                        # if normal then filter based on normal, if daylight then filter based on daylight
                        pl.col("is_dst") == 0
                    )
                    .then(
                        pl.lit(
                            self.market_timing[market_hours.NORMAL][
                                market_hours.MARKET_OPEN
                            ]
                        )
                    )
                    .otherwise(
                        pl.lit(
                            self.market_timing[market_hours.DAYLIGHT][
                                market_hours.MARKET_OPEN
                            ]
                        )
                    )
                )
                & (
                    pl.col("time")
                    <= pl.when(pl.col("is_dst") == 0)
                    .then(
                        pl.lit(
                            self.market_timing[market_hours.NORMAL][
                                market_hours.MARKET_CLOSE
                            ]
                        )
                    )
                    .otherwise(
                        pl.lit(
                            self.market_timing[market_hours.DAYLIGHT][
                                market_hours.MARKET_CLOSE
                            ]
                        )
                    )
                )
            )

        elif hours == market_hours.PRE:
            filtered_df = df.filter(
                (
                    pl.col("time")
                    <= pl.when(pl.col("is_dst") == 0)
                    .then(
                        pl.lit(
                            self.market_timing[market_hours.NORMAL][
                                market_hours.MARKET_OPEN
                            ]
                        )
                    )
                    .otherwise(
                        pl.lit(
                            self.market_timing[market_hours.DAYLIGHT][
                                market_hours.MARKET_OPEN
                            ]
                        )
                    )
                )
            )

        elif hours == market_hours.POST:
            filtered_df = df.filter(
                (
                    pl.col("time")
                    >= pl.when(pl.col("is_dst") == 0)
                    .then(
                        pl.lit(
                            self.market_timing[market_hours.NORMAL][
                                market_hours.MARKET_CLOSE
                            ]
                        )
                    )
                    .otherwise(
                        pl.lit(
                            self.market_timing[market_hours.DAYLIGHT][
                                market_hours.MARKET_CLOSE
                            ]
                        )
                    )
                )
            )
        else:
            filtered_df = df

        return filtered_df.drop("is_dst")

    def prep_time(self) -> None:
        """
        Prepares the date-time structure by computing the minimum and maximum time for each day,
        and joining with the 'daylight' and 'normal' session times.

        This method updates the `self.full_date_time` attribute with the full date-time information.
        """
        daylight_days = self.df.filter(pl.col("is_dst") == 1).select("date").unique()
        daylight_days = daylight_days.join(
            self.times[market_hours.DAYLIGHT], how="cross"
        )

        normal_days = self.df.filter(pl.col("is_dst") == 0).select("date").unique()
        normal_days = normal_days.join(self.times[market_hours.NORMAL], how="cross")

        self.full_date_time = pl.concat(
            [daylight_days, normal_days], how="vertical"
        ).sort(by=["date", "time"])
