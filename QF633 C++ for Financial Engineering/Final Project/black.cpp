#include "black.h"


double Black::Payoff(double marketPrice) const {
	double expiry = (expiryDate - today) / 365.0;
	// N(d1) and N(d2) are the cumulative distribution function values for a standard normal distribution
	double d1_val = (log(marketPrice / strike) + (rate + 0.5 * vol * vol) * expiry) / (vol * sqrt(expiry));
	double d2_val = d1_val - vol * sqrt(expiry);

	double N_d1, N_d2;

	double payoff;

	if (isCall) {
		N_d1 = 0.5 * (1 + erf(d1_val / sqrt(2)));  // Using the error function for N(d1)
		N_d2 = 0.5 * (1 + erf(d2_val / sqrt(2)));  // Using the error function for N(d2)

		payoff = notional * (marketPrice * N_d1 - strike * exp(-rate * expiry) * N_d2);
	}
	else {
		N_d1 = 0.5 * (1 + erf(-d1_val / sqrt(2)));  // N(-d1)
		N_d2 = 0.5 * (1 + erf(-d2_val / sqrt(2)));  // N(-d2)

		payoff = notional * (strike * exp(-rate * expiry) * N_d2 - marketPrice * N_d1);
	}

	return direction == "long" ? payoff : -payoff;
};

double Black::Pv(const Market& mkt) const {
	double expiry = (expiryDate - today) / 365.0;
	double marketPrice = mkt.getstockPrice(underlying);
	double df = mkt.getCurve(curvename)->getDf(expiryDate, today);
	double r = mkt.getCurve(curvename)->getRate(expiryDate);
	double vol = mkt.getVolCurve(volname)->getVol(expiryDate);

	// N(d1) and N(d2) are the cumulative distribution function values for a standard normal distribution
	double d1_val = (log(marketPrice / strike) + (r + 0.5 * vol * vol) * expiry) / (vol * sqrt(expiry));
	double d2_val = d1_val - vol * sqrt(expiry);

	double N_d1, N_d2;

	double payoff;

	if (isCall) {
		N_d1 = 0.5 * (1 + erf(d1_val / sqrt(2)));  // Using the error function for N(d1)
		N_d2 = 0.5 * (1 + erf(d2_val / sqrt(2)));  // Using the error function for N(d2)

		payoff = notional * (marketPrice * N_d1 - strike * df * N_d2);
	}
	else {
		N_d1 = 0.5 * (1 + erf(-d1_val / sqrt(2)));  // N(-d1)
		N_d2 = 0.5 * (1 + erf(-d2_val / sqrt(2)));  // N(-d2)

		payoff = notional * (strike * df * N_d2 - marketPrice * N_d1);
	}

	return direction == "long" ? payoff : -payoff;
}