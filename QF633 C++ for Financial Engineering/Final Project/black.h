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
		expiryDate = end;
		isCall = isCall;
	};

	// for trade factory
	Black(const string& _trade_id, const Date& tradeDate, const Date& start, const Date& end)
		: Trade(_trade_id, "Black", start, tradeDate)
	{
		expiryDate = end;
	}

	// setter
	inline void setToday(const Date& _today) {
		today = _today;
	}
	inline void setNotional(const double& _notional) {
		notional = _notional;
	}
	inline void setVol(const double& _vol) {
		vol = _vol;
	}
	inline void setRate(const double& _Rate) {
		rate = _Rate;
	}
	inline void setCurvename(const string& name) {
		curvename = name;
	}
	inline void setVolname(const string& name) {
		volname = name;
	}
	inline void setStrike(const double& _strike)
	{
		strike = _strike;
	};
	inline void setisCall(const int& _type)
	{
		isCall = _type;
	};
	inline void setUnderlying(const string& _underlying) {
		underlying = _underlying;
	}
	inline void setdirection(const string& _direction) {
		direction = _direction;
	}
	inline void updateBlackName() {
		tradeName = direction + "_Black" 
			+ to_string(strike) + "_" +
			to_string(isCall) + "_" +
			underlying + "_" +
			to_string(expiryDate.year) + "-" +
			to_string(expiryDate.month) + "-" +
			to_string(expiryDate.day);
	}
	inline void updateBaseTradeName() {
		updateTradeName(tradeName);
	}

	// getter
	inline const Date& getExpiryDate() const { return expiryDate; }
	inline string getUnderlying() const override { return underlying; }
	inline string getCurvename() const override { return curvename; }
	inline string getVolname() const override { return volname; }
	inline double getNotional() const override { return notional; }
	inline string getDirection() const override { return direction; }

	// pricing
	double Payoff(double marketPrice) const;
	double Pv(const Market& mkt) const;

private:
	string underlying;
	double notional;
	double strike;
	Date expiryDate;
	string curvename;
	string volname;
	double vol;
	double rate;
	bool isCall;
	string direction;
	Date today;
	string tradeName;
};

#endif
