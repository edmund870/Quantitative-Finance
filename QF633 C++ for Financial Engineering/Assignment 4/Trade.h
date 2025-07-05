#pragma once
#include<string>
#include "Date.h"
#include "Market.h"

using namespace std;

class Trade {
public:
    Trade(){};
    Trade(const string& _trade_id, const string& _type, const string& _trade_name, const Date& _tradeDate)
        : trade_id(_trade_id), tradeType(_type), trade_name(_trade_name), tradeDate(_tradeDate) {};
    inline string getType() { return tradeType; };
    inline string getTradeid() { return trade_id; };
    inline string getTradeName() { return trade_name; };
    //virtual double Price(const Market& market) const = 0;
    virtual double Payoff(double marketPrice) const = 0;
    virtual ~Trade() {};

protected:   
    string trade_id;
    string tradeType;
    string trade_name;
    Date tradeDate;
};