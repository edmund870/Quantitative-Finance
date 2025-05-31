#include <sstream>
#include "trade.h"
#include "black.h"
#include "date.h"

OptionTrade::OptionTrade(string trade_id, double notional, double strike, Date start, Date end, bool isCall)
	: trade_id(trade_id), m_notional(notional), m_strike(strike), m_start(start), m_end(end), m_isCall(isCall), expiry((end - start) / 365.0)
{
};

double OptionTrade::calculatePv(double spot, double vol, double rate) const
{
	double pv = BlackScholes(m_notional, m_strike, expiry, spot, vol, rate, m_isCall);

	return pv;
};

string OptionTrade::getTradeDetails() const
{
	// Create a string that includes trade details
	return "Notional: " + to_string(m_notional) +
		", Strike: " + to_string(m_strike) +
		", Expiry: " + to_string(expiry) +
		", Type: " + (m_isCall ? "Call" : "Put") +
		"      ";
};

string OptionTrade::getTradeId() const {
	return trade_id;
}