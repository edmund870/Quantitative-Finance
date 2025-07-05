#pragma once
#include "Trade.h"

class Swap : public Trade {
public:
	//make necessary change
	Swap(const string& trade_id, const Date& tradeDate, Date start, Date end, double notional, double rate, double freq) 
		: Trade(trade_id, "SwapTrade", "Swap_" + to_string(rate) + "_" + to_string(end.year) + "-" + to_string(end.month) + "-" + to_string(end.day), tradeDate)
	{
		/*
		add constructor details
		*/
		startDate = start;
		endDate = end;
		swapNotional = notional;
		tradeRate = rate;
		frequency = freq;
	}
	inline double Payoff(double marketRate) const {
		/*
		Implement this, using npv = annuity * (traded rate - market swap rate);
		Annuity = sum of (notional * year fraction of each coupon period * Discount factor at each period end);
		Df = exp(-zT), z is the zero coupon rate;
		*/
		return getAnnuity() * (tradeRate - marketRate);
	};

	inline double tenor() const { return endDate - startDate; }

private:
	Date startDate;
	Date endDate;
	double swapNotional;
	double tradeRate;
	double frequency;

	double getAnnuity() const {
		//implement this where assuming zero rate is 4% per annum for discouting. 
		double zeroCouponRate = 0.04;
		double annuity = 0.0;
		int duration = static_cast<int>(floor((endDate - startDate) / 365.25)) / frequency;

		for (int i = 1; i <= duration; ++i) {
			double discountFactor = std::exp(-zeroCouponRate * i);
			annuity += swapNotional * frequency * discountFactor;
		}

		return annuity;
	};
};