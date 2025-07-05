#ifndef _AMERICAN_TRADE
#define _AMERICAN_TRADE

#include <cassert> 

#include "TreeProduct.h"
#include "Types.h"
#include "Payoff.h"

class AmericanOption : public TreeProduct {
public:
	AmericanOption(const string& _trade_id, double _notional, OptionType _optType, double _strike, const Date& _expiry, const string& _underlying)
		: TreeProduct(_trade_id, "AM_" + to_string(_strike) + "_" + to_string(_optType) + "_" + _underlying + "_" + to_string(_expiry.year) + "-" + to_string(_expiry.month) + "-" + to_string(_expiry.day)),
		notional(_notional), optType(_optType), strike(_strike), expiryDate(_expiry), underlying(_underlying) {
	}

	// for trade factory
	AmericanOption(const string& _trade_id, const Date& tradeDate, const Date& start, const Date& end)
		: TreeProduct(_trade_id)
	{
		expiryDate = end;
	}

	//setters
	inline void setStrike(const double& _strike)
	{
		strike = _strike;
	};
	inline void setOptionType(const OptionType& _type)
	{
		optType = _type;
	};
	inline void setCurvename(const string& name) {
		curvename = name;
	}
	inline void setVolname(const string& name) {
		volname = name;
	}
	inline void setUnderlying(const string& _underlying) {
		underlying = _underlying;
	}
	inline void setNotional(double const& _notional) {
		notional = _notional;
	}
	inline void setdirection(const string& _direction) {
		direction = _direction;
	}
	inline void updateOptionName() {
		tradeName = direction + "_AM_" + 
			to_string(strike) + "_" +
			to_string(optType) + "_" +
			underlying + "_" +
			to_string(expiryDate.year) + "-" +
			to_string(expiryDate.month) + "-" +
			to_string(expiryDate.day);
	}
	inline void updateTreeProductTradeName() {
		updateName(tradeName);
	}

	// getters
	virtual const Date& GetExpiry() const { return expiryDate; }
	inline string getUnderlying() const override { return underlying; }
	inline double getNotional() const override { return notional; }
	inline string getCurvename() const override { return curvename; }
	inline string getVolname() const override { return volname; }
	inline string getDirection() const override { return direction; }

	// pricing
	virtual double Payoff(double S) const 
	{
		return PAYOFF::VanillaOption(optType, strike, S);
	}
	virtual double ValueAtNode(double S, double t, double continuation) const
	{
		return std::max(Payoff(S), continuation);
	}

private:
	string trade_id;
	string tradeName;
	OptionType optType;
	double strike;
	string curvename;
	string volname;
	Date expiryDate;
	string underlying;
	double notional;
	string direction;
};

class AmerCallSpread : public TreeProduct {
public:
	AmerCallSpread(const string& _trade_id, double _notional, double _k1, double _k2, const Date& _expiry, const string& _underlying)
		: TreeProduct(_trade_id, "AM_Call_Spread_" + to_string(_k1) + "_" + to_string(_k2) + "_" + _underlying + "_" + to_string(_expiry.year) + "-" + to_string(_expiry.month) + "-" + to_string(_expiry.day)),
		notional(_notional), strike1(_k1), strike2(_k2), expiryDate(_expiry), underlying(_underlying)
	{
		assert(_k1 < _k2);
	};
	inline void setdirection(const string& _direction) {
		direction = _direction;
	}
	inline void setCurvename(const string& name) {
		curvename = name;
	}
	inline void setVolname(const string& name) {
		volname = name;
	}
	virtual double Payoff(double S) const
	{
		return PAYOFF::CallSpread(strike1, strike2, S);
	};
	virtual const Date& GetExpiry() const
	{
		return expiryDate;
	}
	virtual double ValueAtNode(double S, double t, double continuation) const
	{
		return std::max(Payoff(S), continuation);
	}

	inline string getUnderlying() const override { return underlying; }
	inline double getNotional() const override { return notional; }
	inline string getCurvename() const { return curvename; }
	inline string getVolname() const override { return volname; }
	inline string getDirection() const override { return direction; }

private:
	string trade_id;
	double strike1;
	double strike2;
	Date expiryDate;
	string underlying;
	double notional;
	string curvename;
	string volname;
	string direction;
};

#endif
