#!/usr/bin/env python3
from strategies.dbv import DBV
import time

strategies = [DBV("DBV", "AAPL", 1, "day"), DBV("DBV", "AAPL", 4, "hour")]

# Traverse all all active strategies and update them
def run_strategies():
    for strategy in strategies:
        strategy.run()

def main():
    print("Welcome ..")

    while True:
        run_strategies()
        time.sleep(300) # sleep for 5 minutes
    
if __name__ == "__main__":
    main()
