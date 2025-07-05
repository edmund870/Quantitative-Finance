#include <fstream>
#include <ctime>
#include <chrono>
#include <algorithm>
#include <iomanip> // for setprecision

#include "Market.h"
#include "Pricer.h"
#include "EuropeanTrade.h"
#include "Bond.h"
#include "Swap.h"
#include "AmericanTrade.h"
#include "black.h"

using namespace std;

struct PvResult {
	string value_date;
	string trade_id;
	string trade_name;
	double pv;
};

struct PricingError {
	string trade_name;
	int steps;
	double black_pv;
	double tree_pv;
	double error;
};

vector<string> split(const string& str, const string& delimiter)
{
	vector<string> tokens;
	size_t start = 0;
	size_t end = str.find(delimiter);

	while (end != string::npos)
	{
		tokens.push_back(str.substr(start, end - start));
		start = end + delimiter.length();
		end = str.find(delimiter, start);
	}

	tokens.push_back(str.substr(start));
	return tokens;
}

double tenorToYears(const string& tenor) {
	if (tenor == "ON") return 1.0 / 365.0; // Overnight = 1 day
	if (tenor == "3M") return 3.0 / 12.0;  // 3 months = 0.25 years
	if (tenor == "6M") return 6.0 / 12.0;  // 6 months = 0.5 years
	if (tenor == "9M") return 9.0 / 12.0;  // 9 months = 0.75 years
	if (tenor == "1Y") return 1.0;          // 1 year
	if (tenor == "2Y") return 2.0;          // 2 years
	if (tenor == "5Y") return 5.0;          // 5 years
	if (tenor == "10Y") return 10.0;        // 10 years
	return 0.0; // Default: unknown tenor
}

Date addTenorToDate(const time_t& date, const string& tenor) {
	const time_t ONE_DAY = 24 * 60 * 60;
	double days = tenorToYears(tenor) * 365.0;

	// Seconds since the start of epoch
	time_t date_seconds = date + (days * ONE_DAY);
	Date future_date;

	struct tm timeInfo;
	if (localtime_s(&timeInfo, &date_seconds) == 0) {
		// localtime_s() convert current system time into localtime and populate tm struct
		future_date.year = timeInfo.tm_year + 1900; //1900 based
		future_date.month = timeInfo.tm_mon + 1; //0 based
		future_date.day = timeInfo.tm_mday;
	};

	return future_date;
}

void readFromFile(const string& fileName, string& outPut) {
	string lineText;
	ifstream MyReadFile(fileName);
	while (getline(MyReadFile, lineText)) {
		outPut.append(lineText);
	}
	MyReadFile.close();
}

void loadDataFromFile(Market& mkt, const string& filename, const time_t& today)
{
	// Open the file for reading
	ifstream input_file(filename);
	vector<string> lines;

	// Check if the file was opened successfully
	if (!input_file.is_open())
	{
		cerr << "Error: Could not open file '" << filename << "'" << endl;
	}

	string line;
	if (filename == "curve.txt") {
		RateCurve curve;
		string header;

		if (getline(input_file, line)) {
			header = line;
		};

		while (getline(input_file, line))
		{
			if (line.size() != 0) {
				vector<string> lineOfTrade = split(line, ":");

				Date future_date = addTenorToDate(today, lineOfTrade[0]);

				string pct = lineOfTrade[1];
				pct.erase(remove(pct.begin(), pct.end(), '%'), pct.end());
				double convert_pct = stod(pct) / 100;

				curve.addRate(future_date, convert_pct);
			}
		}

		mkt.addCurve(header, curve);
	}
	else if (filename == "vol.txt") {
		VolCurve curve;
		string header = "Vol Curve";

		while (getline(input_file, line))
		{
			if (line.size() != 0) {
				vector<string> lineOfTrade = split(line, ":");

				Date future_date = addTenorToDate(today, lineOfTrade[0]);

				string pct = lineOfTrade[1];
				pct.erase(remove(pct.begin(), pct.end(), '%'), pct.end());
				double convert_pct = stod(pct) / 100;

				curve.addVol(future_date, convert_pct);
			}
		}
		mkt.addVolCurve(header, curve);
	}
	else if (filename == "bondPrice.txt") {
		while (getline(input_file, line))
		{
			if (line.size() != 0) {
				vector<string> lineOfTrade = split(line, ":");

				string bond = lineOfTrade[0];
				double price = stod(lineOfTrade[1]);

				mkt.addBondPrice(bond, price);
			}
		}
	}
	else if (filename == "stockPrice.txt") {
		while (getline(input_file, line))
		{
			if (line.size() != 0) {
				vector<string> lineOfTrade = split(line, ":");

				string stock = lineOfTrade[0];
				double price = stod(lineOfTrade[1]);

				mkt.addStockPrice(stock, price);
			}
		}
	}
}

void loadTradeFromFile(vector<Trade*>& tradesSet, const string& filename, const Date& today)
{
	/*
	load trade data from file
	insert into vector
	*/

	// Open the file for reading
	ifstream input_file(filename);
	vector<string> lines;

	// Check if the file was opened successfully
	if (!input_file.is_open())
	{
		cerr << "Error: Could not open file '" << filename << "'" << endl;
	}

	string line;
	// Read the file line by line
	if (getline(input_file, line)) {
		std::cout << "Skipped first row: " << line << endl; // Optional: Print skipped line
	};

	while (getline(input_file, line))
	{
		// Add each line to our vector
		//lines.push_back(line);
		std::cout << "Processing line: " << line << endl;

		// You could also process each line immediately here
		// use split function to get the neede information for trade

		if (line.size() != 0) {
			vector<string> lineOfTrade = split(line, ";");
			string trade_id = lineOfTrade[0];
			string type = lineOfTrade[1];

			Date trade_dt = Date(stoi(lineOfTrade[2].substr(0, 4)), stoi(lineOfTrade[2].substr(6, 2)), stoi(lineOfTrade[2].substr(9, 2)));
			Date start_dt = Date(stoi(lineOfTrade[3].substr(0, 4)), stoi(lineOfTrade[3].substr(6, 2)), stoi(lineOfTrade[3].substr(9, 2)));
			Date end_dt = Date(stoi(lineOfTrade[4].substr(0, 4)), stoi(lineOfTrade[4].substr(6, 2)), stoi(lineOfTrade[4].substr(9, 2)));

			double notional = stod(lineOfTrade[5]);
			string instr = lineOfTrade[6];
			double rate = stod(lineOfTrade[7]);
			double strike = stod(lineOfTrade[8]);
			double freq = stod(lineOfTrade[9]);
			string option = lineOfTrade[10];

			Trade* trade = nullptr;
			Black* trade_black = nullptr;

			if (type == "bond") {
				transform(instr.begin(), instr.end(), instr.begin(), [](unsigned char c) { return std::toupper(c); });
				trade = new Bond(trade_id, instr, trade_dt, today, start_dt, end_dt, notional, rate, nullptr, freq, 100);
			}
			else if (type == "swap") {
				trade = new Swap(trade_id, trade_dt, today, end_dt, notional, rate, freq);
			}
			else if (type == "european" && option == "call") {
				trade = new EuropeanOption(trade_id, notional, Call, strike, end_dt, instr);
				trade_black = new Black(trade_id + "_Black_price", instr, notional, strike, end_dt, 0, 0.04, true);
			}
			else if (type == "european" && option == "put") {
				trade = new EuropeanOption(trade_id, notional, Put, strike, end_dt, instr);
				trade_black = new Black(trade_id + "_Black_price", instr, notional, strike, end_dt, 0, 0.04, false);
			}
			else if (type == "american" && option == "call") {
				trade = new AmericanOption(trade_id, notional, Call, strike, end_dt, instr);

			}
			else if (type == "american" && option == "put") {
				trade = new AmericanOption(trade_id, notional, Put, strike, end_dt, instr);

			}

			if (trade) {
				tradesSet.push_back(trade);
			}
			else {
				cerr << "Error: Failed to create trade object for line: " << line << endl;
			}

			if (trade_black) {
				tradesSet.push_back(trade_black);
			}
		}

	}
}

void writeTradeTofile(vector<PvResult>& result, const string& filename)
{
	/*
	load trade data from file
	insert into vector
	*/

	ofstream outfile(filename);
	if (!outfile)
	{
		cerr << "Error opening file for writing!" << endl;
	}

	outfile
		<< left << setw(20) << "value date"
		<< setw(20) << "trade id"
		<< setw(40) << "trade info"
		<< setw(20) << "trade pv" << "\n";

	// Write separator line
	outfile << string(120, '-') << "\n";

	// Write each struct in a formatted way
	for (const auto& re : result)
	{
		outfile
			<< left << setw(20) << re.value_date
			<< left << setw(20) << re.trade_id
			<< left << setw(40) << re.trade_name
			<< left << setw(20) << fixed << setprecision(2) << re.pv << "\n";
	}

	outfile << string(120, '-') << "\n";
}

void writeErrorTofile(vector<PricingError>& result, const string& filename)
{
	/*
	load trade data from file
	insert into vector
	*/

	ofstream outfile(filename, ios::app);
	if (!outfile)
	{
		cerr << "Error opening file for writing!" << endl;
	}

	outfile
		<< left << "Compare CRR binomial tree result for an european option vs Black model" << "\n";

	// Write separator line
	outfile << string(120, '-') << "\n";

	// Write each struct in a formatted way
	for (const auto& re : result)
	{
		outfile
			<< left << "Pricing Error For " << re.steps << " steps for " << re.trade_name << ": "
			<< left << setprecision(6) << re.error << "\n";
	}

}

int main()
{
	//task 1, create an market data object, and update the market data from from txt file
	Date valueDate;
	time_t t = time(nullptr);
	struct tm timeInfo;
	if (localtime_s(&timeInfo, &t) == 0) {
		// localtime_s() convert current system time into localtime and populate tm struct
		valueDate.year = timeInfo.tm_year + 1900; //1900 based
		valueDate.month = timeInfo.tm_mon + 1; //0 based
		valueDate.day = timeInfo.tm_mday;
	};
	std::cout << valueDate << endl;
	//Date newDate;
	//cin >> newDate;
	//cout << newDate;

	Market mkt0;
	Market mkt1 = Market(valueDate);
	Market mkt2(mkt1);
	Market mkt3;
	mkt3 = mkt2; //assignemnt constructor	

	vector<PvResult> pvResult;

	/*
	load data from file and update market object with data
	*/
	std::vector<std::string> filenames = { "curve.txt", "vol.txt", "stockPrice.txt", "bondPrice.txt" };
	for (const auto& filename : filenames) {
		loadDataFromFile(mkt1, filename, t);
	}

	mkt1.Print();

	//task 2, create a portfolio of bond, swap, european option, american option
	//for each time, at least should have long / short, different tenor or expiry, different underlying
	//totally no less than 16 trades
	vector<Trade*> myPortfolio;
	string file = "trade.txt";
	loadTradeFromFile(myPortfolio, file, valueDate);

	//task 3, creat a pricer and price the portfolio, output the pricing result of each deal.
	Pricer* treePricer = new CRRBinomialTreePricer(50);
	for (size_t i = 0; i < myPortfolio.size(); ++i) {
		double pv = treePricer->Price(mkt1, myPortfolio[i]);
		string id = myPortfolio[i]->getTradeid();
		string name = myPortfolio[i]->getTradeName();
		std::cout << id << " " << fixed << setprecision(6) << pv << std::endl;
		pvResult.push_back({
			to_string(valueDate.year) + "-" + to_string(valueDate.month) + "-" + to_string(valueDate.day),
			id,
			name,
			pv
			});
	}

	delete treePricer;

	writeTradeTofile(pvResult, "result.txt");

	//task 4, analyzing pricing result
	// a) compare CRR binomial tree result for an european option vs Black model
	// b) compare CRR binomial tree result for an american option call vs european option call, and put

	//final
	vector<PricingError> errors;
	for (int i = 100; i <= 10000; i += 100) {
		Pricer* treePricer = new CRRBinomialTreePricer(i);
		double EU_pv = treePricer->Price(mkt1, myPortfolio[3]);
		string name = myPortfolio[3]->getTradeName();

		double black_pv = treePricer->Price(mkt1, myPortfolio[4]);
		double error = black_pv - EU_pv;

		errors.push_back(
			{
				name,
				i,
				black_pv,
				EU_pv,
				black_pv - EU_pv
			}
		);

		delete treePricer;
	}

	writeErrorTofile(errors, "result.txt");


	std::cout << "Project build successfully!" << endl;
	return 0;

}
