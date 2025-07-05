#include <cmath>
#include "Pricer.h"
#include "Bond.h"
#include "Swap.h"
#include "EuropeanTrade.h"
#include "AmericanTrade.h"
#include "black.h"


double Pricer::Price(const Market& mkt, shared_ptr<Trade> trade) {
	double pv = 0;
	if (trade->getType() == "TreeProduct") {
		auto treePtr = dynamic_cast<TreeProduct*>(trade.get());
		if (treePtr) { //check if cast is sucessful
			pv = PriceTree(mkt, *treePtr) * (treePtr->getDirection() == "long" ? treePtr->getNotional() : -treePtr->getNotional());
		}
	}
	else {
		double price = 0; //get from market data
		pv = trade->Pv(mkt);
	}

	return pv;
}

void BinomialTreePricer::ModelSetup(double S0, double sigma, double r, double dt)
{
	// a basic version of binomial tree
	u = 1.1;
	d = 0.9;
	p = (exp(r) - d) / (u - d);
}

double BinomialTreePricer::PriceTree(const Market& mkt, const TreeProduct& trade) {
	double T = (trade.GetExpiry() - mkt.asOf) / 365.0;
	double dt = T / nTimeSteps;
	double s0 = mkt.getstockPrice(trade.getUnderlying());
	auto volCurve = mkt.getVolCurve(trade.getVolname());
	double vol = volCurve->getVol(trade.GetExpiry());
	auto irCurve = mkt.getCurve("USD-SOFR");
	double rate = irCurve->getRate(trade.GetExpiry());
	ModelSetup(s0, vol, rate, dt);

	// initialize
	for (int i = 0; i <= nTimeSteps; i++) {
		states[i] = trade.Payoff(GetSpot(nTimeSteps, i));
	}

	// price by backward induction
	for (int k = nTimeSteps - 1; k >= 0; k--)
		for (int i = 0; i <= k; i++) {
			// calculate continuation value
			double df = exp(-rate * dt);
			double continuation = df * (states[i] * GetProbUp() + states[i + 1] * GetProbDown());
			// calculate the option value at node(k, i)
			states[i] = trade.ValueAtNode(GetSpot(k, i), dt * k, continuation);
		}

	return states[0];

}

void CRRBinomialTreePricer::ModelSetup(double S0, double sigma, double rate, double dt)
{
	double b = std::exp((2 * rate + sigma * sigma) * dt) + 1;
	u = (b + std::sqrt(b * b - 4 * std::exp(2 * rate * dt))) / 2 /
		std::exp(rate * dt);
	p = (std::exp(rate * dt) - 1 / u) / (u - 1 / u);
	currentSpot = S0;
}

void JRRNBinomialTreePricer::ModelSetup(double S0, double sigma, double rate, double dt)
{
	u = std::exp((rate - sigma * sigma / 2) * dt + sigma * std::sqrt(dt));
	d = std::exp((rate - sigma * sigma / 2) * dt - sigma * std::sqrt(dt));
	p = (std::exp(rate * dt) - d) / (u - d);
	currentSpot = S0;
}
