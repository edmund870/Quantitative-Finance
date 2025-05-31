#ifndef BLACKSCHOLES_H
#define BLACKSCHOLES_H

class BlackScholes
{
public:
	BlackScholes();

	BlackScholes(double notional, double S, double K, double r, double sigma, double T,const bool& isCall);

	double price();
	double pv();

private:
	double notional, S, K, sigma, r, T;
	bool isCall;

	const double& d1();
	const double& d2();
};

#endif
