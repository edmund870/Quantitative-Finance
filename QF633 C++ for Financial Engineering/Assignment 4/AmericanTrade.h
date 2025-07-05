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
	virtual double Payoff(double S) const
	{
		return PAYOFF::VanillaOption(optType, strike, S);
	}
	virtual const Date& GetExpiry() const
	{
		return expiryDate;
	}
	virtual double ValueAtNode(double S, double t, double continuation) const
	{
		return std::max(Payoff(S), continuation);
	}
	inline const string getUnderlying() const { return underlying; }
	inline const double getNotional() const { return notional; }

private:
	string trade_id;
	OptionType optType;
	double strike;
	Date expiryDate;
	string underlying;
	double notional;
};

class AmerCallSpread : public TreeProduct {
public:
	AmerCallSpread(const string& _trade_id, double _notional, double _k1, double _k2, const Date& _expiry, const string& _underlying)
		: TreeProduct(_trade_id, "AM_Call_Spread_" + to_string(_k1) + "_" + to_string(_k2) + "_" + _underlying + "_" + to_string(_expiry.year) + "-" + to_string(_expiry.month) + "-" + to_string(_expiry.day)),
		notional(_notional), strike1(_k1), strike2(_k2), expiryDate(_expiry), underlying(_underlying)
	{
		assert(_k1 < _k2);
	};
	virtual double Payoff(double S) const
	{
		return PAYOFF::CallSpread(strike1, strike2, S);
	}
	virtual const Date& GetExpiry() const
	{
		return expiryDate;
	}
	virtual double ValueAtNode(double S, double t, double continuation) const
	{
		return std::max(Payoff(S), continuation);
	}
	inline const string getUnderlying() const { return underlying; }
	inline const double getNotional() const { return notional; }

private:
	string trade_id;
	double strike1;
	double strike2;
	Date expiryDate;
	string underlying;
	double notional;
};

#endif
