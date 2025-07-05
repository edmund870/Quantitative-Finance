import numba
import numpy as np
import math
from typing import Optional, Tuple

spec = [
    ("tau_star_c", numba.float64[:]),
    ("tau_min_c", numba.float64[:]),
    ("tau_max_c", numba.float64[:]),
    ("tau_c_smallp", numba.float64[:, :]),
    ("tau_c_largep", numba.float64[:, :]),
]


@numba.experimental.jitclass(spec)
class ADF_Test:
    """
    A class for performing the Augmented Dickey-Fuller (ADF) test and calculating p-values
    for time series stationarity using pre-defined critical values for different sample sizes.

    Attributes
    ----------
    tau_star_c : np.ndarray
        Critical values for tau statistics at different levels.
    tau_min_c : np.ndarray
        Minimum critical values for tau statistics.
    tau_max_c : np.ndarray
        Maximum critical values for tau statistics.
    tau_c_smallp : np.ndarray
        Small sample size critical values for tau statistics for small p-values.
    tau_c_largep : np.ndarray
        Large sample size critical values for tau statistics for large p-values.
    """

    def __init__(self):
        """
        Initializes the ADF_Test object with predefined critical values for tau statistics.

        The values are based on the Augmented Dickey-Fuller test for different lag lengths.
        """
        self.tau_star_c = np.array(
            [-1.61, -2.62, -3.13, -3.47, -3.78, -3.93], dtype=np.float64
        )
        self.tau_min_c = np.array(
            [-18.83, -18.86, -23.48, -28.07, -25.96, -23.27], dtype=np.float64
        )
        self.tau_max_c = np.array([2.74, 0.92, 0.55, 0.61, 0.79, 1.0], dtype=np.float64)

        small_scaling = np.array([1.0, 1.0, 1e-2], dtype=np.float64)
        tau_c_smallp = np.array(
            [
                [2.1659, 1.4412, 3.8269],
                [2.92, 1.5012, 3.9796],
                [3.4699, 1.4856, 3.164],
                [3.9673, 1.4777, 2.6315],
                [4.5509, 1.5338, 2.9545],
                [5.1399, 1.6036, 3.4445],
            ],
            dtype=np.float64,
        )
        self.tau_c_smallp = tau_c_smallp * small_scaling

        large_scaling = np.array([1.0, 1e-1, 1e-1, 1e-2], dtype=np.float64)
        tau_c_largep = np.array(
            [
                [1.7339, 9.3202, -1.2745, -1.0368],
                [2.1945, 6.4695, -2.9198, -4.2377],
                [2.5893, 4.5168, -3.6529, -5.0074],
                [3.0387, 4.5452, -3.3666, -4.1921],
                [3.5049, 5.2098, -2.9158, -3.3468],
                [3.9489, 5.8933, -2.5359, -2.721],
            ],
            dtype=np.float64,
        )
        self.tau_c_largep = tau_c_largep * large_scaling

    def norm_cdf(self, x: float, mean: float = 0, std_dev: float = 1) -> float:
        """
        Computes the cumulative distribution function (CDF) of the standard normal distribution.

        Parameters
        ----------
        x : float
            The value at which the CDF is evaluated.
        mean : float, optional
            The mean of the distribution (default is 0).
        std_dev : float, optional
            The standard deviation of the distribution (default is 1).

        Returns
        -------
        float
            The CDF value for the given `x`.
        """
        return 0.5 * (1 + math.erf((x - mean) / (std_dev * math.sqrt(2))))

    def horner_eval(self, coeffs: np.ndarray, x: float) -> float:
        """
        Evaluates a polynomial using Horner's method.

        Parameters
        ----------
        coeffs : np.ndarray
            Coefficients of the polynomial, ordered from highest to lowest degree.
        x : float
            The point at which the polynomial is evaluated.

        Returns
        -------
        float
            The result of evaluating the polynomial at `x`.
        """
        result = 0.0
        for c in coeffs:
            result = result * x + c
        return result

    def mackinnonp(self, teststat: float, N: int = 1) -> float:
        """
        Computes the p-value based on the given test statistic using the MacKinnon p-value method.

        Parameters
        ----------
        teststat : float
            The test statistic to compute the p-value for.
        N : int, optional
            The number of lags used in the test (default is 1).

        Returns
        -------
        float
            The computed p-value.
        """
        maxstat = self.tau_max_c
        minstat = self.tau_min_c
        starstat = self.tau_star_c
        if teststat > maxstat[N - 1]:
            return 1.0
        elif teststat < minstat[N - 1]:
            return 0.0
        if teststat <= starstat[N - 1]:
            tau_coef = self.tau_c_smallp[N - 1]
        else:
            # Note: above is only for z stats
            tau_coef = self.tau_c_largep[N - 1]
        return self.norm_cdf(self.horner_eval(tau_coef[::-1], teststat))

    def narrow(
        self, input: np.ndarray, dim: int, start: int, length: int
    ) -> np.ndarray:
        """
        Extracts a subarray from the input array along the specified dimension.

        Parameters
        ----------
        input : np.ndarray
            The input array from which to extract the subarray.
        dim : int
            The dimension along which to slice (0 for rows, 1 for columns).
        start : int
            The starting index of the slice.
        length : int
            The length of the slice.

        Returns
        -------
        np.ndarray
            The sliced subarray.
        """
        if dim == 0:
            return input[start : start + length]
        # elif dim == 1:
        #     return input[:, start : start + length]

    def ad_fuller(
        self, series: np.ndarray, maxlag: Optional[int] = None
    ) -> Tuple[float, float]:
        """
        Performs the Augmented Dickey-Fuller (ADF) test on the given time series and returns
        the test statistic and p-value.

        Parameters
        ----------
        series : np.ndarray
            The time series data to perform the ADF test on.
        maxlag : int, optional
            The maximum lag to use for the ADF test (default is calculated automatically).

        Returns
        -------
        Tuple[float, float]
            A tuple containing the test statistic and the p-value.
        """
        """Get series and return the p-value and the t-stat of the coefficient"""
        if np.isnan(series).any() or np.isinf(series).any():
            return 1e6, 1e6
        if maxlag is None:
            n = int((len(series) - 1) ** (1.0 / 3))
        elif maxlag < 1:
            n = 1
        else:
            n = maxlag

        # Putting the X values on a Tensor with Double as type
        X = series

        # Generating the lagged tensor to calculate the difference
        X_1 = self.narrow(X, 0, 1, X.shape[0] - 1)

        # Re-sizing the x values to get the difference
        X_diff = self.narrow(X, 0, 0, X.shape[0] - 1)
        dX = X_1 - X_diff

        # Generating the lagged difference tensors
        # and concatenating the lagged tensors into a single one
        for i in range(1, n + 1):
            lagged_n = self.narrow(dX, 0, n - i, (dX.shape[0] - n))
            lagged_reshape = np.reshape(lagged_n, (lagged_n.shape[0], 1))
            if i == 1:
                lagged_tensors = lagged_reshape
            else:
                lagged_tensors = np.concatenate((lagged_tensors, lagged_reshape), 1)

        # Reshaping the X and the difference tensor
        # to match the dimension of the lagged ones
        X_match = self.narrow(X_diff, 0, 0, X_diff.shape[0] - n)
        dX = self.narrow(dX, 0, n, dX.shape[0] - n)
        dX = np.reshape(dX, (dX.shape[0], 1))

        # Concatenating the lagged tensors to the X one
        # and adding a column full of ones for the Linear Regression
        X_linreg = X_match.copy()
        X_linreg = np.concatenate(
            (np.reshape(X_linreg, (X_linreg.shape[0], 1)), lagged_tensors), 1
        )
        ones_columns = np.ones((X_linreg.shape[0], 1))
        X_ = np.concatenate((X_linreg, np.ones_like(ones_columns, dtype=np.float64)), 1)

        # Xb = y -> Xt.X.b = Xt.y -> b = (Xt.X)^-1.Xt.y
        if np.linalg.det(X_.T @ X_) != 0:
            coeff = np.linalg.inv(X_.T @ X_) @ X_.T @ dX

            std_error = self.get_std_error(X_, dX, coeff)
            coeff_std_err = self.get_coeff_std_error(X_, std_error, coeff)[0]
            t_stat = (coeff[0] / coeff_std_err).item()

            p_value = self.mackinnonp(t_stat, N=1)

            return t_stat, p_value
        else:
            return 0.0, 1.0

    def get_coeff_std_error(
        self, X: np.ndarray, std_error: float, p: np.ndarray
    ) -> list:
        """
        Calculates the standard error for each coefficient in the regression.

        This function computes the standard error for each coefficient by
        using the formula: sqrt(Var(beta) * (s^2)), where Var(beta) is
        the variance of the coefficient, and s^2 is the residual variance.

        Parameters
        ----------
        X : np.ndarray
            The matrix of independent variables (shape: [n_samples, n_features]).
        std_error : float
            The regression standard error (calculated in `get_std_error`).
        p : np.ndarray
            The regression coefficients (shape: [n_features,]).

        Returns
        -------
        list
            A list of standard errors for each coefficient.
        """
        std_coeff = []
        temp = np.linalg.inv(X.T @ X)
        for i in range(len(p)):
            s = temp[i][i] * (std_error**2)
            s = np.sqrt(s)
            std_coeff.append(s)
        return std_coeff

    def get_std_error(self, X: np.ndarray, label: np.ndarray, p: np.ndarray) -> float:
        """
        Calculates the standard error of the regression.

        This function computes the standard error of the regression (also known
        as the residual standard error), which is a measure of the variance of
        the residuals. It is calculated using the formula:
        sqrt(1/n * sum((y - y_pred)^2)) where y_pred is the predicted values
        and y is the observed values.

        Parameters
        ----------
        X : np.ndarray
            The matrix of independent variables (shape: [n_samples, n_features]).
        label : np.ndarray
            The observed dependent variable values (shape: [n_samples, 1]).
        p : np.ndarray
            The regression coefficients (shape: [n_features,]).

        Returns
        -------
        float
            The regression standard error.
        """
        std_error = 0
        y_new = X @ p
        std_error = np.sum((label[:, 0] - y_new[:, 0]) ** 2)
        return np.sqrt(std_error / X.shape[0])
