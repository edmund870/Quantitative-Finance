#pragma once
#include<string>
#include "Date.h"
#include "Market.h"

using namespace std;

class Trade {
public:
	Trade() {};
	Trade(const string& _trade_id, const string& _type, const string& _trade_name, const Date& _tradeDate)
		: trade_id(_trade_id), tradeType(_type), trade_name(_trade_name), tradeDate(_tradeDate) {
	};

	// for trade factory
	Trade(const string& _trade_id, const string& _type, const Date& _startDate, const Date& _tradeDate)
		: trade_id(_trade_id), tradeType(_type), tradeDate(_tradeDate) {
	};

	// setter
	inline void updateTradeName(const string& name) {
		trade_name = name;
	}

	// getter
	inline string getType() { return tradeType; };
	inline string getTradeid() { return trade_id; };
	inline string getTradeName() { return trade_name; };
	virtual string getUnderlying() const = 0;
	virtual double getNotional() const = 0;
	virtual string getDirection() const = 0;
	virtual string getCurvename() const = 0;
	virtual string getVolname() const = 0;
	virtual double Pv(const Market& mkt) const = 0;
	virtual double Payoff(double marketPrice) const = 0;
	virtual ~Trade() {};

protected:
	string trade_id;
	string tradeType;
	string trade_name;
	string underlying = "";
	Date tradeDate;
};