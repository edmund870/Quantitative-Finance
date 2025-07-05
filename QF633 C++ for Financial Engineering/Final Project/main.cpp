#include <fstream>
#include <ctime>
#include <chrono>
#include <algorithm>
#include <iomanip> // for setprecision
#include <memory>

#include "TradeFactory.h"
#include "Market.h"
#include "Pricer.h"
#include "EuropeanTrade.h"
#include "Bond.h"
#include "Swap.h"
#include "AmericanTrade.h"
#include "black.h"
#include "threadpool.h"
#include "RiskEngine.h"

using namespace std;

struct TradeResult
{
	string value_date;
	string id;
	string trade_name;
	double PV = 0;
	double DV01 = 0;
	double Vega = 0;
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
	// handling for rate curve
	if (filename == "sgd_curve.txt") {
		shared_ptr<RateCurve> curve = std::make_shared<RateCurve>();
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

				curve->addRate(future_date, convert_pct);
			}
		}

		mkt.addCurve(header, curve);
	}
	else if (filename == "usd_curve.txt") {
		shared_ptr<RateCurve> curve = std::make_shared<RateCurve>();
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

				curve->addRate(future_date, convert_pct);
			}
		}

		mkt.addCurve(header, curve);
	}
	// handling for vol curve
	else if (filename == "vol.txt") {
		auto curve = make_shared<VolCurve>();
		string header = "LOGVOL";

		while (getline(input_file, line))
		{
			if (line.size() != 0) {
				vector<string> lineOfTrade = split(line, ":");

				Date future_date = addTenorToDate(today, lineOfTrade[0]);

				string pct = lineOfTrade[1];
				pct.erase(remove(pct.begin(), pct.end(), '%'), pct.end());
				double convert_pct = stod(pct) / 100;

				curve->addVol(future_date, convert_pct);
			}
		}
		mkt.addVolCurve(header, curve);
	}
	// handling for bond price
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
	// handling for stock price
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

void loadTradeFromFile(vector<shared_ptr<Trade>>& tradesSet, const string& filename, const Date& today)
{
	/*
	load trade data from file
	insert into vector
	*/

	// Open the file for reading
	ifstream input_file(filename);
	vector<string> lines;
	auto lFactory = make_unique<LinearTradeFactory>();
	auto oFactory = make_unique<OptionTradeFactory>();

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
		std::cout << "Processing line: " << line << endl;

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
			string direction = lineOfTrade[11];


			if (type == "bond") {
				//convert to uppercase
				transform(instr.begin(), instr.end(), instr.begin(), [](unsigned char c) { return toupper(c); });

				auto bond = lFactory->createTrade(trade_id, "bond", trade_dt, start_dt, end_dt);
				auto bond_ptr = dynamic_pointer_cast<Bond>(bond);

				//setting bond parameters
				bond_ptr->setValueDate(today);
				bond_ptr->setCoupon(rate);
				bond_ptr->setFrequency(freq);
				bond_ptr->setNotional(notional);
				bond_ptr->settradePrice(100);
				bond_ptr->setUnderlying(instr);
				bond_ptr->setdirection(direction);
				bond_ptr->updateBondName();
				bond_ptr->updateBaseTradeName();
				bond_ptr->generateBondSchedule();

				tradesSet.push_back(bond);
			}
			else if (type == "swap") {
				//convert to uppercase
				transform(instr.begin(), instr.end(), instr.begin(), [](unsigned char c) { return toupper(c); });

				auto swap = lFactory->createTrade(trade_id, "swap", trade_dt, start_dt, end_dt);
				auto swap_ptr = dynamic_pointer_cast<Swap>(swap);

				//setting swap parameters
				swap_ptr->setValueDate(today);
				swap_ptr->setFrequency(freq);
				swap_ptr->setNotional(notional);
				swap_ptr->setCurvename(instr);
				swap_ptr->setRate(rate);
				swap_ptr->setdirection(direction);
				swap_ptr->updateSwapName();
				swap_ptr->updateBaseTradeName();
				swap_ptr->generateSwapSchedule();

				tradesSet.push_back(swap);
			}
			else if (type == "european") {
				auto eoption = oFactory->createTrade(trade_id, "european", trade_dt, start_dt, end_dt);
				auto eOpt = dynamic_pointer_cast<EuropeanOption>(eoption);

				auto blackeoption = oFactory->createTrade(trade_id + "_Black_price", "black", trade_dt, start_dt, end_dt);
				auto blackeOpt = dynamic_pointer_cast<Black>(blackeoption);

				//setting european option parameters
				eOpt->setNotional(notional);
				eOpt->setStrike(strike);
				eOpt->setUnderlying(instr);
				eOpt->setdirection(direction);
				eOpt->setCurvename("USD-SOFR"); // assume all use USD rate curve
				eOpt->setVolname("LOGVOL");

				//setting european option parameters using black scholes
				blackeOpt->setToday(today);
				blackeOpt->setNotional(notional);
				blackeOpt->setStrike(strike);
				blackeOpt->setUnderlying(instr);
				blackeOpt->setdirection(direction);
				blackeOpt->setCurvename("USD-SOFR"); // assume all use USD rate curve
				blackeOpt->setVolname("LOGVOL");

				if (option == "call") {
					eOpt->setOptionType(Call);
					blackeOpt->setisCall(1);
				}
				else if (option == "put") {
					eOpt->setOptionType(Put);
					blackeOpt->setisCall(0);
				};

				eOpt->updateOptionName();
				eOpt->updateTreeProductTradeName();
				blackeOpt->updateBlackName();
				blackeOpt->updateBaseTradeName();

				tradesSet.push_back(eoption);
				tradesSet.push_back(blackeoption);
			}

			else if (type == "american") {
				auto amoption = oFactory->createTrade(trade_id, "american", trade_dt, start_dt, end_dt);
				auto amOpt = dynamic_pointer_cast<AmericanOption>(amoption);

				//setting american option parameters
				amOpt->setNotional(notional);
				amOpt->setStrike(strike);
				amOpt->setUnderlying(instr);
				amOpt->setdirection(direction);
				amOpt->setCurvename("USD-SOFR"); // assume all use USD rate curve
				amOpt->setVolname("LOGVOL");

				if (option == "call") {
					amOpt->setOptionType(Call);
				}
				else if (option == "put") {
					amOpt->setOptionType(Put);
				};

				amOpt->updateOptionName();
				amOpt->updateTreeProductTradeName();

				tradesSet.push_back(amoption);
			}
		}

	}
}

void outPutResult(vector<TradeResult>& result, const string& filename)
{
	ofstream outfile(filename);
	if (!outfile)
	{
		cerr << "Error opening file for writing!" << endl;
	}
	outfile
		<< left << setw(20) << "value date"
		<< setw(20) << "trade id"
		<< setw(40) << "trade info"
		<< setw(20) << "trade pv"
		<< setw(20) << "Delta"
		<< setw(20) << "Vega" << "\n";

	// Write separator line
	outfile << string(140, '-') << "\n";

	// Write each struct in a formatted way
	for (const auto& re : result)
	{
		outfile
			<< left << setw(20) << re.value_date
			<< left << setw(20) << re.id
			<< left << setw(40) << re.trade_name
			<< left << setw(20) << fixed << setprecision(2) << re.PV
			<< left << setw(20) << fixed << setprecision(6) << re.DV01
			<< left << setw(20) << fixed << setprecision(6) << re.Vega << "\n";
	}

	outfile << string(140, '-') << "\n";
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
	//create an market data object, and update the market data from from txt file
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
	auto mkt = make_shared<Market>(valueDate);


	//loading market 
	vector<string> filenames = { "sgd_curve.txt", "usd_curve.txt", "vol.txt", "stockPrice.txt", "bondPrice.txt" };
	for (const auto& filename : filenames) {
		loadDataFromFile(*mkt, filename, t);
	}

	mkt->Print();

	//creating trade factory
	vector<shared_ptr<Trade>> myPortfolio;
	string file = "trade.txt";
	loadTradeFromFile(myPortfolio, file, valueDate);

	//Pricing Portfolio
	auto treePricer = make_shared<CRRBinomialTreePricer>(50);

	//using single thread
	vector<TradeResult> result;
	string str_value_date = to_string(valueDate.year) + "-" + to_string(valueDate.month) + "-" + to_string(valueDate.day);

	auto start = chrono::high_resolution_clock::now();
	for (size_t i = 0; i < myPortfolio.size(); ++i) {
		double pv = treePricer->Price(*mkt, myPortfolio[i]);
		string id = myPortfolio[i]->getTradeid();
		string name = myPortfolio[i]->getTradeName();
		std::cout << id << " " << fixed << setprecision(6) << pv << endl;
		TradeResult re;
		re.value_date = str_value_date;
		re.id = id;
		re.trade_name = name;
		re.PV = pv;
		result.push_back(re);
	}
	auto end = chrono::high_resolution_clock::now();
	auto duration = chrono::duration_cast<chrono::microseconds>(end - start).count();
	std::cout << "PV Sequential Execution Time: " << duration << " microseconds" << endl;

	//creating risk engine
	double curve_shock = 0.0001;// 1 bp of zero rate
	double vol_shock = 0.01; //1% of log normal vol
	double price_shock = 1.0; // shock in abs price of stock
	//string risk_id = "USD-SOFR:DV01:DEAL 01";
	RiskEngine risk(*mkt, curve_shock, vol_shock, price_shock);

	start = chrono::high_resolution_clock::now();
	for (size_t i = 0; i < myPortfolio.size(); ++i) {
		risk.computeRisk("dv01", myPortfolio[i], true);
		result[i].DV01 = risk.getResult()[myPortfolio[i]->getCurvename()];

		risk.computeRisk("vega", myPortfolio[i], true);
		result[i].Vega = risk.getResult()[myPortfolio[i]->getVolname()];
	}
	end = chrono::high_resolution_clock::now();
	duration = chrono::duration_cast<chrono::microseconds>(end - start).count();
	std::cout << "Risk Sequential Execution Time: " << duration << " microseconds" << endl;


	outPutResult(result, "result.txt");


	result.clear();
	vector<TradeResult> multithread_result;
	// using multi thread
	mutex cvMutex;
	mutex resultMutex;
	condition_variable cv;
	atomic<int> tasksRemaining(0);

	for (size_t i = 0; i < myPortfolio.size(); ++i) {
		TradeResult re;
		re.value_date = str_value_date;
		re.id = myPortfolio[i]->getTradeid();
		multithread_result.push_back(re);
	}

	// Get hardware concurrency (number of available CPU threads)
	size_t hardwareConcurrency = thread::hardware_concurrency();

	ThreadPool pool(hardwareConcurrency);

	start = chrono::high_resolution_clock::now();
	// Enqueue tasks for execution 
	for (size_t i = 0; i < myPortfolio.size(); ++i) {
		tasksRemaining++;

		pool.enqueue([&, i] {
			// Pricing logic
			auto mt_treePricer = make_shared<CRRBinomialTreePricer>(50);
			double pv = mt_treePricer->Price(*mkt, myPortfolio[i]);
			multithread_result[i].PV = pv;
			string name = myPortfolio[i]->getTradeName();
			multithread_result[i].trade_name = myPortfolio[i]->getTradeName();

			tasksRemaining--;
			cv.notify_one();
			}
		);
	}

	{
		unique_lock<mutex> lock(cvMutex);
		cv.wait(lock, [&] { return tasksRemaining == 0; });
	}

	end = chrono::high_resolution_clock::now();
	duration = chrono::duration_cast<chrono::microseconds>(end - start).count();
	std::cout << "PV Parallel Execution Time (ThreadPool): " << duration << " microseconds" << endl;

	start = chrono::high_resolution_clock::now();
	// Enqueue tasks for execution 
	for (size_t i = 0; i < myPortfolio.size(); ++i) {
		tasksRemaining++;

		pool.enqueue([&, i] {
			auto mt_risk = make_shared<RiskEngine>(*mkt, curve_shock, vol_shock, price_shock);

			mt_risk->computeRisk("dv01", myPortfolio[i], true);
			multithread_result[i].DV01 = mt_risk->getResult()[myPortfolio[i]->getCurvename()];

			mt_risk->computeRisk("vega", myPortfolio[i], true);
			multithread_result[i].Vega = mt_risk->getResult()[myPortfolio[i]->getVolname()];

			tasksRemaining--;
			cv.notify_one();
			}
		);
	}

	{
		unique_lock<mutex> lock(cvMutex);
		cv.wait(lock, [&] { return tasksRemaining == 0; });
	}

	end = chrono::high_resolution_clock::now();
	duration = chrono::duration_cast<chrono::microseconds>(end - start).count();
	std::cout << "Risk Parallel Execution Time (ThreadPool): " << duration << " microseconds" << endl;

	std::cout << "Project build successfully!" << endl;
	std::cout << "Thanks PROF! This is my last module for MQF, thank you for the semester" << endl;
	return 0;

}
