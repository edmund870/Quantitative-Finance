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

	// for trade factory
	EuropeanOption(const string& _trade_id, const Date& tradeDate, const Date& start, const Date& end)
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
		tradeName = direction + 
			"_EU_" + to_string(strike) + "_" +
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
	inline string getCurvename() const override{ return curvename; }
	inline string getVolname() const override { return volname; }
	inline string getDirection() const override { return direction; }

	//pricing
	virtual double Payoff(double S) const 
	{ 
		return PAYOFF::VanillaOption(optType, strike, S); 
	}
	virtual double ValueAtNode(double S, double t, double continuation) const { return continuation; }

protected:
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

class EuroCallSpread : public EuropeanOption {
public:
	EuroCallSpread(const string& _trade_id, double _notional, double _k1, double _k2, const Date& _expiry, const string& _underlying)
		: EuropeanOption(_trade_id, "EU_Call_Spread_" + to_string(_k1) + "_" + to_string(_k2) + "_" + _underlying + "_" + to_string(_expiry.year) + "-" + to_string(_expiry.month) + "-" + to_string(_expiry.day)), strike1(_k1), strike2(_k2) {
		notional = _notional;
		expiryDate = _expiry;
		assert(_k1 < _k2);
		underlying = _underlying;
	};
	virtual double Payoff(double S) const 
	{ 
		return PAYOFF::CallSpread(strike1, strike2, S); 
	};
	virtual const Date& GetExpiry() const { return expiryDate; };
	inline string getUnderlying() const override { return underlying; }
	inline double getNotional() const override { return notional; }
	inline string getDirection() const override { return direction; }

private:
	string trade_id;
	double strike1;
	double strike2;
	double notional;
	//Date expiryDate;
};

#endif
