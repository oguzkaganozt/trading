#!/usr/bin/env python3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

color_palette = ["red", "blue", "green", "brown", "purple", "orange", "cyan", "pink", "gray", "black"]

def get_next_color(color_palette, color_index):
    color = color_palette[color_index]
    color_index = (color_index + 1) % len(color_palette)
    color_index = color_index + 1
    return color

def draw_graph(df, limit=60):   
    color_index = 0
    rsi_title_text = ""
    ma_title_text = ""

    # Limit the dataframe to the last 'limit' rows
    df = df.tail(limit)

    # Create subplot with 3 rows
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.02, row_heights=[0.6, 0.2, 0.2])

    # Add candlestick trace to first row
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        hovertext=[f"Date: {date}<br>"
                   f"Percent Return: {percent_return:.2%}<br>"
                   f"Open: {open:.2f}<br>"
                   f"High: {high:.2f}<br>"
                   f"Low: {low:.2f}<br>"
                   f"Close: {close:.2f}"
                   for date, percent_return, open, high, low, close in zip(df.index, df["percent_return"], df["open"], df["high"], df["low"], df["close"])],
        hoverinfo="text"
    ), row=1, col=1)

    # Add indicators to bottom rows
    for indicator in df.columns:
        if "RSI" in indicator:
            color = get_next_color(color_palette, color_index)
            color_index = (color_index + 1) % len(color_palette)
            fig.add_trace(go.Scatter(x=df.index, y=df[indicator], 
                                     name=indicator, line=dict(color=color)), row=2, col=1)
            if rsi_title_text:
                rsi_title_text += f" | {indicator}"
            else:
                rsi_title_text = indicator
            fig.update_yaxes(title_text=rsi_title_text, row=2, col=1)
        elif "EMA" in indicator or "SMA" in indicator:
            color = get_next_color(color_palette, color_index)
            color_index = (color_index + 1) % len(color_palette)
            fig.add_trace(go.Scatter(x=df.index, y=df[indicator], 
                                     name=indicator, line=dict(color=color)), row=3, col=1)
            if ma_title_text:
                ma_title_text += f" | {indicator}"
            else:
                ma_title_text = indicator
            fig.update_yaxes(title_text=ma_title_text, row=3, col=1)

    # Draw entry and exit points on the ohlc graph
    fig.add_trace(go.Scatter(x=df.index, y=df["entry"], name="Entry", mode="markers", marker=dict(color="green", size=20, symbol="triangle-up")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["exit"], name="Exit", mode="markers", marker=dict(color="red", size=20, symbol="triangle-down")), row=1, col=1)
            
    # Update layout
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=1000, 
        title=f'{df["symbol"].iloc[0]} GRAPH',
        template="plotly_white",  # Use a white template for a cleaner look
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Update all x-axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGrey')

    # Update all y-axes
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGrey')

    fig.show()
    return True
