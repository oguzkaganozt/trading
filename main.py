#!/usr/bin/env python3
from strategies.dbv import DBV

# coin_list = ["XBTUSD", "ETHUSD", "SOLUSD", "ENJUSD", "DOTUSD", "AVAXUSD", "ADAUSD", "LINKUSD", "BCHUSD", "LTCUSD", "XRPUSD"]
coin_list = ["BTCUSD"]
strategies = [DBV(symbol=coin, interval="1d", balance=1000, risk_percentage=100, stop_loss_percentage=10) for coin in coin_list]

# Traverse all all active strategies and update them
def run_strategies():
    for strategy in strategies:
        strategy.run()

def main():    
    for strategy in strategies:
        strategy.backtest(100)
    
    # Wait for user input to exit
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
