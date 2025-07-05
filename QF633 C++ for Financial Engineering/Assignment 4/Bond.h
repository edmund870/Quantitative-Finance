#pragma once
#include "Trade.h"
#include "Market.h"

class Bond : public Trade {

public:
	Bond(const string& trade_id, const std::string& name, const Date& tradeDate, const Date& today, Date& start, const Date& end,
		double notional, double rate, RateCurve* rateCurve, double couponFreq, double price) : Trade(trade_id, "BondTrade", "Bond_" + to_string(rate) + "_" + to_string(end.year) + "-" + to_string(end.month) + "-" + to_string(end.day), tradeDate) {
		startDate = start;
		endDate = end;
		valuedate = today;
		bondName = name;
		bondNotional = notional;
		coupon_rate = rate;
		rateCurve = rateCurve;
		frequency = couponFreq;
		tradePrice = price;
	}

	inline double Payoff(double marketPrice) const
	{
		double couponPayment = coupon_rate * frequency * 100;
		double bondValue = 0.0;
		vector<Date> cashflowDates;
		Date interim = startDate;

		while (endDate - interim >= 0) {
			if (interim - valuedate >= 0) {
				cashflowDates.push_back(interim);
			}
			interim = interim.addMonths(12 * frequency);
		}

		for (size_t i = 0; i < cashflowDates.size(); ++i) {
			double zeroCouponRate = rateCurve->getRate(cashflowDates[i]);
			double discountFactor = pow(1 + zeroCouponRate * frequency, -(static_cast<int>(i) + 1));

			bondValue += couponPayment * discountFactor;
		}

		// Discount the principal (notional) value to the present
		double discountFactorForPrincipal = pow(1 + rateCurve->getRate(endDate) * frequency, -(static_cast<int>(cashflowDates.size())));
		bondValue += 100 * discountFactorForPrincipal;

		return bondNotional * (marketPrice - bondValue) / 100;
	};

	inline string getName() const { return bondName; }
	inline void setRateCurve(RateCurve* curve) { rateCurve = curve; }

private:
	string bondName;
	double bondNotional;
	double coupon_rate;
	RateCurve* rateCurve;
	double tradePrice;
	double frequency;
	Date startDate;
	Date endDate;
	Date valuedate;
};

