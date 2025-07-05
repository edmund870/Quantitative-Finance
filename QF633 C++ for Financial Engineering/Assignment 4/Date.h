#ifndef DATE_H
#define DATE_H

#include <iostream>

class Date
{
public:
	int year = 0;
	int month = 0;
	int day = 0;
	Date(int y, int m, int d) : year(y), month(m), day(d) {};
	Date() {
		std::cout << "default Date constructor called" << std::endl;
	};

	Date addDays(int days) const;

	Date addMonths(int months) const;

	Date addYears(int years) const;

	bool isLeapYear() const;

	int daysInMonth() const;

	void normalize();
private:
	static const int days_in_months[12];
};

double operator-(const Date& d1, const Date& d2);
bool operator==(const Date& d1, const Date& d2);
std::ostream& operator<<(std::ostream& os, const Date& date);
std::istream& operator>>(std::istream& is, Date& date);

#endif
