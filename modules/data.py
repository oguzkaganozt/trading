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
    
    # Convert timestamp to datetime with UTC+3 timezone
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Etc/GMT-3')
    df.set_index('timestamp', inplace=True)

    # If no data is returned, return None
    if df.empty:
        return None
    
    # Tail the data to get the last limit entries
    if len(df) > limit:
        df = df.iloc[-limit:]

    # Calculate support and resistance
    calculate_support_resistance(df)

    # Add additional columns
    df['symbol'] = symbol
    df['interval'] = interval
    df['percent_return'] = df['close'] / df['open'] - 1
    df['entry_data'] = None  # This will be a dictionary
    df['exit_data'] = None   # This will be a dictionary
    df['partial_close_data'] = None  # This will be a dictionary

    return df

# Calculate support and resistance levels
def calculate_support_resistance(data, window=15, deviation_threshold=0.005, smoothing_periods=5, volume_factor=1.2):
    """
    Calculate support and resistance levels using local minima and maxima with additional filtering.
    
    :param window: The number of periods to consider for local extrema
    :param deviation_threshold: The minimum price deviation to consider as a new level
    :param smoothing_periods: Number of periods for moving average smoothing
    :param volume_factor: Factor to consider a volume spike
    :return: The updated DataFrame with support and resistance columns
    """
    # Apply smoothing to reduce noise
    highs = data['high'].rolling(window=smoothing_periods).mean()
    lows = data['low'].rolling(window=smoothing_periods).mean()
    volumes = data['volume']
    
    resistance_levels = []
    support_levels = []
    
    # Calculate average volume
    avg_volume = volumes.mean()
    
    # Initialize support and resistance columns
    data['resistance'] = None
    data['support'] = None
    
    for i in range(window, len(data) - window):
        # Check for resistance
        if highs.iloc[i] > highs.iloc[i-window:i].max() and highs.iloc[i] > highs.iloc[i+1:i+window+1].max():
            # Check if this is a significant new level
            if not resistance_levels or abs(highs.iloc[i] - resistance_levels[-1]) / resistance_levels[-1] > deviation_threshold:
                # Check for volume confirmation
                if volumes.iloc[i] > avg_volume * volume_factor:
                    resistance_levels.append(highs.iloc[i])
                    data.at[data.index[i], 'resistance'] = highs.iloc[i]
        
        # Check for support
        if lows.iloc[i] < lows.iloc[i-window:i].min() and lows.iloc[i] < lows.iloc[i+1:i+window+1].min():
            # Check if this is a significant new level
            if not support_levels or abs(lows.iloc[i] - support_levels[-1]) / support_levels[-1] > deviation_threshold:
                # Check for volume confirmation
                if volumes.iloc[i] > avg_volume * volume_factor:
                    support_levels.append(lows.iloc[i])
                    data.at[data.index[i], 'support'] = lows.iloc[i]
    
    return data
