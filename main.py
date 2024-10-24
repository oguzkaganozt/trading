#!/usr/bin/env python3
from strategies.dbv import DBV
from multiprocessing import Pool

coin_list = ["XBTUSD", "ETHUSD", "SOLUSD", "ENJUSD", "DOTUSD", "AVAXUSD", "ADAUSD", "LINKUSD", "BCHUSD", "LTCUSD", "XRPUSD"]
# coin_list = ["BTCUSD"]
strategies = [DBV(symbol=coin, interval="1d", balance=1000, risk_percentage=50, stop_loss_percentage=10) for coin in coin_list]

def run_backtest(strategy):
    return strategy.backtest(100)

def main():
    # Use a process pool to run backtests in parallel
    with Pool() as pool:
        results = pool.map(run_backtest, strategies)

if __name__ == "__main__":
    main()
