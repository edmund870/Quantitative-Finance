#ifndef _TREE_PRODUCT_H
#define _TREE_PRODUCT_H
#include "Date.h"
#include "Trade.h"

// this class provide a common member function interface for option type of trade.
class TreeProduct : public Trade
{
public:
	TreeProduct() {};
	TreeProduct(const string& trade_id, const string& trade_name) : Trade(trade_id, "TreeProduct", trade_name, Date()) { tradeType = "TreeProduct"; };

	// for trade factory
	TreeProduct(const string& trade_id) : Trade(trade_id, "TreeProduct", Date(), Date()) { tradeType = "TreeProduct"; };

	// setters
	inline void updateName(const string& _tradename) {
		updateTradeName(_tradename);
	}

	// getters
	virtual const Date& GetExpiry() const = 0;

	// pricers
	virtual double ValueAtNode(double stockPrice, double t, double continuationValue) const = 0;
	double Pv(const Market& mkt) const { return 0; };
};

#endif
