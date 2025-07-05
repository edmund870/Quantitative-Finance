#ifndef PAYOFF_H
#define PAYOFF_H
#include "Types.h"

namespace PAYOFF
{
	inline double VanillaOption(OptionType optType, double strike, double S)
	{
		switch (optType)
		{
		case Call:
			return S > strike ? S - strike : 0;
		case Put:
			return S < strike ? strike - S : 0;
		case BinaryCall:
			return S >= strike ? 1 : 0;
		case BinaryPut:
			return S <= strike ? 1 : 0;
		default:
			throw "unsupported optionType";
		}
	}

	inline double CallSpread(double strike1, double strike2, double S)
	{
		if (S < strike1)
			return 0;
		else if (S > strike2)
			return 1;
		else
			return (S - strike1) / (strike2 - strike1);
	}
}
#endif
