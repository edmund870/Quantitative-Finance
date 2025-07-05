#include <cmath>
#include "Pricer.h"
#include "Bond.h"
#include "Swap.h"
#include "EuropeanTrade.h"
#include "AmericanTrade.h"
#include "black.h"


double Pricer::Price(const Market& mkt, Trade* trade) {
	double pv = 0;
	if (trade->getType() == "TreeProduct") {
		TreeProduct* treePtr = dynamic_cast<TreeProduct*>(trade);
		if (treePtr) { //check if cast is sucessful
			pv = PriceTree(mkt, *treePtr);
		}
	}
	else {
		double price = 0; //get from market data
		string type = trade->getType();
		RateCurve curve = mkt.getCurve("USD-SOFR");

		if (type == "BondTrade") {
			Bond* bondPtr = dynamic_cast<Bond*>(trade);
			price = mkt.getbondPrice(bondPtr->getName());
			bondPtr->setRateCurve(&curve);

		}
		if (type == "SwapTrade") {
			RateCurve swap_rate = mkt.getCurve("USD-SOFR");
			Swap* SwapPtr = dynamic_cast<Swap*>(trade);
			double tenor = SwapPtr->tenor();

			time_t t = time(nullptr);
			const time_t ONE_DAY = 24 * 60 * 60;
			time_t date_seconds = t + (tenor * ONE_DAY);

			Date tenor_end_date;

			struct tm timeInfo;
			if (localtime_s(&timeInfo, &date_seconds) == 0) {
				// localtime_s() convert current system time into localtime and populate tm struct
				tenor_end_date.year = timeInfo.tm_year + 1900; //1900 based
				tenor_end_date.month = timeInfo.tm_mon + 1; //0 based
				tenor_end_date.day = timeInfo.tm_mday;
			};

			price = swap_rate.getRate(tenor_end_date);
		}

		if (type == "Black") {
			Black* BlackPtr = dynamic_cast<Black*>(trade);
			price = mkt.getstockPrice(BlackPtr->getUnderlying());
			VolCurve vol_curve = mkt.getVolCurve("Vol Curve");
			double vol = vol_curve.getVol(BlackPtr->getEndDate());

			BlackPtr->setVol(vol);
			BlackPtr->setToday(mkt.asOf);
			BlackPtr->setRate(0.04);
		}

		pv = trade->Payoff(price);
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
	// model setup
	double T = (trade.GetExpiry() - mkt.asOf) / 365.0;
	double dt = T / nTimeSteps;
	double stockPrice = 0, vol = 0, rate = 0.04;
	/*
	get these data for the deal from market object
	*/
	string underlying;
	double notional;
	if (const EuropeanOption* euroPtr = dynamic_cast<const EuropeanOption*>(&trade)) {
		underlying = euroPtr->getUnderlying();
		notional = euroPtr->getNotional();

	}
	else if (const EuroCallSpread* eurospreadPtr = dynamic_cast<const EuroCallSpread*>(&trade)) {
		underlying = eurospreadPtr->getUnderlying();
		notional = eurospreadPtr->getNotional();
	}
	else if (const AmericanOption* AmPtr = dynamic_cast<const AmericanOption*>(&trade)) {
		underlying = AmPtr->getUnderlying();
		notional = AmPtr->getNotional();
	}
	else if (const AmerCallSpread* AmspreadPtr = dynamic_cast<const AmerCallSpread*>(&trade)) {
		underlying = AmspreadPtr->getUnderlying();
		notional = AmspreadPtr->getNotional();
	}

	stockPrice = mkt.getstockPrice(underlying);

	VolCurve vol_curve = mkt.getVolCurve("Vol Curve");
	vol = vol_curve.getVol(trade.GetExpiry());

	ModelSetup(stockPrice, vol, rate, dt);

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

	return states[0] * notional;

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
