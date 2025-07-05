import numpy as np
from numba import prange, njit
from numba.typed import List
from pairs_finding.adf import ADF_Test
from typing import Dict, Optional, Tuple


class cointegration_pairs:
    """
    A class for identifying cointegrated pairs of assets based on the Augmented Dickey-Fuller (ADF) test.

    Attributes
    ----------
    tickers : List[str]
        List of asset tickers used for cointegration analysis.
    pairs : Dict[Tuple[str, str], float]
        Dictionary storing identified cointegrated pairs with their corresponding test statistic.
    p_val_cutoff : float
        The p-value threshold for cointegration significance (default is 0.05).
    cluster_pairs : Optional[List[List[str]]]
        List of clustered pairs to check for cointegration. If None, all pairs are checked.
    df_arr : np.ndarray
        Numpy array containing the asset price data (rows are assets, columns are time series).
    adf : ADF_Test
        An instance of the ADF_Test class used to perform Augmented Dickey-Fuller tests.
    """

    def __init__(
        self,
        df: np.ndarray,
        p_val_cutoff: float = 0.05,
        cluster_pairs: Optional[Dict[int, list[str]]] = None,
    ):
        """
        Initializes the cointegration_pairs object with asset price data and optional clustering.

        Parameters
        ----------
        df : np.ndarray
            Numpy array where rows represent assets and columns represent the time series of asset prices.
        p_val_cutoff : float, optional
            The p-value threshold for the cointegration test (default is 0.05).
        cluster_pairs : Optional[Dict[int, list[str]]], optional
            A dictionary where each key represents a cluster, and the value is a list of asset tickers in that cluster.
            If None, no clustering is performed (default is None).
        """
        self.pairs = {}

        if cluster_pairs is not None:
            self.cluster_pairs = list(cluster_pairs.values())
            nb_list = List()
            for lst in self.cluster_pairs:
                nb_list.append(lst)

            self.cluster_pairs = nb_list

            # make sure the order of tickers in col header is right
            flatten_list = [
                item for sublist in list(cluster_pairs.values()) for item in sublist
            ]
            self.df_arr = df.select(flatten_list).to_numpy().T
            self.tickers = flatten_list
        else:
            self.cluster_pairs = cluster_pairs
            self.df_arr = df.to_numpy().T
            self.tickers = list(df.columns)

        self.p_val_cutoff = p_val_cutoff
        self.adf = ADF_Test()

    def identify_pairs(self) -> None:
        """
        Identifies cointegrated asset pairs by comparing pairs of assets in the price data.

        This method updates the `self.pairs` dictionary with the identified pairs and their respective test statistics.
        """
        pairs = self._identify_pairs(
            tickers=self.tickers,
            df_arr=self.df_arr,
            adf=self.adf,
            coint=self.coint_test,
            p_val_cutoff=self.p_val_cutoff,
            cluster_pairs=self.cluster_pairs,
        )

        self.pairs = dict(pairs)
        self.sort_pairs()

    @staticmethod
    @njit
    def coint_test(x1: np.ndarray, x2: np.ndarray) -> np.ndarray:
        """
        Performs cointegration testing between two asset time series using the OLS method.

        Parameters
        ----------
        x1 : np.ndarray
            The first asset time series.
        x2 : np.ndarray
            The second asset time series.

        Returns
        -------
        np.ndarray
            The residuals from the cointegration test.
        """
        X = np.column_stack((np.ones(x1.shape[0]), x1))
        beta = np.linalg.inv(X.T @ X) @ X.T @ x2

        pred = X @ beta
        resid = x2 - pred
        return resid

    @staticmethod
    @njit(parallel=True)
    def _identify_pairs(
        tickers: list[str],
        df_arr: np.ndarray,
        adf: ADF_Test,
        coint: callable,
        p_val_cutoff: float,
        cluster_pairs: Optional[list[list[str]]],
    ) -> Dict[Tuple[str, str], float]:
        """
        Identifies cointegrated pairs from the price data and returns a dictionary of pairs and their test statistics.

        Parameters
        ----------
        tickers : list[str]
            A list of tickers for the assets.
        df_arr : np.ndarray
            The price data array, where rows represent assets and columns represent the time series.
        adf : ADF_Test
            The Augmented Dickey-Fuller test instance.
        coint : callable
            The cointegration test function.
        p_val_cutoff : float
            The p-value cutoff for cointegration significance.
        cluster_pairs : Optional[list[list[str]]]
            The list of asset clusters for identifying pairs. If None, all pairs are checked.

        Returns
        -------
        Dict[Tuple[str, str], float]
            A dictionary with pairs of asset tickers as keys and their cointegration test statistics as values.
        """
        pairs = {}

        if cluster_pairs is not None:
            start = 0
            n_clusters = len(cluster_pairs)
            for cluster in range(n_clusters):
                n_this_cluster = len(cluster_pairs[cluster])
                if n_this_cluster != 1:
                    for i in prange(n_this_cluster):
                        x1_arr = df_arr[start + i]
                        for j in range(i + 1, n_this_cluster):
                            x2_arr = df_arr[start + j]
                            if (
                                adf.ad_fuller(x1_arr)[1] > p_val_cutoff
                                and adf.ad_fuller(x2_arr)[1] > p_val_cutoff
                            ):
                                resid = coint(x1=x1_arr, x2=x2_arr)
                                t, pval = adf.ad_fuller(resid)
                                if pval <= p_val_cutoff:
                                    pairs[(tickers[start + i], tickers[start + j])] = t

                start += n_this_cluster
        else:
            n = len(tickers)
            for i in prange(n):
                x1_arr = df_arr[i]
                for j in range(i + 1, n + 1):
                    x2_arr = df_arr[j]
                    if (
                        adf.ad_fuller(x1_arr)[1] > p_val_cutoff
                        and adf.ad_fuller(x2_arr)[1] > p_val_cutoff
                    ):
                        resid = coint(x1=x1_arr, x2=x2_arr)
                        t, pval = adf.ad_fuller(resid)
                        if pval <= p_val_cutoff:
                            pairs[(tickers[i], tickers[j])] = t
        return pairs

    def sort_pairs(self):
        """
        Sorts cointegrated pairs based on their cointegration test statistic.
        """
        if len(self.pairs) > 0:
            if self.cluster_pairs is not None:
                self.cluster_sorted_pairs = {}
                self.cluster_pairs = list(self.cluster_pairs)
                for i in range(len((self.cluster_pairs))):
                    tickers = self.cluster_pairs[i]
                    pairs_with_t = []

                    for j in range(len(tickers)):
                        for k in range(j + 1, len(tickers)):
                            ticker_pair = (tickers[j], tickers[k])
                            ticker_pair2 = (tickers[k], tickers[j])

                            if ticker_pair in self.pairs.keys():
                                t_value = self.pairs[ticker_pair]
                                pairs_with_t.append((t_value, ticker_pair))
                            if ticker_pair2 in self.pairs.keys():
                                t_value = self.pairs[ticker_pair2]
                                pairs_with_t.append((t_value, ticker_pair2))

                    pairs_with_t.sort(key=lambda x: x[0])

                    self.cluster_sorted_pairs[i] = [
                        (pair, t_value) for t_value, pair in pairs_with_t
                    ]

            else:
                self.pairs = {
                    k: v
                    for k, v in sorted(
                        self.pairs.items(),
                        key=lambda item: item[1],
                    )
                }

    def get_top_pairs(self, n: int = 20) -> list[Tuple[str, str]]:
        """
        Retrieves the top N cointegrated pairs based on their cointegration test statistic.

        Parameters
        ----------
        n : int, optional
            The number of top pairs to retrieve (default is 20).

        Returns
        -------
        list[Tuple[str, str]]
            A list of the top N cointegrated pairs, sorted by their cointegration test statistic.
        """
        if len(self.pairs) > 0:
            if self.cluster_pairs is not None:
                return [
                    pair[0]
                    for sublist in self.cluster_sorted_pairs.values()
                    for pair in sublist[:n]
                ]
            else:
                return list(self.pairs.keys())[:n]
