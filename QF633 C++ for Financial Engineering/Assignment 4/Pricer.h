#ifndef _PRICER
#define _PRICER

#include <vector>
#include <cmath>

#include "Trade.h"
#include "TreeProduct.h"
#include "Market.h"

// pricer interface
class Pricer {
public:
	virtual double Price(const Market& mkt, Trade* trade);

private:
	virtual double PriceTree(const Market& mkt, const TreeProduct& trade) { return 0; };
};

class BinomialTreePricer : public Pricer
{
public:
	BinomialTreePricer(int N) {
		nTimeSteps = N;
		states.resize(N + 1);
	}
	double PriceTree(const Market& mkt, const TreeProduct& trade) override;

protected:
	virtual void ModelSetup(double S0, double sigma, double rate, double dt);
	virtual double GetSpot(int ti, int si) const { return currentSpot* std::pow(u, ti - si)* std::pow(d, si); };
	virtual inline double GetProbUp() const { return p; };
	virtual double GetProbDown() const { return 1 - p; };;

	int nTimeSteps;
	std::vector<double> states;
	double u; // up multiplicative
	double d; // down
	double p; // probability for up state
	double currentSpot; // current market spot price
};

class CRRBinomialTreePricer : public BinomialTreePricer
{
public:
	CRRBinomialTreePricer(int N) : BinomialTreePricer(N) {}

protected:
	void ModelSetup(double S0, double sigma, double rate, double dt) override;
	double GetSpot(int ti, int si) const override {
		return currentSpot * std::pow(u, ti - 2 * si);
	}
	// double GetProbUp() const { return p; }
	// double GetProbDown() const { return 1 - p; }
};

class JRRNBinomialTreePricer : public BinomialTreePricer
{
public:
	JRRNBinomialTreePricer(int N) : BinomialTreePricer(N) {}

protected:
	void ModelSetup(double S0, double sigma, double rate, double dt);

	//double GetSpot(int ti, int si) const
	//{
	//	return currentSpot * std::pow(u, ti - si) * std::pow(d, si);
	//}
	// double GetProbUp() const { return p; }
	// double GetProbDown() const { return 1 - p; }

};

#endif
