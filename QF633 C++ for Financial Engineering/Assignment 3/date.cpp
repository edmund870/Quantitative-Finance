#include <cmath>
#include <iostream>
#include <ctime>
#include "date.h"

Date::Date(const string& dateStr)
{
	// substr() get the mid string from string using position index

	year = stoi(dateStr.substr(1, 4));
	month = stoi(dateStr.substr(6, 2));
	day = stoi(dateStr.substr(9, 2));

}

int Date::operator-(const Date& dt2)
{
    // Create tm structures for both dates
    tm thisDate = {};
    tm otherDate = {};

    thisDate.tm_year = this->year - 1900; // tm_year is years since 1900
    thisDate.tm_mon = this->month - 1;    // tm_mon is 0-indexed
    thisDate.tm_mday = this->day;

    otherDate.tm_year = dt2.year - 1900;
    otherDate.tm_mon = dt2.month - 1;
    otherDate.tm_mday = dt2.day;

    // Convert tm structures to time_t (epoch time)
    time_t time1 = mktime(&thisDate);
    time_t time2 = mktime(&otherDate);

    // Calculate the difference in seconds
    double diffInSeconds = difftime(time1, time2);

    // Convert seconds to days
    int diffInDays = diffInSeconds / (60 * 60 * 24); // Number of seconds in a day

    return diffInDays;
}