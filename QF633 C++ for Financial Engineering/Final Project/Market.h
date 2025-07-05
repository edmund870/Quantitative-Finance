#ifndef MARKET_H
#define MARKET_H

#include <iostream>
#include <vector>
#include <unordered_map>
#include "Date.h"

using namespace std;

class RateCurve {
public:
	RateCurve() {};
	RateCurve(const string& _name) : name(_name) {};
	void addRate(Date tenor, double rate);
	double getRate(Date tenor) const; //implement this function using linear interpolation
	double getDf(Date _date, Date valueDate) const;
	void shock(Date tenor, double value);
	void display() const;

private:
	std::string name;
	vector<Date> tenorDates;
	vector<double> rates;
};

class VolCurve { // atm vol curve without smile
public:
	VolCurve() {}
	VolCurve(const string& _name) : name(_name) {};
	void addVol(Date tenor, double rate); //implement this
	double getVol(Date tenor) const; //implement this function using linear interpolation
	void shock(Date tenor, double value);
	void display() const; //implement this

private:
	string name;
	vector<Date> tenors;
	vector<double> vols;
};

class Market
{
public:
	Date asOf;
	char* name;

	Market() {
		//cout << "default market constructor is called by object@" << this << endl;
	}

	Market(const Date& now) : asOf(now) {
		//cout << "market constructor is called by object@" << this << endl;
		//name = new char[5];
		//strcpy_s(name, 5, "test");
	}

	// for risk engine
	Market(const Market& other) {
		this->asOf = other.asOf;
		// Deep copy each Curve
		for (const auto& curve : other.curves) {
			curves.emplace(curve.first, std::make_shared<RateCurve>(*curve.second)); // Deep copy each Curve
		}
		// Deep copy each Curve
		for (const auto& vol : other.vols) {
			vols.emplace(vol.first, std::make_shared<VolCurve>(*vol.second)); // Deep copy each Curve
		}
		bondPrices = other.bondPrices;
		stockPrices = other.stockPrices;
	};

	Market& operator=(const Market& other) {
		//cout << "assignment constructor is called by object@" << this << endl;
		if (this != &other) {  // Check for self-assignment
			asOf = other.asOf;
		}
		return *this;
	}

	//~Market() {
	//	//cout << "Market destructor is called" << endl;
	//	if (name != nullptr)
	//		delete name;
	//}

	void Print() const;
	void addCurve(const std::string& name, shared_ptr<RateCurve> curve);
	void addVolCurve(const std::string& name, shared_ptr<VolCurve> vol);
	void addBondPrice(const std::string& bondName, double price);
	void addStockPrice(const std::string& stockName, double price);

	inline void shockPrice(const string& underlying, double shock) { stockPrices[underlying] += shock; }
	inline shared_ptr<RateCurve> getCurve(const string& name) const { return curves.at(name); };
	inline shared_ptr<VolCurve> getVolCurve(const string& name) const { return vols.at(name); };

	inline double getbondPrice(const string& name) const { return bondPrices.at(name); };
	inline double getstockPrice(const string& name) const { return stockPrices.at(name); };

private:

	unordered_map<string, shared_ptr<VolCurve>> vols;
	unordered_map<string, shared_ptr<RateCurve>> curves;
	unordered_map<string, double> bondPrices;
	unordered_map<string, double> stockPrices;
};

std::ostream& operator<<(std::ostream& os, const Market& obj);
std::istream& operator>>(std::istream& is, Market& obj);

#endif
