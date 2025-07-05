#include "Swap.h"

double Swap::Payoff(double s) const
{
	//this function will not be called
	return (s - tradeRate) * swapNotional;
}

double Swap::getAnnuity(const Market& mkt) const
{
	double annuity = 0;
	Date valueDate = mkt.asOf;
	auto rc = mkt.getCurve(curvename);
	for (size_t i = 1; i < cashflowDates.size(); i++) {
		auto dt = cashflowDates[i];
		if (dt - valueDate < 0)
			continue;
		double tau = (cashflowDates[i] - cashflowDates[i - 1]) / 360;
		double df = rc->getDf(dt, valueDate);
		annuity += swapNotional * tau * df;
	}

	return annuity;
}

double Swap::Pv(const Market& mkt) const
{
	//using cash flow discunting
	Date valueDate = mkt.asOf;
	auto rc = mkt.getCurve(curvename);
	double fltPv = (-swapNotional + swapNotional * rc->getDf(endDate, valueDate));
	double fixPv = 0;
	for (size_t i = 1; i < cashflowDates.size(); i++) {
		Date dt = cashflowDates[i];
		if (dt - valueDate < 0)
			continue;
		double tau = (cashflowDates[i] - cashflowDates[i - 1]) / 360;
		double df = rc->getDf(dt, valueDate);
		fixPv += swapNotional * tau * tradeRate * df;
	}

	return direction == "pay" ? -(fixPv + fltPv) : fixPv + fltPv;

}
