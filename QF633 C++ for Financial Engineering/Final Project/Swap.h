#pragma once
#include "Trade.h"

class Swap : public Trade {
public:
	Swap(const string& trade_id, const Date& tradeDate, Date start, Date end, double notional, double rate, double freq)
		: Trade(trade_id, "SwapTrade", "Swap_" + to_string(rate) + "_" + to_string(end.year) + "-" + to_string(end.month) + "-" + to_string(end.day), tradeDate)
	{
		startDate = start;
		endDate = end;
		swapNotional = notional;
		tradeRate = rate;
		frequency = freq;
	}

	// for trade factory
	Swap(const string& trade_id, const Date& tradeDate, const Date& start, const Date& end)
		: Trade(trade_id, "SwapTrade", start, tradeDate)
	{
		startDate = start;
		endDate = end;
	}

	// setters
	inline void setValueDate(const Date& today) {
		valuedate = today;
	}
	inline void setNotional(const double& notional) {
		swapNotional = notional;
	}
	inline void setCurvename(const string& name) {
		curvename = name;
	}
	inline void setRate(const double& rate) {
		tradeRate = rate;
	}
	inline void setFrequency(const double& freq) {
		frequency = freq;
	}
	inline void setdirection(const string& _direction) {
		direction = _direction;
	}
	inline void updateSwapName() {
		tradeName = direction + 
			"_Swap_" + to_string(tradeRate) + "_" +
			to_string(endDate.year) + "-" +
			to_string(endDate.month) + "-" +
			to_string(endDate.day);
	}
	inline void updateBaseTradeName() {
		updateTradeName(tradeName);
	}

	// getters
	inline string getUnderlying() const override { return "Swap"; }
	inline string getCurvename() const override{ return curvename; }
	inline string getVolname() const override { return ""; }
	inline double getNotional() const override { return swapNotional; }
	inline string getDirection() const override { return direction; }


	// pricers
	double Payoff(double r) const;
	double Pv(const Market& mkt) const;
	double getAnnuity(const Market& mkt) const;

	inline double tenor() const { return endDate - startDate; }

	void inline generateSwapSchedule() {
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

private:
	Date valuedate;
	Date startDate;
	Date endDate;
	string curvename;
	double swapNotional;
	double tradeRate;
	double frequency;
	string tradeName;
	vector<Date> cashflowDates;
	string direction;
};