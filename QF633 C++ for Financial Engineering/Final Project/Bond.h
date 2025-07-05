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
		tradeName = name;
		bondNotional = notional;
		coupon_rate = rate;
		rateCurve = rateCurve;
		frequency = couponFreq;
		tradePrice = price;
	}

	// for trade factory
	Bond(const string& trade_id, const Date& tradeDate, const Date& start, const Date& end)
		: Trade(trade_id, "BondTrade", start, tradeDate)
	{
		startDate = start;
		endDate = end;
	}

	// setters
	inline void setValueDate(const Date& today) {
		valuedate = today;
	}
	inline void setUnderlying(const string& _underlying) {
		underlying = _underlying;
		string currency = _underlying.substr(0, 3);
		if (currency == "USD") {
			curvename = "USD-SOFR";
		}
		else if (currency == "SGD") {
			curvename = "SGD-SORA";
		}
		else {
			throw std::runtime_error("NO CURVE FOR CURRENCY: " + currency);
		};
	}
	inline void setNotional(const double& _notional) {
		bondNotional = _notional;
	}
	inline void setCoupon(const double& _coupon) {
		coupon_rate = _coupon;
	}
	inline void settradePrice(const double& _tradeprice) {
		tradePrice = _tradeprice;
	}
	inline void setFrequency(const double& _freq) {
		frequency = _freq;
	}
	inline void setdirection(const string& _direction) {
		direction = _direction;
	}
	inline void updateBondName() {
		tradeName = direction +
			"_Bond_" + to_string(coupon_rate) + "_" +
			to_string(endDate.year) + "-" +
			to_string(endDate.month) + "-" +
			to_string(endDate.day);
	}
	inline void updateBaseTradeName() {
		updateTradeName(tradeName);
	}

	// getters
	inline string getUnderlying() const override { return underlying; }
	inline string getCurvename() const override { return curvename; }
	inline string getVolname() const override { return ""; }
	inline double getNotional() const override { return bondNotional; }
	inline string getDirection() const override { return direction; }

	// pricers
	void inline generateBondSchedule() {
		if (startDate - endDate >= 0 || frequency <= 0 || frequency > 1)
			throw std::runtime_error("Error: start date is later than end date, or invalid frequency!");

		Date interim = startDate;
		while (endDate - interim >= 0) {
			if (interim - valuedate >= 0) {
				cashflowDates.push_back(interim);
			}
			interim = interim.addMonths(12.0 * frequency);
		}

	}
	double Payoff(double s) const;
	double Pv(const Market& mkt) const;

private:
	string tradeName;
	string underlying;
	double bondNotional;
	double coupon_rate;
	string curvename;
	double tradePrice;
	double frequency;
	Date startDate;
	Date endDate;
	Date valuedate;
	vector<Date> cashflowDates;
	string direction;
};

