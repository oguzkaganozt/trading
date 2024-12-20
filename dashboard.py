#!/usr/bin/env python3
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from multiprocessing import Pool
import os
import json
from strategies.mfi import MFI
from strategies.rsi import RSI
from strategies.mfi_macd import MFI_MACD
from strategies.macd import MACD
from strategies.stoch_rsi import STOCH_RSI
from strategies.stoch_rsi_double import STOCH_RSI_DOUBLE
from strategies.macd_double import MACD_DOUBLE
import pandas_ta as ta

strategy_map = {
    "RSI: Long: RSI SMA üzerine çıktığında, Short: RSI SMA altına düştüğünde": RSI,
    "MFI: Long: MFI SMA üzerine çıktığında, Short: MFI SMA altına düştüğünde": MFI,
    "MFI-MACD: Long: MACD pozitif alanda, MFI SMA üzerine çıktığında, Short: MACD negatif alanda, MFI SMA altına düştüğünde": MFI_MACD,
    "MACD: Long: MACD pozitif kestiğinde, Short: MACD negatif kestiğinde": MACD,
    "STOCH-RSI: Long: STOCH-RSI pozitif kestiğinde, Short: STOCH-RSI negatif kestiğinde": STOCH_RSI,
    # "MACD-DOUBLE: Giriş: Büyük ve küçük zaman diliminde MACD pozitif alanda. Çıkış: Küçük zaman diliminde MACD negatif alanda": MACD_DOUBLE,
    # "STOCH-RSI-DOUBLE: Giriş: Büyük ve küçük zaman diliminde STOCH-RSI pozitif alanda. Çıkış: Küçük zaman diliminde STOCH-RSI negatif alanda": STOCH_RSI_DOUBLE
}

def get_coin_pairs():
    with open("./coins.json", 'r') as f:
        coin_pairs = json.load(f)
    return coin_pairs

coin_pairs = get_coin_pairs()

def get_strategy_class(strategy_name):
    return strategy_map.get(strategy_name)

def run_backtest(args):
    strategy, duration = args
    return strategy.backtest(duration)

def run_step(args):
    strategy = args
    return strategy.run_step()

def show_dashboard():
    st.sidebar.title("Menu")
    dashboard_type = st.sidebar.selectbox("Select Dashboard", ["Tarama", "Backtesting", "Live Simulation", "Live Trading"], index=0)

    if dashboard_type == "Tarama":
        show_scanning_dashboard()
    elif dashboard_type == "Backtesting":
        show_backtesting_dashboard()
    elif dashboard_type == "Live Trading":
        show_live_trading_dashboard()
    elif dashboard_type == "Live Simulation":
        show_live_simulation_dashboard()

def show_live_trading_dashboard():
    st.title("Live Trading")
    pass

def show_scanning_dashboard():
    # Initialize session state for results and signals if not exists
    if 'scan_results' not in st.session_state:
        st.session_state.scan_results = None
    if 'signal_messages' not in st.session_state:
        st.session_state.signal_messages = []

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
    
    st.title("Tarama")

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
    
    # Timeframe selection
    interval = st.select_slider(
        "Küçük Zaman Dilimi",
        options=["30m", "1h", "4h", "1d", "1w"],
        value="4h"
    )

    # Parent interval selection
    parent_interval = st.select_slider(
        "Büyük Zaman Dilimi",
        options=["1h", "4h", "1d", "1w", "15d"],
        value="1d"
    )

    # Start button
    if st.button("Başlat"):
        # Clear previous signals when starting new scan
        st.session_state.signal_messages = []
        
        # Clear and recreate graphs folder
        if os.path.exists("graphs"):
            for file in os.listdir("graphs"):
                os.remove(os.path.join("graphs", file))
        os.makedirs("graphs", exist_ok=True)
        
        # Create strategy instances based on configuration
        strategies = []
        for coin in coin_pairs:
            # Convert from "BTC/USDT" format to "BTCUSD" format
            symbol = coin.split('/')[0] + "USD"
            strategy_instance = strategy_class(
                symbol=symbol,
                interval=interval,
                parent_interval=parent_interval
            )
            strategies.append(strategy_instance)
        
        # Run live simulation for each strategy
        for strategy in strategies:
            strategy.put_live_simulation()
        
        # Run step run in parallel
        with st.status("Tarama yapılıyor...") as status:
            with Pool() as pool:
                run_args = [(strategy) for strategy in strategies]
                results = []
                
                try:
                    for i, result in enumerate(pool.imap(run_step, run_args)):
                        if result is not None:  # Add null check
                            results.append(result)
                            st.write(f"Tamamlandı {result['name']} {result['symbol']} {result['interval']}")
                        else:
                            st.warning(f"Sonuç yok {strategies[i].symbol}")
                        status.update(label=f"Tarama {i + 1}/{len(strategies)}")
                    
                    status.update(label="Tamamlandı!", state="complete")
                except Exception as e:
                    status.update(label=f"Error: {str(e)}", state="error")
                    st.error(f"An error occurred during scanning: {str(e)}")
        
        for result in results:
            if result is None:
                # Drop result
                results.remove(result)
                continue
            entry_signal = result['entry_signal']
            exit_signal = result['exit_signal']
            
            # Store signals in session state instead of displaying directly
            if entry_signal == "long":
                message = f"<span style='color: green'>{result['last_index']} {result['name']} {result['symbol']} {result['interval']} Entry Signal: {entry_signal}</span>"
                st.session_state.signal_messages.append(message)
            elif entry_signal == "short":
                message = f"<span style='color: red'>{result['last_index']} {result['name']} {result['symbol']} {result['interval']} Entry Signal: {entry_signal}</span>"
                st.session_state.signal_messages.append(message)

        # Store results in session state
        st.session_state.scan_results = results

    # Display stored signals (this will persist when changing dropdown)
    for message in st.session_state.signal_messages:
        st.markdown(message, unsafe_allow_html=True)

    # Move graph display outside the button click condition
    if st.session_state.scan_results:
        selected_result = st.selectbox(
            "Select Graph",
            options=[f"{result['symbol']} {result['interval']}" for result in st.session_state.scan_results],
            format_func=lambda x: f"Graph for {x}"
        )
        
        # Find the selected result
        selected_idx = [f"{result['symbol']} {result['interval']}" for result in st.session_state.scan_results].index(selected_result)
        result = st.session_state.scan_results[selected_idx]
        
        # Display the selected graph
        with open("./" + result["graph_url"], 'r') as f:
            html_data = f.read()
        st.components.v1.html(html_data, scrolling=True, width=1400, height=1000)
        
        return st.session_state.scan_results

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
    interval = st.select_slider(
        "Select Timeframe",
        options=["30m", "1h", "4h", "1d", "1w"],
        value="4h"
    )

    # Parent interval selection
    parent_interval = st.select_slider(
        "Select Parent Interval",
        options=["1h", "4h", "1d", "1w", "15d"],
        value="1d"
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
                symbol=coin,
                interval=interval,
                parent_interval=parent_interval,
                balance=balance,
                risk_percentage=risk_percentage,
                stop_loss_percentage=stop_loss
            )
            strategies.append(strategy_instance)
        
        # Run live simulation for each strategy
        for strategy in strategies:
            strategy.put_live_simulation()
        
        # Run live simulation in parallel
        with st.status("Running live simulation...") as status:
            with Pool() as pool:
                pool.map(strategy.live_simulation, strategies)
                status.update(label="Completed!", state="complete")


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
    
    # Interval selection
    interval = st.select_slider(
        "Select Interval",
        options=["30m", "1h", "4h", "1d", "1w"],
        value="4h"
    )

    # Parent interval selection
    parent_interval = st.select_slider(
        "Select Parent Interval",
        options=["1h", "4h", "1d", "1w", "15d"],
        value="1d"
    )

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
                interval=interval,
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
        
        # Replace tabs with dropdown for graph selection
        if results:
            selected_result = st.selectbox(
                "Select Graph",
                options=[f"{result['symbol']} {result['interval']}" for result in results],
                format_func=lambda x: f"Graph for {x}"
            )
            
            # Find the selected result
            selected_idx = [f"{result['symbol']} {result['interval']}" for result in results].index(selected_result)
            result = results[selected_idx]
            
            # Display the selected graph
            with open("./" + result["graph_url"], 'r') as f:
                html_data = f.read()
            st.components.v1.html(html_data, scrolling=True, width=1400, height=1000)
        
        return results
    
    return None

if __name__ == "__main__":
    show_dashboard()
