#include "Bond.h"

double Bond::Payoff(double s) const
{
	double pv = bondNotional * (s - tradePrice);
	return pv;
}

double Bond::Pv(const Market& mkt) const {
	double couponPayment = coupon_rate * frequency * 100;
	double bondValue = 0.0;
	auto rc = mkt.getCurve(curvename);

	// discounting cash flow
	for (size_t i = 0; i < cashflowDates.size(); ++i) {
		Date dt = cashflowDates[i];
		if (dt - valuedate < 0)
			continue;
		double df = rc->getDf(dt, valuedate);
		bondValue += couponPayment * df;
	}

	// Discount the principal (notional) value to the present
	bondValue += 100 * rc->getDf(endDate, valuedate);
	double pv = bondValue / 100.0 * bondNotional;


	return direction == "long" ? pv : -pv;
}