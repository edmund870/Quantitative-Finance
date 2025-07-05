#include "Date.h"
#include <ctime>

// Days in each month (not accounting for leap years)
const int Date::days_in_months[12] = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };

// Check if the current year is a leap year
bool Date::isLeapYear() const {
    return (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0));
}

// Get the number of days in the current month
int Date::daysInMonth() const {
    if (month == 2) { // February
        return isLeapYear() ? 29 : 28;
    }
    return days_in_months[month - 1];
}

// Normalize the date (handling overflow into next month/year)
void Date::normalize() {
    // Normalize day if it's more than the days in the current month
    while (day > daysInMonth()) {
        day -= daysInMonth();
        month++;
        if (month > 12) {
            month = 1;
            year++;
        }
    }

    // Normalize day if it's less than 1 (handle underflow)
    while (day < 1) {
        month--;
        if (month < 1) {
            month = 12;
            year--;
        }
        day += daysInMonth();
    }
}

// Add days to the current date
Date Date::addDays(int days) const {
    Date result = *this;
    result.day += days;
    result.normalize();
    return result;
}

// Add months to the current date
Date Date::addMonths(int months) const {
    Date result = *this;
    result.month += months;
    while (result.month > 12) {
        result.month -= 12;
        result.year++;
    }
    while (result.month < 1) {
        result.month += 12;
        result.year--;
    }
    if (result.day > result.daysInMonth()) {
        result.day = result.daysInMonth();
    }
    return result;
}

// Add years to the current date
Date Date::addYears(int years) const {
    Date result = *this;
    result.year += years;
    if (result.month == 2 && result.day == 29 && !result.isLeapYear()) {
        result.day = 28;
    }
    return result;
}


//return date difference in fraction of year
double operator-(const Date& d1, const Date& d2)
{
	// Create tm structures for both dates
	tm thisDate = {};
	tm otherDate = {};

	thisDate.tm_year = d1.year - 1900; // tm_year is years since 1900
	thisDate.tm_mon = d1.month - 1;    // tm_mon is 0-indexed
	thisDate.tm_mday = d1.day;

	otherDate.tm_year = d2.year - 1900;
	otherDate.tm_mon = d2.month - 1;
	otherDate.tm_mday = d2.day;

	// Convert tm structures to time_t (epoch time)
	time_t time1 = mktime(&thisDate);
	time_t time2 = mktime(&otherDate);

	// Calculate the difference in seconds
	double diffInSeconds = difftime(time1, time2);

	// Convert seconds to days
	int diffInDays = diffInSeconds / (60 * 60 * 24); // Number of seconds in a day

	return diffInDays;
}

bool operator==(const Date& d1, const Date& d2)
{
	return d1.year == d2.year && d1.month == d2.month && d1.day == d2.day;
}

std::ostream& operator<<(std::ostream& os, const Date& d)
{
	os << d.year << "-" << d.month << "-" << d.day << std::endl;
	return os;
}

std::istream& operator>>(std::istream& is, Date& d)
{
	is >> d.year >> d.month >> d.day;
	return is;
}
