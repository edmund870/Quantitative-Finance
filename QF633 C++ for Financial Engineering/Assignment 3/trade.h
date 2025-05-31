#pragma once

#include <string>
#include <iostream>

#include "date.h"

using namespace std;

// complete this implementation
class Trade
{

public:
	virtual double calculatePv(double spot, double vol, double rate) const = 0;
	virtual string getTradeDetails() const = 0;


	virtual ~Trade() {};

	virtual string getTradeId() const = 0;

};

class OptionTrade : public Trade
{
public:
	OptionTrade()
	{
		cout << "deafult constructor is called for option trade" << endl;
	};

	~OptionTrade()
	{
		cout << "deafult destructor is called for option trade" << endl;
	}

	OptionTrade(string trade_id, double notional, double strike, Date start, Date end, bool isCall);

	double calculatePv(double spot, double vol, double rate) const override;

	string getTradeId() const override;

	string getTradeDetails() const;

private:
	string trade_id;
	double m_notional = 0;
	double m_strike = 0;
	bool m_isCall = true;
	Date m_start;
	Date m_end;
	double expiry;
};