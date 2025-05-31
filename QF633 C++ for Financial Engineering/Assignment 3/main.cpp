#include <iostream>
#include <fstream>
#include <vector>
#include <iomanip> // for setprecision

#include "black.h"
#include "trade.h"

using namespace std;

struct PvResult
{
	string trade_id;
	string trade_info;
	double pv;
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

double convertNotional(const string& str) {
	// Check if the last character is 'k' or 'K'
	if (str.back() == 'k' || str.back() == 'K') {
		// Remove 'k' and convert the remaining part to a double
		return stod(str.substr(0, str.size() - 1)) * 1000;
	}
	// If there's no 'k', just convert the whole string
	return stod(str);
}

void loadTradeFromFile(vector<Trade*>& tradesSet, const string& filename)
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
		cout << "Skipped first row: " << line << endl; // Optional: Print skipped line
	};

	while (getline(input_file, line))
	{
		// Add each line to our vector
		//lines.push_back(line);
		cout << "Processing line: " << line << endl;

		// You could also process each line immediately here
		// use split function to get the neede information for trade

		if (line.size() != 0) {
			vector<string> lineOfTrade = split(line, ";");
			string trade_id = lineOfTrade[0];
			double notional = convertNotional(lineOfTrade[1]);
			double strike = stod(lineOfTrade[2]);
			double isCall = lineOfTrade[3] == "true" ? true : false;

			Date start = Date(lineOfTrade[4]);
			Date end = Date(lineOfTrade[5]);

			Trade* optTrade = new OptionTrade(trade_id, notional, strike, start, end, isCall);

			tradesSet.push_back(optTrade);
		}

	}
}

void writeTofile(vector<PvResult>& result, const string& filename)
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

	// Write header line
	outfile << left << setw(20) << "trade id" << setw(75) << "trade info" << setw(20) << "trade pv" << "\n";

	// Write separator line
	outfile << string(120, '-') << "\n";

	// Write each struct in a formatted way
	for (const auto& re : result)
	{
		outfile << left << setw(20) << re.trade_id
			<< right << setw(75) << re.trade_info
			<< left << setw(20) << fixed << setprecision(2) << re.pv << "\n";
	}
}

int main()
{
	cout << "compute option pv task is started." << endl;
	vector<Trade*> tradesSet; // base class pointer but need to create option trade object
	string file = "../trades.txt";
	loadTradeFromFile(tradesSet, file);
	vector<PvResult> pvResult;
	double spot = 100;
	double vol = .2;
	double rate = 0.045;

	for (auto& trade : tradesSet)
	{
		string trade_id = trade->getTradeId();
		string trade_details = trade->getTradeDetails();
		double pv = trade->calculatePv(spot, vol, rate);

		pvResult.push_back({ trade_id, trade_details, pv });
	}

	writeTofile(pvResult, "../result.txt");

	// Cleaning up (Deleting the allocated memory)
	for (auto& obj : tradesSet)
	{
		delete obj;
	}

	// Clearing the vector (removes dangling pointers)
	tradesSet.clear();

	cout << "compute option pv task is completed." << endl;
	return 0;
}