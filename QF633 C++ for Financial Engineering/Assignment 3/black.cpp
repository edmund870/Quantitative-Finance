#include <cmath>
#include "black.h"

double BlackScholes(double notional, double strike, double expiry, double spot, double vol, double rate, bool isCall)
{
	// N(d1) and N(d2) are the cumulative distribution function values for a standard normal distribution
	double d1_val = (log(spot / strike) + (rate + 0.5 * vol * vol) * expiry) / (vol * sqrt(expiry));
	double d2_val = d1_val - vol * sqrt(expiry);

	double N_d1, N_d2;

	if (isCall) {
		N_d1 = 0.5 * (1 + erf(d1_val / sqrt(2)));  // Using the error function for N(d1)
		N_d2 = 0.5 * (1 + erf(d2_val / sqrt(2)));  // Using the error function for N(d2)

		return notional * (spot * N_d1 - strike * exp(-rate * expiry) * N_d2);
	}
	else {
		N_d1 = 0.5 * (1 + erf(-d1_val / sqrt(2)));  // N(-d1)
		N_d2 = 0.5 * (1 + erf(-d2_val / sqrt(2)));  // N(-d2)

		return notional * (strike * exp(-rate * expiry) * N_d2 - spot * N_d1);
	}
};