// Assignment 2.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include <iostream>
#include <fstream>
#include <vector>
#include <stdexcept>
#include <string>
#include <iomanip>

#include "black.h"

using namespace std;

struct OptionTrade
{
	int tradeid;
	double notional;
	double strike;
	double expiry;
	bool isCall;
};

double convertNotional(const string& str) {
	// Check if the last character is 'k' or 'K'
	if (str.back() == 'k' || str.back() == 'K') {
		// Remove 'k' and convert the remaining part to a double
		return stod(str.substr(0, str.size() - 1)) * 1000;
	}
	// If there's no 'k', just convert the whole string
	return stod(str);
}

void splitString(vector<string>& output, const string& inputLine, const char separator)
{
	output.clear();
	size_t start = 0;
	size_t end = inputLine.find(separator);

	while (end != string::npos) {
		output.push_back(inputLine.substr(start, end - start)); // Extract substring
		start = end + 1; // Move past the separator
		end = inputLine.find(separator, start); // Find next separator
	}
	output.push_back(inputLine.substr(start)); // Add last part of the string
}

void loadTradeFromFile(vector<OptionTrade>& tradesSet, const string& filePath)
{
	/*
	load trade data from file
	insert into vector
	*/
	ifstream inputFile(filePath); // Open the file
	try {
		if (inputFile) {
			string line;
			if (getline(inputFile, line)) {
				cout << "Skipped first row: " << line << endl; // Optional: Print skipped line
			}

			while (getline(inputFile, line)) { // Read each line
				cout << line << endl;    // Print the line (or process it)
				if (line.size() != 0) {
					vector<string> lineOfTrade;
					splitString(lineOfTrade, line, ';');

					int tradeId = stoi(lineOfTrade[0]);
					if (tradeId < 6) {
						OptionTrade ot;
						ot.tradeid = tradeId;
						ot.expiry = stod(lineOfTrade[4]); // casting string to double
						ot.isCall = lineOfTrade[3] == "true" ? true : false;
						ot.notional = convertNotional(lineOfTrade[1]);
						ot.strike = stod(lineOfTrade[2]);
						tradesSet.push_back(ot);
					}
				}
			}
			inputFile.close(); // Close the file

		}
		else
			cout << "file does not exsits" << endl;
	}
	catch (const exception& e) {
		cerr << e.what() << endl;
	}
}

void writeResultToFile(const vector<pair<int, double>>& result, const string& fileName)
{
	ofstream outputFile(fileName); // Create or open the file for writing
	if (!outputFile) {
		cerr << "Error: Could not create or open file!" << endl;
	}
	else {
		for (auto& re : result) {
			outputFile << "trade pv for ID " << re.first << ": " << fixed << setprecision(6) << re.second << endl;
		}
	}
	outputFile.close();
	cout << "Data written to file successfully!" << endl;
}

int main() {
	cout << "compute option pv task is started." << endl;

	vector<OptionTrade> tradesSet;

	string file = "../trades.txt";
	loadTradeFromFile(tradesSet, file);

	vector<pair<int, double>> pvResult;

	double spot = 100;
	double vol = .2;
	double rate = 0.045;

	for (auto& trade : tradesSet)
	{
		BlackScholes option = BlackScholes(
			trade.notional,
			spot,
			trade.strike,
			rate,
			vol,
			trade.expiry,
			trade.isCall
		);

		double pv = option.pv();

		pvResult.push_back({ trade.tradeid, pv });
	}

	/*
	save result back into a file
	*/
	writeResultToFile(pvResult, "../result.txt");
	cout << "compute option pv task is completed." << endl;
	return 0;
}

