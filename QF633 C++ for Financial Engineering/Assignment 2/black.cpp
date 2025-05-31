// BlackScholes.cpp
#include "black.h"
#include <cmath>

// Constructor implementation
BlackScholes::BlackScholes(
	double notional,
	double S,
	double K,
	double r,
	double sigma,
	double T,
	const bool& isCall
) {
	this->notional = notional;
	this->S = S;
	this->K = K;
	this->r = r;
	this->sigma = sigma;
	this->T = T;
	this->isCall = isCall;
}

const double& BlackScholes::d1() {
	return (log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt(T));
}

const double& BlackScholes::d2() {
	return d1() - sigma * sqrt(T);
}

// Call option price based on the Black-Scholes formula
double BlackScholes::price() {
	// N(d1) and N(d2) are the cumulative distribution function values for a standard normal distribution
	double d1_val = d1();
	double d2_val = d2();

	double N_d1, N_d2;

	if (isCall) {
		N_d1 = 0.5 * (1 + erf(d1_val / sqrt(2)));  // Using the error function for N(d1)
		N_d2 = 0.5 * (1 + erf(d2_val / sqrt(2)));  // Using the error function for N(d2)

		return S * N_d1 - K * exp(-r * T) * N_d2;
	}
	else {
		N_d1 = 0.5 * (1 + erf(-d1_val / sqrt(2)));  // N(-d1)
		N_d2 = 0.5 * (1 + erf(-d2_val / sqrt(2)));  // N(-d2)

		return K * exp(-r * T) * N_d2 - S * N_d1;
	}
}

double BlackScholes::pv() {
	return notional * price();
}

