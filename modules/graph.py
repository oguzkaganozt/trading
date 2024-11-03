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

def draw_graph(df, limit=180, summary=None, step_run=False):
    if df is None or df.empty:
        print("Error: Empty dataframe provided to draw_graph")
        return False
    
    color_index = 0
    rsi_title_text = ""
    mfi_title_text = ""
    ma_title_text = ""
    macd_title_text = ""
    stochrsi_title_text = ""

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
        if "RSI" in indicator and "Parent" not in indicator:
            color = get_next_color(color_palette, color_index)
            color_index = (color_index + 1) % len(color_palette)
            fig.add_trace(go.Scatter(x=df.index, y=df[indicator], 
                                     name=indicator, line=dict(color=color)), row=3, col=1)
            if rsi_title_text:
                rsi_title_text += f" | {indicator}"
            else:
                rsi_title_text = indicator
            fig.update_yaxes(title_text=rsi_title_text, row=2, col=1)
        elif "STOCHRSI" in indicator:
            color = get_next_color(color_palette, color_index)
            fig.add_trace(go.Scatter(x=df.index, y=df[indicator], 
                                     name=indicator, line=dict(color=color)), row=2, col=1)
            if stochrsi_title_text:
                stochrsi_title_text += f" | {indicator}"
            else:
                stochrsi_title_text = indicator
            fig.update_yaxes(title_text=stochrsi_title_text, row=2, col=1)
        elif "MFI" in indicator and "Parent" not in indicator:
            color = get_next_color(color_palette, color_index)
            color_index = (color_index + 1) % len(color_palette)
            fig.add_trace(go.Scatter(x=df.index, y=df[indicator], 
                                     name=indicator, line=dict(color=color)), row=2, col=1)
            if mfi_title_text:
                mfi_title_text += f" | {indicator}"
            else:
                mfi_title_text = indicator
            fig.update_yaxes(title_text=mfi_title_text, row=2, col=1)
        elif "EMA" in indicator or "SMA" in indicator:
            color = get_next_color(color_palette, color_index)
            color_index = (color_index + 1) % len(color_palette)
            fig.add_trace(go.Scatter(x=df.index, y=df[indicator], 
                                     name=indicator, line=dict(color=color)), row=1, col=1)
            if ma_title_text:
                ma_title_text += f" | {indicator}"
            else:
                ma_title_text = indicator
            fig.update_yaxes(title_text=ma_title_text, row=3, col=1)
        elif "MACD" in indicator and "MACDh" not in indicator:
            color = get_next_color(color_palette, color_index)
            color_index = (color_index + 1) % len(color_palette)
            fig.add_trace(go.Scatter(x=df.index, y=df[indicator], 
                                     name=indicator, line=dict(color=color)), row=3, col=1)
            if macd_title_text:
                macd_title_text += f" | {indicator}"
            else:
                macd_title_text = indicator
            fig.update_yaxes(title_text=macd_title_text, row=3, col=1)
    
    # Draw support and resistance lines as horizontal lines
    if 'support' in df.columns:
        for support_level in df['support'].dropna().unique():
            fig.add_shape(type='line',
                          x0=df.index.min(), x1=df.index.max(),
                          y0=support_level, y1=support_level,
                          line=dict(color='green', width=2, dash='dot'),
                          name='Support')

    if 'resistance' in df.columns:
        for resistance_level in df['resistance'].dropna().unique():
            fig.add_shape(type='line',
                          x0=df.index.min(), x1=df.index.max(),
                          y0=resistance_level, y1=resistance_level,
                          line=dict(color='red', width=2, dash='dot'),
                          name='Resistance')

    # Draw entry points
    entry_data = df['entry_data'].dropna()
    fig.add_trace(go.Scatter(
        x=entry_data.index,
        y=entry_data.apply(lambda x: x['price']),
        name="Entry",
        mode="markers",
        marker=dict(color="green", size=20, symbol="triangle-up"),
        hovertext=entry_data.apply(lambda x: f"Entry<br>Price: ${x['price']:.2f}<br>Size: {x['size']:.4f}<br>Amount: ${x['amount']:.2f}")
    ), row=1, col=1)

    # Draw exit points
    exit_data = df['exit_data'].dropna()
    fig.add_trace(go.Scatter(
        x=exit_data.index,
        y=exit_data.apply(lambda x: x['price']),
        name="Exit",
        mode="markers",
        marker=dict(color="red", size=20, symbol="triangle-down"),
        hovertext=exit_data.apply(lambda x: f"Exit<br>Price: ${x['price']:.2f}<br>Gain/Loss: {x['percentage_gain_loss']:.2f}%<br>Reason: {x['reason']}")
    ), row=1, col=1)

    # Draw partial close points
    partial_close_data = df['partial_close_data'].dropna()
    fig.add_trace(go.Scatter(
        x=partial_close_data.index,
        y=partial_close_data.apply(lambda x: x['price']),
        name="Partial Close",
        mode="markers",
        marker=dict(color="yellow", size=20, symbol="circle"),
        hovertext=partial_close_data.apply(lambda x: f"Partial Close<br>Price: ${x['price']:.2f}<br>Gain/Loss: {x['percentage_gain_loss']:.2f}%")
    ), row=1, col=1)

    # Update layout
    if not step_run:
        text = f'<b>{summary["name"]} {df["symbol"].iloc[0]} - {df["interval"].iloc[0].upper()} </b> - {summary["win_trades"]} Win / {summary["loss_trades"]} Loss Trades -  Profit Factor: {summary["profit_factor"]:.2f} - Total Gain/Loss: {summary["total_profit_loss_percentage"]:.2f}%'
    else:
        text = f'<b>{summary["name"]} {summary["symbol"]} {summary["interval"]} </b>'

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=1000, 
        title=dict(
            text=text,
            font=dict(size=18)
        ),
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(b=80)
    )

    # Update all x-axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGrey')

    # Update all y-axes
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGrey')

    # Save graph to HTML file
    try:
        file_name = f"{summary['name']}-{summary['symbol']}-{summary['interval']}.html"
        fig.write_html(f"graphs/{file_name}")
        summary["graph_url"] = f"graphs/{file_name}"
        print(f"Graph saved to {summary['graph_url']}")
    except Exception as e1:
        print(f"Error saving graph to HTML file: {e1}")

    return True
