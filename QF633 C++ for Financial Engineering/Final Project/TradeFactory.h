#pragma once
#include <memory>
#include "Trade.h"
#include "Market.h"
#include "Pricer.h"
#include "EuropeanTrade.h"
#include "Bond.h"
#include "Swap.h"
#include "AmericanTrade.h"
#include "black.h"

using namespace std;
// Abstract creator class
class TradeFactory
{
public:
	virtual shared_ptr<Trade> createTrade(
		const string& trade_id, const string& type, const Date& tradeDate,
		const Date& startDate, const Date& expiryDate
	) = 0;

	virtual ~TradeFactory()
	{
		cout << "trade factor is destroyed" << endl;
	}
};
// Concrete creator class - create option type of trades
class LinearTradeFactory : public TradeFactory
{
public:
	shared_ptr<Trade> createTrade(
		const string& trade_id, const string& type, const Date& tradeDate,
		const Date& startDate, const Date& expiryDate
	) override
	{

		if (type == "swap")
		{
			return make_shared<Swap>(trade_id, tradeDate, startDate, expiryDate);
		}
		else if (type == "bond")
		{
			return make_shared<Bond>(trade_id, tradeDate, startDate, expiryDate);
		}
		else
			return nullptr;
	}
};

// Concrete creator class - create option type of trades
class OptionTradeFactory : public TradeFactory
{
public:
	shared_ptr<Trade> createTrade(
		const string& trade_id, const string& type, const Date& tradeDate,
		const Date& startDate, const Date& expiryDate
	) override
	{
		if (type == "european")
		{
			return make_shared<EuropeanOption>(trade_id, tradeDate, startDate, expiryDate);
		}
		else if (type == "american")
		{
			return make_shared<AmericanOption>(trade_id, tradeDate, startDate, expiryDate);
		}
		else if (type == "black")
		{
			return make_shared<Black>(trade_id, tradeDate, startDate, expiryDate);
		}
		else
			return nullptr;
	}

};
#pragma once
