import requests     
import pandas as pd

def kraken_request(symbol, interval = "1h"):
    # 1m = 1, 5m = 5, 15m = 15, 30m = 30, 1h = 60, 4h = 240, 1d = 1440, 1w = 10080, 15d = 21600
    multiplier = 60

    if interval == "1m":
        multiplier = 1
    elif interval == "5m":
        multiplier = 5
    elif interval == "15m":
        multiplier = 15
    elif interval == "30m":
        multiplier = 30
    elif interval == "1h":
        multiplier = 60
    elif interval == "4h":
        multiplier = 240
    elif interval == "1d":
        multiplier = 1440
    elif interval == "1w":
        multiplier = 10080
    elif interval == "15d":
        multiplier = 21600

    url = "https://api.kraken.com/0/public/OHLC"

    payload = {
        "pair": symbol,
        "interval": multiplier
    }
    headers = {
        'Accept': 'application/json'
    }

    response = requests.get(url, params=payload, headers=headers)
    data = response.json()
    data = next(iter(data['result'].values()))

    return data

def get_ohlc(symbol, interval, limit=180):
    # Get the data from Kraken
    data = kraken_request(symbol, interval)

    # Create DataFrame
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
    
    # Convert data types
    numeric_columns = ['open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
    df[numeric_columns] = df[numeric_columns].astype(float)
    
    # Convert timestamp to datetime and set as index
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    df.set_index('timestamp', inplace=True)

    # If no data is returned, return None
    if df.empty:
        return None
    
    # Tail the data to get the last limit entries
    if len(df) > limit:
        df = df.iloc[-limit:]

    # Add additional columns
    df['interval'] = interval
    df['percent_return'] = df['close'] / df['open'] - 1
    df['symbol'] = symbol
    df['entry'] = None
    df['exit'] = None
    df['position_size'] = None
    df['partial_close'] = None
    df['percentage_gain_loss'] = None
    
    return df
