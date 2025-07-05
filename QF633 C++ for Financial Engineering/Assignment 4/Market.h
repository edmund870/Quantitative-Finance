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
		cout << "default market constructor is called by object@" << this << endl;
	}

	Market(const Date& now) : asOf(now) {
		cout << "market constructor is called by object@" << this << endl;
		name = new char[5];
		strcpy_s(name, 5, "test");
	}

	Market(const Market& other) : asOf(other.asOf) {
		cout << "copy constructor is called by object@" << this << endl;
		// deep copy behaviour
		if (other.name != nullptr) {
			name = new char[strlen(other.name) + 1];
			strcpy_s(name, strlen(other.name) + 1, other.name);
		}
	}

	Market& operator=(const Market& other) {
		cout << "assignment constructor is called by object@" << this << endl;
		if (this != &other) {  // Check for self-assignment
			asOf = other.asOf;
		}
		return *this;
	}

	~Market() {
		cout << "Market destructor is called" << endl;
		if (name != nullptr)
			delete name;
	}

	void Print() const;
	void addCurve(const std::string& curveName, const RateCurve& curve);//implement this
	void addVolCurve(const std::string& curveName, const VolCurve& curve);//implement this
	void addBondPrice(const std::string& bondName, double price);//implement this
	void addStockPrice(const std::string& stockName, double price);//implement this

	inline RateCurve getCurve(const string& name) const { return curves.at(name); };
	inline VolCurve getVolCurve(const string& name) const { return vols.at(name); };

	inline double getbondPrice(const string& name) const { return bondPrices.at(name); };
	inline double getstockPrice(const string& name) const { return stockPrices.at(name); };

private:

	unordered_map<string, VolCurve> vols;
	unordered_map<string, RateCurve> curves;
	unordered_map<string, double> bondPrices;
	unordered_map<string, double> stockPrices;
};

std::ostream& operator<<(std::ostream& os, const Market& obj);
std::istream& operator>>(std::istream& is, Market& obj);

#endif
