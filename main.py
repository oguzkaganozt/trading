#!/usr/bin/env python3
from strategies.rsi_sma import RSI_SMA
from strategies.mfi_sma import MFI_SMA
from strategies.macd_mfi import MACD_MFI
from multiprocessing import Pool

# coin_list = ["BTCUSD", "ETHUSD", "SOLUSD", "LTCUSD"]
coin_list = ["BTCUSD"]
# strategies = [RSI_SMA(symbol=coin, interval="1d", balance=1000, risk_percentage=100, stop_loss_percentage=0) for coin in coin_list]
# strategies = [MFI_SMA(symbol=coin, interval="1d", balance=1000, risk_percentage=100, stop_loss_percentage=0) for coin in coin_list]
strategies = [MACD_MFI(symbol=coin, interval="1d", parent_interval="1w", balance=1000, risk_percentage=100, stop_loss_percentage=0) for coin in coin_list]

def run_backtest(strategy):
    return strategy.backtest(300)

def main():
    # Use a process pool to run backtests in parallel
    with Pool() as pool:
        results = pool.map(run_backtest, strategies)

if __name__ == "__main__":
    main()
