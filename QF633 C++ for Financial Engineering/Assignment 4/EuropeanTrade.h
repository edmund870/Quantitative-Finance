#ifndef _EUROPEAN_TRADE
#define _EUROPEAN_TRADE

#include <cassert> 

#include "TreeProduct.h"
#include "Payoff.h"
#include "Types.h"

class EuropeanOption : public TreeProduct {
public:
	EuropeanOption() {};
	EuropeanOption(const string& _trade_id, const string& trade_name) : TreeProduct(_trade_id, trade_name) {};
	EuropeanOption(const string& _trade_id, double _notional, OptionType _optType, double _strike, const Date& _expiry, const string& _underlying)
		: TreeProduct(_trade_id, "EU_" + to_string(_strike) + "_" + to_string(_optType) + "_" + _underlying + "_" + to_string(_expiry.year) + "-" + to_string(_expiry.month) + "-" + to_string(_expiry.day)),
		notional(_notional), optType(_optType), strike(_strike), expiryDate(_expiry), underlying(_underlying) {
	};
	virtual double Payoff(double S) const { return PAYOFF::VanillaOption(optType, strike, S); }
	virtual const Date& GetExpiry() const { return expiryDate; }
	virtual double ValueAtNode(double S, double t, double continuation) const { return continuation; }

	inline const string getUnderlying() const { return underlying; }
	inline const double getNotional() const { return notional; }

protected:
	string trade_id;
	OptionType optType;
	double strike;
	Date expiryDate;
	string underlying;
	double notional;
};

class EuroCallSpread : public EuropeanOption {
public:
	EuroCallSpread(const string& _trade_id, double _notional, double _k1, double _k2, const Date& _expiry, const string& _underlying)
		: EuropeanOption(_trade_id, "EU_Call_Spread_" + to_string(_k1) + "_" + to_string(_k2) + "_" + _underlying + "_" + to_string(_expiry.year) + "-" + to_string(_expiry.month) + "-" + to_string(_expiry.day)), strike1(_k1), strike2(_k2) {
		notional = _notional;
		expiryDate = _expiry;
		assert(_k1 < _k2);
		underlying = _underlying;
	};
	virtual double Payoff(double S) const { return PAYOFF::CallSpread(strike1, strike2, S); };
	virtual const Date& GetExpiry() const { return expiryDate; };
	inline const string getUnderlying() const { return underlying; }
	inline const double getNotional() const { return notional; }

private:
	string trade_id;
	double strike1;
	double strike2;
	double notional;
	//Date expiryDate;
};

#endif
