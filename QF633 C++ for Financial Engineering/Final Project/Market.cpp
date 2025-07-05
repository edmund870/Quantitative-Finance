#include "Market.h"

using namespace std;

void RateCurve::display() const {
	cout << "rate curve:" << name << endl;
	for (size_t i = 0; i < tenorDates.size(); i++) {
		cout << tenorDates[i] << ":" << rates[i] << endl;
	}
	cout << endl;
}

void RateCurve::addRate(Date tenor, double rate) {
	//check if tenor already exist
	auto exists = std::find(tenorDates.begin(), tenorDates.end(), tenor);

	if (exists == tenorDates.end()) {
		tenorDates.push_back(tenor);
		rates.push_back(rate);
	}
}

double RateCurve::getRate(Date tenor) const {
	//check if exact date exists, if not, linearly interpolate
	auto exists = std::find(tenorDates.begin(), tenorDates.end(), tenor);
	if (tenor - tenorDates[0] < 0) {
		return rates[0];
	}
	else if (tenor - tenorDates[tenorDates.size() - 1] > 0) {
		return rates[tenorDates.size() - 1];
	}
	else if (exists != tenorDates.end()) {
		size_t index = std::distance(tenorDates.begin(), exists);
		return rates[index];
	}
	//use linear interpolation to get rate
	else {
		for (size_t i = 0; i < tenorDates.size() - 1; ++i) {
			if (tenor - tenorDates[i] >= 0 && tenorDates[i + 1] - tenor >= 0) {

				Date x0 = tenorDates[i];
				Date x1 = tenorDates[i + 1];
				double y0 = rates[i];
				double y1 = rates[i + 1];

				return y0 + (tenor - x0) * (y1 - y0) / (x1 - x0);
			}
		}
	}
}

double RateCurve::getDf(Date _date, Date valueDate) const
{
	double ccr = getRate(_date);
	double t = (_date - valueDate) / 365.0;
	return exp(-ccr * t);
}

void RateCurve::shock(Date tenor, double value)
{
	// parallel shock all tenors rate
	for (auto& rt : rates) {
		rt += value;
	}
}

void VolCurve::display() const {
	cout << "Vol curve:" << name << endl;
	for (size_t i = 0; i < tenors.size(); i++) {
		cout << tenors[i] << ":" << vols[i] << endl;
	}
	cout << endl;
}

void VolCurve::addVol(Date tenor, double rate) {
	//check if tenor already exist
	auto exists = std::find(tenors.begin(), tenors.end(), tenor);

	if (exists == tenors.end()) {
		tenors.push_back(tenor);
		vols.push_back(rate);
	}
}

void VolCurve::shock(Date tenor, double value)
{
	// parallel shock all tenors rate
	for (auto& v : vols) {
		v += value;
	}
}

double VolCurve::getVol(Date tenor) const {
	//check if exact date exists, if not, linearly interpolate
	auto exists = std::find(tenors.begin(), tenors.end(), tenor);
	if (tenor - tenors[0] < 0) {
		return vols[0];
	}
	else if (tenor - tenors[tenors.size() - 1] > 0) {
		return vols[tenors.size() - 1];
	}
	if (exists != tenors.end()) {
		size_t index = std::distance(tenors.begin(), exists);
		return vols[index];
	}
	//use linear interpolation to get rate
	else {
		for (size_t i = 0; i < tenors.size() - 1; ++i) {
			if (tenor - tenors[i] >= 0 && tenors[i + 1] - tenor >= 0) {

				Date x0 = tenors[i];
				Date x1 = tenors[i + 1];
				double y0 = vols[i];
				double y1 = vols[i + 1];

				return y0 + (tenor - x0) * (y1 - y0) / (x1 - x0);
			}
		}
	}
}

void Market::Print() const
{
	cout << "market asof: " << asOf << endl;

	for (auto curve : curves) {
		curve.second->display();
	}
	for (auto vol : vols) {
		vol.second->display();
	}

	cout << "Bond Price:" << endl;
	for (auto bondPrice : bondPrices) {
		cout << bondPrice.first << ' ' << bondPrice.second << endl;

	}
	cout << endl;

	cout << "Stock Price:" << endl;
	for (auto stockPrice : stockPrices) {
		cout << stockPrice.first << ' ' << stockPrice.second << endl;
	}
}

void Market::addCurve(const std::string& name, shared_ptr<RateCurve> curve) 
{
	curves.emplace(name, curve);
}
void Market::addVolCurve(const std::string& name, shared_ptr<VolCurve> vol)
{
	vols.emplace(name, vol);
}

void Market::addBondPrice(const std::string& bondName, double price) {
	bondPrices.emplace(bondName, price);
}

void Market::addStockPrice(const std::string& stockName, double price) {
	stockPrices.emplace(stockName, price);
}

std::ostream& operator<<(std::ostream& os, const Market& mkt)
{
	os << mkt.asOf << std::endl;
	return os;
}

std::istream& operator>>(std::istream& is, Market& mkt)
{
	is >> mkt.asOf;
	return is;
}
