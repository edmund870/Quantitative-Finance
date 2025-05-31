// Assignment_1.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include <iostream>
#include <fstream>
#include <string>
#include <vector>

using namespace std;

void output2File(const string& fileName, vector<string> sizes) {
	try {
		// Writing to a file
		ofstream outputFile(fileName);
		if (outputFile.is_open()) {
			cout << "Save result information to a text file named " << fileName << endl;
			for (string size : sizes) {
				outputFile << size << endl;
			}
			cout << "Data written to the file" << fileName << endl;
			// Close the file
			outputFile.close();
		}
	}
	catch (const exception& e) {
		cerr << "Error opening the file for writing." << endl;
	}
}

void readFile(const string& fileName) {
	try {
		// reading from file
		ifstream inputFile(fileName);
		if (inputFile.is_open()) {
			cout << "Reading the saved information from " << fileName << " and display it back to the user" << endl;
			string line;
			while (getline(inputFile, line)) {
				cout << line << endl;
			}
			// Close the file
			inputFile.close();
		}
	}
	catch (const exception& e) {
		cerr << "Error opening the file for reading." << endl;
	}
}

int main()
{
	vector<string> sizes;

	cout << "ASSIGNMENT 1: EDMUND CHIA" << endl;

	cout << "Display the sizes (in bytes) of basic data types (e.g., int, float, double, char, bool) using the sizeof operator" << endl;

	cout << "The size of int: " << sizeof(int) << endl;
	cout << "The size of char: " << sizeof(char) << endl;
	cout << "The size of bool: " << sizeof(bool) << endl;
	cout << "The size of short: " << sizeof(short) << endl;
	cout << "The size of long: " << sizeof(long) << endl;
	cout << "The size of unsigned long: " << sizeof(unsigned long) << endl;
	cout << "The size of size_t: " << sizeof(size_t) << endl; //unsigned long
	cout << "The size of float: " << sizeof(float) << endl;
	cout << "The size of double: " << sizeof(double) << endl;
	cout << endl;


	sizes.push_back("The size of int: " + to_string(sizeof(int)));
	sizes.push_back("The size of char: " + to_string(sizeof(char)));
	sizes.push_back("The size of bool: " + to_string(sizeof(bool)));
	sizes.push_back("The size of short: " + to_string(sizeof(short)));
	sizes.push_back("The size of long: " + to_string(sizeof(long)));
	sizes.push_back("The size of unsigned long: " + to_string(sizeof(unsigned long)));
	sizes.push_back("The size of size_t: " + to_string(sizeof(size_t)));
	sizes.push_back("The size of float: " + to_string(sizeof(float)));
	sizes.push_back("The size of double: " + to_string(sizeof(double)));


	string filename = "output.txt";

	output2File(filename, sizes);

	cout << endl;

	readFile(filename);

	return 0;
}