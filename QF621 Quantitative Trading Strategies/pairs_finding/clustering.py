import polars as pl
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn import metrics
from sklearn.cluster import KMeans, AgglomerativeClustering, AffinityPropagation, DBSCAN

from utils.clustering_methods import Clustering_methods


class Clustering:
    """
    A class to perform clustering using KMeans, Agglomerative Clustering (AGNES), or DBSCAN.

    Attributes
    ----------
    df : pl.DataFrame
        The input dataframe to be clustered.
    reduction_threshold : float
        The silhouette score reduction threshold to decide the optimal number of clusters.
    stats : pl.DataFrame
        A dataframe containing computed statistics (mean, volatility, etc.).
    scaler : np.ndarray
        The standardized data after applying scaling to `stats`.
    cluster_pairs : dict
        A dictionary holding cluster labels and associated tickers.

    Methods
    -------
    compute_stats() -> pl.DataFrame
        Computes the statistical features of the dataframe, including percentage changes.
    scaling() -> np.ndarray
        Scales the statistical features using StandardScaler.
    group_pairs(labels: np.ndarray) -> None
        Groups tickers by cluster labels.
    evaluate(silhouette_score: list) -> int
        Evaluates the clustering results based on silhouette score reduction.
    kmeans_clustering(min_clusters=5, max_clusters=20) -> None
        Performs KMeans clustering and groups tickers based on the best cluster number.
    agnes_clustering(min_clusters=5, max_clusters=20) -> np.ndarray
        Performs Agglomerative Clustering (AGNES) and returns the cluster labels.
    dbscan_clustering(eps_values=[0.3, 0.5, 0.7], min_samples_values=[5, 10, 15]) -> np.ndarray
        Performs DBSCAN clustering and returns the cluster labels.
    select_clustering_method(method: str, **kwargs) -> np.ndarray
        Selects and applies the appropriate clustering method based on user input.
    """

    def __init__(self, df: pl.DataFrame, reduction_threshold: float = 10.0):
        """
        Initializes the Clustering object with the dataframe and reduction threshold.

        Parameters
        ----------
        df : pl.DataFrame
            The dataframe containing the data to be clustered.
        reduction_threshold : float, optional
            The silhouette score reduction threshold for optimal clusters, default is 10.
        """
        self.df = df
        self.reduction_threshold = reduction_threshold
        self.stats = self.compute_stats()
        self.scaler = self.scaling()
        self.cluster_pairs = {}
        self.random_state = 1111

    def compute_stats(self) -> pl.DataFrame:
        """
        Computes the median and volatility (standard deviation) of percentage changes for each column.

        Returns
        -------
        pl.DataFrame
            A DataFrame with ticker symbols and their corresponding median returns and volatility.
        """
        df = self.df.select([i for i in self.df.columns if i not in ["date", "time"]])
        returns = df.with_columns(pl.all().log().diff())

        return (
            df.with_columns(pl.all().log().diff())
            .median()
            .transpose(include_header=True, header_name="ticker", column_names=["ret"])
            .join(
                returns.with_columns(pl.all().std())
                .median()
                .transpose(
                    include_header=True, header_name="ticker", column_names=["vol"]
                ),
                how="inner",
                left_on="ticker",
                right_on="ticker",
            )
            .join(
                returns.with_columns(pl.all().skew())
                .median()
                .transpose(
                    include_header=True, header_name="ticker", column_names=["skew"]
                ),
                how="inner",
                left_on="ticker",
                right_on="ticker",
            )
            .join(
                returns.with_columns(pl.all().kurtosis())
                .median()
                .transpose(
                    include_header=True, header_name="ticker", column_names=["kurt"]
                ),
                how="inner",
                left_on="ticker",
                right_on="ticker",
            )
            .fill_nan(0)
            .fill_null(0)
        )

    def scaling(self) -> np.ndarray:
        """
        Scales the statistical data using StandardScaler from scikit-learn.

        Returns
        -------
        np.ndarray
            The scaled statistical features as a numpy array.
        """
        scaler = StandardScaler().fit_transform(self.stats.drop("ticker").to_numpy())

        return scaler

    def group_pairs(self, labels: np.ndarray) -> None:
        """
        Groups tickers by their cluster labels.

        Parameters
        ----------
        labels : np.ndarray
            The cluster labels assigned by the clustering algorithm.
        """
        self.cluster_pairs = {}
        for i in range(len(labels)):
            if labels[i] not in self.cluster_pairs.keys():
                self.cluster_pairs[labels[i]] = []

            self.cluster_pairs[labels[i]].append(self.stats["ticker"][i])

    def evaluate(self, silhouette_score: list) -> int:
        """
        Evaluates silhouette score and returns the optimal cluster index.

        Parameters
        ----------
        silhouette_score : list
            A list containing silhouette scores for different cluster sizes.

        Returns
        -------
        int
            The optimal cluster index.
        """
        return np.argmax(silhouette_score)

    def kmeans_clustering(self, min_clusters: int = 5, max_clusters: int = 20) -> None:
        """
        Performs KMeans clustering and groups tickers based on the optimal number of clusters.

        Parameters
        ----------
        min_clusters : int, optional
            The minimum number of clusters to start testing for, default is 5.
        max_clusters : int, optional
            The maximum number of clusters to test for, default is 20.
        """
        silhouette_score = []

        for k in range(min_clusters, max_clusters):
            kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
            kmeans.fit(self.scaler)
            silhouette_score.append(
                metrics.silhouette_score(
                    self.scaler, kmeans.labels_, random_state=self.random_state
                )
            )
        n = self.evaluate(silhouette_score=silhouette_score) + min_clusters
        kmeans = KMeans(n_clusters=n, random_state=self.random_state, n_init=10)
        kmeans.fit(self.scaler)

        self.group_pairs(kmeans.labels_)

    def agnes_clustering(self, min_clusters: int = 5, max_clusters: int = 20) -> None:
        """
        Perform Agglomerative Hierarchical clustering (AGNES) and selects the optimal number of clusters based on silhouette score.

        Parameters
        ----------
        min_clusters : int, optional
            The minimum number of clusters to start testing for. Default is 5.
        max_clusters : int, optional
            The maximum number of clusters to test for. Default is 20.

        Returns
        -------
        np.ndarray
            The final cluster labels after AGNES clustering.
        """
        silhouette_score = []

        for k in range(min_clusters, max_clusters):
            agnes = AgglomerativeClustering(n_clusters=k, linkage="average")
            agnes.fit(self.scaler)
            silhouette_score.append(
                metrics.silhouette_score(
                    self.scaler, agnes.labels_, random_state=self.random_state
                )
            )

        # Choose the best number of clusters
        n = self.evaluate(silhouette_score=silhouette_score) + min_clusters
        agnes = AgglomerativeClustering(n_clusters=n)
        agnes.fit(self.scaler)

        self.group_pairs(agnes.labels_)

    def dbscan_clustering(
        self, eps_values: list = [0.3, 0.5, 0.7], min_samples_values: list = [5, 10, 15]
    ) -> None:
        """
        Perform DBSCAN clustering and selects the optimal `eps` and `min_samples` based on silhouette score.

        Parameters
        ----------
        eps_values : list of float, optional
            The list of epsilon values to test for DBSCAN. Default is [0.3, 0.5, 0.7].
        min_samples_values : list of int, optional
            The list of `min_samples` values to test for DBSCAN. Default is [5, 10, 15].

        Returns
        -------
        np.ndarray
            The final cluster labels after DBSCAN clustering.
        """
        best_silhouette_score = -1
        best_dbscan = None

        # Testing different eps and min_samples values
        for eps in eps_values:
            for min_samples in min_samples_values:
                dbscan = DBSCAN(eps=eps, min_samples=min_samples)
                dbscan.fit(self.scaler)

                # Only compute silhouette score if there are more than one cluster
                if len(set(dbscan.labels_)) > 1:
                    score = metrics.silhouette_score(self.scaler, dbscan.labels_)
                    if score > best_silhouette_score:
                        best_silhouette_score = score
                        best_dbscan = dbscan

        if best_dbscan is not None:
            self.group_pairs(best_dbscan.labels_)
            if -1 in self.cluster_pairs:  # -1 is noise in dbscan so remove
                self.cluster_pairs.pop(-1)
        else:
            raise ValueError("no best dbscan")

    def affinity_propagation_clustering(
        self, damping: float = 0.9, max_iter: int = 200, convergence_iter: int = 15
    ) -> None:
        """
        Perform Affinity Propagation clustering and select the optimal clusters based on the provided parameters.

        Parameters
        ----------
        damping : float, optional, default=0.9
            Damping factor to avoid numerical oscillations. Between 0.5 and 1.
        preference : array-like of shape (n_samples,), optional, default=None
            Preference values for each point. Higher values will result in more clusters.
        max_iter : int, optional, default=200
            The maximum number of iterations.
        convergence_iter : int, optional, default=15
            The number of iterations with no improvement in the clustering that triggers convergence.

        Returns
        -------
        np.ndarray
            The final cluster labels after Affinity Propagation.
        """
        affinity = AffinityPropagation(
            damping=damping,
            max_iter=max_iter,
            convergence_iter=convergence_iter,
            random_state=self.random_state,
        )
        affinity.fit(self.scaler)

        # Get the cluster labels
        labels = affinity.labels_
        self.group_pairs(labels)

    def run_clustering(self, method: str, **kwargs):
        """
        Selects the clustering method to apply based on user input.

        Parameters
        ----------
        method : str
            The clustering method to use. Can be "kmeans", "agnes", or "dbscan".
        kwargs : keyword arguments
            Additional parameters specific to the selected clustering method.

        Returns
        -------
        np.ndarray
            The final cluster labels after applying the selected clustering method.

        Raises
        ------
        ValueError
            If the provided method is not one of "kmeans", "agnes", or "dbscan".
        """
        if method == Clustering_methods.kmeans:
            return self.kmeans_clustering(**kwargs)
        elif method == Clustering_methods.agnes:
            return self.agnes_clustering(**kwargs)
        elif method == Clustering_methods.dbscan:
            return self.dbscan_clustering(**kwargs)
        elif method == Clustering_methods.dbscan:
            return self.affinity_propagation_clustering(**kwargs)
        else:
            raise ValueError(
                "Invalid method. Choose from 'kmeans', 'agnes', or 'dbscan'."
            )
