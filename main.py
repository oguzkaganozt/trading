#!/usr/bin/env python3
from dbv import DBV
import time
from polygon_api import get_symbol_details, get_ohlc, get_rsi, get_macd, get_sma, get_ema, get_symbols, get_bbands
# strategies = [DBV("DBV", "AAPL", 1, "day"), DBV("DBV", "AAPL", 4, "hour")]

# Traverse all all active strategies and update them
# def run_strategies():
#     for strategy in strategies:
#         strategy.run()

def main():
    print("Welcome ..")

    # Check all datas are coming in correctly
    # get_symbol_details("AAPL")

    # data = get_ohlc("AAPL", "hour", 4, limit=60)
    # for i, entry in enumerate(data, start=1):
    #     print(f"{i}: {entry}")

    # data = get_rsi("X:BTCUSD", "day", 1, limit=60)
    # for i, entry in enumerate(data, start=1):
    #     print(f"{i}: {entry}")

    # get_macd("AAPL", "day", 10)
    # get_macd("AAPL", "hour", 10)
    # get_macd("AAPL", "minute", 10)

    data = get_sma("X:BTCUSD", "day", 1, limit=60)

    for i, entry in enumerate(data, start=1):
        print(f"{i}: {entry}")

    # get_ema("AAPL", "day", 10)
    # get_ema("AAPL", "hour", 10)
    # get_ema("AAPL", "minute", 10)

    # get_bbands("AAPL", "day", 10)
    # get_bbands("AAPL", "hour", 10)
    # get_bbands("AAPL", "minute", 10)

    # while True:
    #     run_strategies()
    
if __name__ == "__main__":
    main()
