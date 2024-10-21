#!/usr/bin/env python3
from dbv import DBV
import pandas as pd
import pandas_ta as ta
from polygon_api import kraken_request, get_ohlc
# coin_list = ["XBTUSD", "ETHUSD", "SOLUSD", "ENJUSD", "DOTUSD", "AVAXUSD", "ADAUSD", "LINKUSD", "BCHUSD", "LTCUSD", "XRPUSD"]
coin_list = ["XBTUSD"]
strategies = [DBV(coin, "1d", 1000) for coin in coin_list]

# Traverse all all active strategies and update them
def run_strategies():
    for strategy in strategies:
        strategy.run()

def main():
    print("Hello World")
    
    for strategy in strategies:
        strategy.backtest(100)
    
    # Wait for user input to exit
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
