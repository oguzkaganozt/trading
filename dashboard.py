#!/usr/bin/env python3
import streamlit as st
import pandas as pd
from strategies.rsi_sma import RSI_SMA
from strategies.mfi_sma import MFI_SMA
from strategies.macd_mfi import MACD_MFI
from multiprocessing import Pool

def run_backtest(strategy):
    return strategy.backtest(300)

def get_strategy_class(strategy_name):
    strategy_map = {
        "RSI-SMA": RSI_SMA,
        "MFI-SMA": MFI_SMA,
        "MACD-MFI": MACD_MFI
    }
    return strategy_map.get(strategy_name)

def show_dashboard():
    st.title("Backtesting Dashboard")
    
    # Strategy selection
    strategy = st.selectbox(
        "Select Trading Strategy",
        ["RSI-SMA", "MFI-SMA", "MACD-MFI"]
    )
    
    # Coin selection (allowing multiple)
    coins = st.multiselect(
        "Select Trading Pairs",
        ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT"],
        default=["BTC/USDT"]
    )
    
    # Timeframe selection
    timeframe = st.select_slider(
        "Select Timeframe",
        options=["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "15d"],
        value="1d"
    )

    # Parent interval selection
    parent_interval = st.select_slider(
        "Select Parent Interval",
        options=["1h", "4h", "1d", "1w", "15d"],
        value="1w"
    )

    # Duration selection
    duration = st.select_slider(
        "Select Duration",
        options=[100, 200, 300, 400, 500],
        value=300
    )
    
    # Trading parameters in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        balance = st.number_input(
            "Enter Initial Balance (USDT)",
            min_value=0.0,
            value=1000.0,
            step=100.0
        )
    
    with col2:
        risk_percentage = st.slider(
            "Risk Percentage per Trade",
            min_value=0.0,
            max_value=100.0,
            value=10.0,
            step=5.0
        )
    
    with col3:
        stop_loss = st.slider(
            "Stop Loss Percentage",
            min_value=0.0,
            max_value=10.0,
            value=2.0,
            step=0.5
        )
    
    # Start button
    if st.button("Start Backtesting"):
        # Create strategy instances based on configuration
        strategy_class = get_strategy_class(strategy)
        if not strategy_class:
            st.error(f"Strategy {strategy} not implemented")
            return None
            
        strategies = []
        for coin in coins:
            # Convert from "BTC/USDT" format to "BTCUSD" format
            symbol = coin.split('/')[0] + "USD"
            strategy_instance = strategy_class(
                symbol=symbol,
                interval=timeframe,
                parent_interval=parent_interval,
                balance=balance,
                risk_percentage=risk_percentage,
                stop_loss_percentage=stop_loss
            )
            strategies.append(strategy_instance)
        
        # Run backtests in parallel
        with Pool() as pool:
            results = pool.map(lambda s: s.backtest(duration), strategies)
            
        st.success("Backtesting completed!")
        st.write(results)
        
        # Return configuration and results
        return results
    
    return None

if __name__ == "__main__":
    show_dashboard()