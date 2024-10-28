#!/usr/bin/env python3
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from multiprocessing import Pool
import os

from strategies.rsi_sma import RSI_SMA
from strategies.mfi_sma import MFI_SMA
from strategies.mfi_sma_macd import MFI_SMA_MACD
from strategies.mfi_sma_macd_10diff import MFI_SMA_MACD_10DIFF

strategy_map = {
    "RSI-SMA": RSI_SMA,
    "MFI-SMA": MFI_SMA,
    "MFI-SMA-MACD": MFI_SMA_MACD,
    "MFI-SMA-MACD-10DIFF": MFI_SMA_MACD_10DIFF
}

coin_pairs = ["BTC/USDT", 
              "ETH/USDT", 
              "SOL/USDT", 
              "XRP/USDT",
              "DOGE/USDT",
              "TRX/USDT",
              "ADA/USDT",
              "AVAX/USDT",
              "WBTC/USDT",
              "SHIB/USDT", 
              "BCH/USDT", 
              "LINK/USDT", 
              "DOT/USDT", 
              "LTC/USDT", 
              "NEAR/USDT", 
              "APT/USDT", 
              "SUI/USDT",
              "UNI/USDT",
              "TAO/USDT", 
              "PEPE/USDT", 
              "ICP/USDT", 
              "DAI/USDT", 
              "FET/USDT", 
              "XMR/USDT", 
              "ETC/USDT", 
              "XLM/USDT", 
              "STX/USDT",
              "WIF/USDT",
              "AAVE/USDT",
              "IMX/USDT",
              "FIL/USDT",
              "ARB/USDT",
              "OP/USDT",
              "MNT/USDT",
              "RUNE/USDT",
              "FTM/USDT",
              "RENDER/USDT",
              "INJ/USDT",
              "ATOM/USDT",
              "POPCAT/USDT",
              "GRT/USDT",
              "BONK/USDT",
              "JUP/USDT",
              "SEI/USDT",
              "PYTH/USDT",
              "FLOKI/USDT",
              "HNT/USDT",
              "TIA/USDT",
              "MKR/USDT",
              "ONDO/USDT",
              "ALGO/USDT",
              "ENA/USDT",
              "MSOL/USDT",
              "BEAM/USDT",
              "LDO/USDT",
              "QNT/USDT",
              "RAY/USDT"
              ]

def get_strategy_class(strategy_name):
    return strategy_map.get(strategy_name)

def run_backtest(args):
    strategy, duration = args
    return strategy.backtest(duration)

def show_dashboard():
    st.sidebar.title("Menu")
    dashboard_type = st.sidebar.selectbox("Select Dashboard", ["Backtesting", "Live Simulation", "Live Trading"], index=0)

    if dashboard_type == "Backtesting":
        show_backtesting_dashboard()
    elif dashboard_type == "Live Trading":
        show_live_trading_dashboard()
    elif dashboard_type == "Live Simulation":
        show_live_simulation_dashboard()

def show_live_trading_dashboard():
    st.title("Live Trading")
    pass

def show_live_simulation_dashboard():
        # Add custom CSS to left-align content
    st.markdown("""
        <style>
        .block-container {
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 85%;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Live Simulation")
    
    # Strategy selection
    strategies = list(strategy_map.keys())
    strategy = st.selectbox(
        "Select Trading Strategy",
        strategies
    )
    
    # Get strategy class immediately after selection
    strategy_class = get_strategy_class(strategy)
    if not strategy_class:
        st.error(f"Strategy {strategy} not implemented")
        return None
    
    # Coin selection (allowing multiple)
    coins = st.multiselect(
        "Select Trading Pairs",
        coin_pairs,
        default=["BTC/USDT"]
    )
    
    # Timeframe selection
    timeframe = st.select_slider(
        "Select Timeframe",
        options=["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "15d"],
        value="1d"
    )

    # Parent interval selection
    if strategy_class.is_parent_interval_supported():
        parent_interval = st.select_slider(
            "Select Parent Interval",
            options=["1h", "4h", "1d", "1w", "15d"],
            value="1w"
        )
    else:
        parent_interval = None
    
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
            value=100.0,
            step=5.0
        )
    
    with col3:
        stop_loss = st.slider(
            "Stop Loss Percentage",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5
        )

    # Start button
    if st.button("Start Simulation"):
        # Clear and recreate graphs folder
        if os.path.exists("graphs"):
            for file in os.listdir("graphs"):
                os.remove(os.path.join("graphs", file))
        os.makedirs("graphs", exist_ok=True)
        
        # Create strategy instances based on configuration
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


def show_backtesting_dashboard():
    # Add custom CSS to left-align content
    st.markdown("""
        <style>
        .block-container {
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 85%;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Backtesting")
    
    # Strategy selection
    strategies = list(strategy_map.keys())
    strategy = st.selectbox(
        "Select Trading Strategy",
        strategies
    )
    
    # Get strategy class immediately after selection
    strategy_class = get_strategy_class(strategy)
    if not strategy_class:
        st.error(f"Strategy {strategy} not implemented")
        return None
    
    # Coin selection (allowing multiple)
    coins = st.multiselect(
        "Select Trading Pairs",
        coin_pairs,
        default=["BTC/USDT"]
    )
    
    # Timeframe selection
    timeframe = st.select_slider(
        "Select Timeframe",
        options=["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "15d"],
        value="1d"
    )

    # Parent interval selection
    if strategy_class.is_parent_interval_supported():
        parent_interval = st.select_slider(
            "Select Parent Interval",
            options=["1h", "4h", "1d", "1w", "15d"],
            value="1w"
        )
    else:
        parent_interval = None

    # Duration selection
    duration = st.select_slider(
        "Select Duration(Bars)",
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
            value=100.0,
            step=5.0
        )
    
    with col3:
        trailing_stop_loss = st.slider(
            "Trailing Stop Loss Percentage",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5
        )
    
    # Start button
    if st.button("Start Backtesting"):
        # Clear and recreate graphs folder
        if os.path.exists("graphs"):
            for file in os.listdir("graphs"):
                os.remove(os.path.join("graphs", file))
        os.makedirs("graphs", exist_ok=True)
        
        # Create strategy instances based on configuration
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
                trailing_stop_percentage=trailing_stop_loss
            )
            strategies.append(strategy_instance)
        
        # Run backtests in parallel
        with st.status("Running backtests...") as status:
            with Pool() as pool:
                backtest_args = [(strategy, duration) for strategy in strategies]
                results = []
                
                try:
                    for i, result in enumerate(pool.imap(run_backtest, backtest_args)):
                        if result is not None:  # Add null check
                            results.append(result)
                            st.write(f"Completed backtest for {strategies[i].symbol}")
                        else:
                            st.warning(f"No results for {strategies[i].symbol}")
                        status.update(label=f"Backtest {i + 1}/{len(strategies)}")
                    
                    status.update(label="Completed!", state="complete")
                except Exception as e:
                    status.update(label=f"Error: {str(e)}", state="error")
                    st.error(f"An error occurred during backtesting: {str(e)}")
        
        # Create tabs for each result
        if results:            
            tabs = st.tabs([f"Result for {result['symbol']} {result['interval']}" for result in results])
            
            for tab, result in zip(tabs, results):
                with tab:
                    with open("./"+result["graph_url"],'r') as f: 
                        html_data = f.read()

                    # Show in webpage
                    st.components.v1.html(html_data, scrolling=True, width=1400, height=1000)
        
        # Return configuration and results
        return results
    
    return None

if __name__ == "__main__":
    show_dashboard()
