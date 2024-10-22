#!/usr/bin/env python3
import pandas as pd
import pandas_ta as ta
from rest_api import get_ohlc
from graph import draw_graph

data = get_ohlc("X:BTCUSD", "day", 1)
data.ta.sma(length=7, append=True)
data.ta.ema(length=7, append=True)
data.ta.rsi(length=14, append=True)
data.ta.sma(close=data['RSI_14'], length=14, append=True, suffix='RSI')


# data.ta.bbands(length=20, std=2, append=True)
# data.ta.atr(length=14, append=True)
# print(data)
draw_graph(data)

# df.ta.rsi(length=14, append=True)
# df.ta.ema(length=10, append=True)
# df.ta.macd(append=True)
# df.ta.bbands(append=True)
# print(df)
# # List of all indicators
# df.ta.indicators()
#  pd.DataFrame: lower, mid, upper, bandwidth, and percent columns.
# # Help about an indicator such as rsi
# help(ta.rsi)

# # Load data
# df = pd.read_csv("AAPL.csv", sep=",")
# # VWAP requires the DataFrame index to be a DatetimeIndex.
# # Replace "datetime" with the appropriate column from your DataFrame
# df.set_index(pd.DatetimeIndex(df["datetime"]), inplace=True)

# # Calculate Returns and append to the df DataFrame
# df.ta.log_return(cumulative=True, append=True)
# df.ta.percent_return(cumulative=True, append=True)

# # New Columns with results
# df.columns

# # Take a peek
# df.tail()