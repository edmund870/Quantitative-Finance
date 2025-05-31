#pragma once

#include <string>

using namespace std;

class Date
{
public:
	Date() {};
	Date(const string &dateStr);

	int operator-(const Date &dt2);

private:
	int year = 1900;
	int month = 1;
	int day = 1;
};

