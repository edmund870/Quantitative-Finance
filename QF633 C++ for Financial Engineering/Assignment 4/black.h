#ifndef _BLACK_H
#define _BLACK_H
#include "Date.h"
#include "Trade.h"

// this class provide a common member function interface for option type of trade.
class Black : public Trade
{
public:
	Black(const string& trade_id, const string& name, double notional, double strike, const Date& end, double vol, double rate, bool isCall)
		: Trade(trade_id, "Black", "Black", tradeDate) {
		underlying = name;
		this->notional = notional;
		this->strike = strike;
		endDate = end;
		isCall = isCall;
	};

	inline double Payoff(double marketPrice) const
	{
		double expiry = (endDate - today) / 365.0;
		// N(d1) and N(d2) are the cumulative distribution function values for a standard normal distribution
		double d1_val = (log(marketPrice / strike) + (rate + 0.5 * vol * vol) * expiry) / (vol * sqrt(expiry));
		double d2_val = d1_val - vol * sqrt(expiry);

		double N_d1, N_d2;

		if (isCall) {
			N_d1 = 0.5 * (1 + erf(d1_val / sqrt(2)));  // Using the error function for N(d1)
			N_d2 = 0.5 * (1 + erf(d2_val / sqrt(2)));  // Using the error function for N(d2)

			return notional * (marketPrice * N_d1 - strike * exp(-rate * expiry) * N_d2);
		}
		else {
			N_d1 = 0.5 * (1 + erf(-d1_val / sqrt(2)));  // N(-d1)
			N_d2 = 0.5 * (1 + erf(-d2_val / sqrt(2)));  // N(-d2)

			return notional * (strike * exp(-rate * expiry) * N_d2 - marketPrice * N_d1);
		}
	};

	inline const Date& getEndDate() const { return endDate; }
	inline string getUnderlying() const { return underlying; }

	inline void setVol(double _vol) { vol = _vol; }
	inline void setRate(double _Rate) { rate = _Rate; }
	inline void setToday(Date _today) { today = _today; }

private:
	string underlying;
	double notional;
	double strike;
	Date endDate;
	double vol;
	double rate;
	bool isCall;
	Date today;
};

#endif
