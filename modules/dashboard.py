#!/usr/bin/env python3
import streamlit as st
import pandas as pd

def show_dashboard():
    st.title("Trading Bot Configuration")
    
    # Strategy selection
    strategy = st.selectbox(
        "Select Trading Strategy",
        ["RSI Strategy", "Moving Average", "MACD", "Bollinger Bands"]
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
        options=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        value="1h"
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
            min_value=0.1,
            max_value=5.0,
            value=1.0,
            step=0.1
        )
    
    with col3:
        stop_loss = st.slider(
            "Stop Loss Percentage",
            min_value=0.5,
            max_value=10.0,
            value=2.0,
            step=0.5
        )
    
    # Start button
    if st.button("Start Trading"):
        # Return configuration as dictionary
        config = {
            "strategy": strategy,
            "coins": coins,
            "timeframe": timeframe,
            "balance": balance,
            "risk_percentage": risk_percentage,
            "stop_loss": stop_loss
        }
        return config
    
    return None

if __name__ == "__main__":
    config = show_dashboard()
    if config:
        st.write("Configuration:", config)
