import json
import wrds
import os
from typing import Optional, Dict


class get_cons:
    """
    A class to retrieve and store the constituent tickers of a specified ETF for quarter-end dates.

    Attributes
    ----------
    etf : str
        The ETF composite ticker symbol for which to fetch constituent tickers.
    cons : Optional[pd.DataFrame]
        DataFrame holding the ETF constituent data.
    out_file : str
        The file path for saving the constituent tickers by date in JSON format.
    """

    def __init__(self, etf: str):
        """
        Initializes the get_cons object with the ETF ticker and output file path.

        Parameters
        ----------
        etf : str
            The ETF composite ticker symbol (e.g., 'SPY', 'QQQ').
        """
        self.etf = etf
        self.cons = None
        self.out_file = f"{etf}_cons_by_date.json"

    def query_db(self) -> None:
        """
        Queries the WRDS database to fetch ETF constituent tickers for the specified ETF.
        Filters the data to only include quarter-end dates: March 31, June 30, September 30, and December 31.

        The query results are stored in the `self.cons` attribute as a DataFrame.
        """
        db = wrds.Connection()
        self.cons = db.raw_sql(
            f"""
            SELECT 
                as_of_date, 
                composite_ticker, 
                constituent_ticker, 
                weight
            FROM 
                etfg_constituents.constituents
            WHERE 
                composite_ticker = '{self.etf}'
            ORDER BY 
                as_of_date;

            """,
            date_cols=["as_of_date"],
        )

        self.cons = self.cons.groupby(
            ["as_of_date", "constituent_ticker"], as_index=False
        ).last()

    def output(self) -> None:
        """
        Saves the ETF constituent tickers grouped by date into a JSON file.

        The file will be named `<ETF>_cons_by_date.json` and stored in the current directory.

        The JSON file will have the following format:
        {
            "YYYY-MM-DD": [list_of_constituent_tickers]
        }
        """
        tickers_dictionary = (
            self.cons.groupby("as_of_date")["constituent_ticker"].apply(list).to_dict()
        )

        tickers_dictionary = {
            key.strftime("%Y-%m-%d"): value for key, value in tickers_dictionary.items()
        }

        with open(self.out_file, "w") as json_file:
            json.dump(tickers_dictionary, json_file, default=str)

    def run(self) -> None:
        """
        Executes the process of querying the database for ETF constituents and saving them to a JSON file.

        This method will:
        1. Query the database.
        2. Save the results to a JSON file.
        """
        self.query_db()
        self.output()

    def read(self) -> Optional[Dict[str, list]]:
        """
        Reads the JSON file containing the ETF constituent tickers by date.

        If the file exists, it returns the contents as a dictionary. If the file does not exist, it prints an error message.

        Returns
        -------
        Optional[Dict[str, list]]
            A dictionary where the keys are dates (in 'YYYY-MM-DD' format) and the values are lists of constituent tickers.
            Returns None if the file does not exist.
        """
        if not os.path.exists(f"./{self.out_file}"):
            print("no file, running query")
            self.run()

        with open(self.out_file, "r") as json_file:
            data = json.load(json_file)
            return data
