#!/usr/bin/env python3
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from polygon_api import get_ohlc, get_macd, get_rsi, get_ema, get_sma
from plotly.subplots import make_subplots

def get_ohlc_data(ticker, multiplier, timespan, from_date, to_date):
    # Get data
    df = get_ohlc(ticker, multiplier, timespan, from_date, to_date)

    # Convert t column to datetime
    for entry in df:
        entry['t'] = datetime.fromtimestamp(entry['t'] / 1000).strftime('%Y-%m-%d %H:%M:%S')

    # Convert to pandas dataframe
    df = pd.DataFrame(df)

    print(df)

    return df

def get_rsi_data(ticker, timespan, limit):
    # Convert to pandas dataframe
    df = pd.DataFrame(get_rsi(ticker, timespan, limit))

    return df

def get_macd_data(ticker, timespan, limit):
    # Convert to pandas dataframe
    df = pd.DataFrame(get_macd(ticker, timespan, limit))

    return df

def get_ema_data(ticker, timespan, limit):
    # Convert to pandas dataframe
    df = pd.DataFrame(get_ema(ticker, timespan, limit))

    return df

def get_sma_data(ticker, timespan, limit):
    # Convert to pandas dataframe
    df = pd.DataFrame(get_sma(ticker, timespan, limit))

    return df

def draw_graph(ticker, multiplier, timespan, limit=30):
   
    # Calculate from_date and to_date based on limit
    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    end_date = int(one_day_ago.timestamp() * 1000)

    if timespan == "minute":
        start_date = int((one_day_ago - timedelta(minutes=limit*multiplier)).timestamp() * 1000)
    elif timespan == "hour":
        start_date = int((one_day_ago - timedelta(hours=limit*multiplier)).timestamp() * 1000)
    elif timespan == "day":
        start_date = int((one_day_ago - timedelta(days=limit*multiplier)).timestamp() * 1000)
    else:
        print("Invalid timespan")
        return False
    
    # Get OHLC data
    ohlc_df = get_ohlc_data(ticker, multiplier, timespan, start_date, end_date)

    # Get MACD data
    macd_df = get_macd_data(ticker, timespan, limit)

    # Get RSI data for 44 spans (30 + 14 for SMA calculation)
    rsi_df = get_rsi_data(ticker, timespan, limit+14)
    
    # Calculate 14-day SMA of RSI
    rsi_df['RSI_SMA'] = rsi_df['value'].rolling(window=14).mean()
    
    # Trim the RSI dataframe to show only the last 30 spans
    rsi_df = rsi_df.tail(limit)
    
    # Create subplot with 4 rows
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.02, row_heights=[0.4, 0.2, 0.2, 0.2])

    # Add candlestick trace to first row
    fig.add_trace(go.Candlestick(x=ohlc_df['t'],
                open=ohlc_df['o'],
                high=ohlc_df['h'],
                low=ohlc_df['l'],
                close=ohlc_df['c']), row=1, col=1)
    
    # Add RSI trace to second row
    fig.add_trace(go.Scatter(x=rsi_df['timestamp'], y=rsi_df['value'], 
                                name='RSI', line=dict(color='blue')), row=2, col=1)

    # Add RSI SMA trace to the same subplot as RSI
    fig.add_trace(go.Scatter(x=rsi_df['timestamp'], y=rsi_df['RSI_SMA'], 
                             name='RSI 14-day SMA', line=dict(color='orange')), row=2, col=1)
    

    # Add MACD trace to third row
    fig.add_trace(go.Scatter(x=macd_df['timestamp'], y=macd_df['value'], 
                             name='MACD', line=dict(color='green')), row=3, col=1)

    # Add MACD signal trace to the same subplot as MACD
    fig.add_trace(go.Scatter(x=macd_df['timestamp'], y=macd_df['signal'], 
                             name='MACD Signal', line=dict(color='red')), row=3, col=1)
    
    # Add EMA trace to fourth row
    ema_df = get_ema_data(ticker, timespan, limit)
    fig.add_trace(go.Scatter(x=ema_df['timestamp'], y=ema_df['value'], 
                             name='EMA', line=dict(color='purple')), row=4, col=1)
    
    # # Add SMA trace to fifth row
    sma_df = get_sma_data(ticker, timespan, limit)
    fig.add_trace(go.Scatter(x=sma_df['timestamp'], y=sma_df['value'], 
                             name='SMA', line=dict(color='red')), row=4, col=1)

    # Update layout
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=1000, 
        title=f'{ticker} OHLC, RSI, MACD, and Moving Averages',
        template="plotly_white",  # Use a white template for a cleaner look
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Update all x-axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGrey')

    # Update all y-axes
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGrey')

    # Update specific y-axes titles
    fig.update_yaxes(title_text='Price', row=1, col=1)
    fig.update_yaxes(title_text='RSI', row=2, col=1)
    fig.update_yaxes(title_text='MACD', row=3, col=1)
    fig.update_yaxes(title_text='MA', row=4, col=1)

    fig.show()
    return True
