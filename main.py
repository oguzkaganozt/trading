#!/usr/bin/env python3
from dbv import DBV
import pandas as pd
import pandas_ta as ta
strategies = [DBV("X:BTCUSD", "hour", 4, 1000)]

# Traverse all all active strategies and update them
def run_strategies():
    for strategy in strategies:
        strategy.run()

def main():
    print("Hello World")
    # help(ta.sma)
    # run_strategies()
    strategies[0].backtest(100)
    
    # Wait for user input to exit
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
