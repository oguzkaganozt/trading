import requests
import datetime
from collections import deque

def get_api_key():
    import json
    try:
        with open('credentials.json', 'r') as file:
            credentials = json.load(file)
            api_key = credentials.get('POLYGON_API_KEY')
            if not api_key:
                raise ValueError("POLYGON_API_KEY not found in credentials.json")
            return api_key
    except FileNotFoundError:
        raise FileNotFoundError("credentials.json file not found")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in credentials.json")

REST_API_KEY = get_api_key()

def polygon_request(url, params):
    try:
        response = requests.get(url, params=params)
        print(response.request.url)
        if response.status_code == 200:
            data = response.json()
            # if 'next_url' in data:
            #     print(f"Next URL available for pagination")
            if 'results' in data and 'values' in data['results']:
                return data['results']['values']
            else:
                return data['results']
        else:
            print(f"API request failed with status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def get_symbol_details(symbol):
    url = f"https://api.polygon.io/v3/reference/tickers/{symbol}"
    params = {
        "apiKey": REST_API_KEY
    }
    data = polygon_request(url, params)
    if data:
        return data
    else:
        return None

def get_symbols():
    url = "https://api.polygon.io/v3/reference/tickers"
    params = {
        "apiKey": REST_API_KEY,
        "limit": 1000,
        "market": "crypto",
        "sort": "ticker"
    }
    
    data = polygon_request(url, params)
    if data:
        return data
    else:
        return None

def get_ohlc(symbol, timespan, multiplier, limit=60, from_date=int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)).timestamp() * 1000), to_date=int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
    params = {
        "adjusted": "true",
        "apiKey": REST_API_KEY,
        "sort": "desc"
    }
    
    data = polygon_request(url, params)

    # Tail the data to get the last limit entries
    if len(data) > limit:
        data = data[:limit]

    if data:
        for entry in data:
            entry['date'] = datetime.datetime.fromtimestamp(entry['t'] / 1000).strftime('%Y-%m-%dT%H:%M:%SZ')
        return data
    else:
        return None

def get_rsi(symbol, timespan, multiplier, limit=60, series_type="close", window=14):
    """
    Calculate the Relative Strength Index (RSI) for a given symbol.

    Args:
        symbol (str): The ticker symbol.
        timespan (str): The timespan for the data (e.g., 'day', 'minute').
        multiplier (int): The multiplier for the timespan.
        limit (int, optional): Number of RSI values to return. Defaults to 60.
        series_type (str, optional): Type of series to use ('close', 'open', 'high', 'low'). Defaults to "close".
        window (int, optional): The window size for RSI calculation. Defaults to 14.

    Returns:
        list: A list of dictionaries containing the date and RSI value.
    """
    ohlc_data = get_ohlc(symbol, timespan, multiplier, limit=limit + window)
    if not ohlc_data:
        return None

    # Reverse the data to chronological order (oldest first)
    ohlc_data = list(reversed(ohlc_data))

    for i, entry in enumerate(ohlc_data, 1):
        print(f"{i}: {entry}")

    # Map series_type to the appropriate key
    if series_type == "close":
        series_key = "c"
    elif series_type == "open":
        series_key = "o"
    elif series_type == "high":
        series_key = "h"
    elif series_type == "low":
        series_key = "l"
    else:
        raise ValueError(f"Invalid series_type: {series_type}")

    # Extract the relevant series
    series = [entry[series_key] for entry in ohlc_data]

    # Calculate price changes
    deltas = [series[i] - series[i - 1] for i in range(1, len(series))]

    # Separate gains and losses
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]

    # Initialize average gain and loss using the first 'window' periods
    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window

    rsi_values = []

    # Calculate RSI for the first window
    if avg_loss == 0:
        rs = float('inf')
    else:
        rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_values.append({
        'date': ohlc_data[window]['date'],
        'rsi': rsi
    })

    # Calculate RSI for the rest of the data using Wilder's smoothing method
    for i in range(window, len(gains)):
        gain = gains[i]
        loss = losses[i]

        # Update the average gain and loss
        avg_gain = (avg_gain * (window - 1) + gain) / window
        avg_loss = (avg_loss * (window - 1) + loss) / window

        if avg_loss == 0:
            rs = float('inf')
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        rsi_values.append({
            'date': ohlc_data[i + 1]['date'],
            'rsi': rsi
        })

    # Limit the results to the specified limit
    return reversed(rsi_values)

def get_sma(symbol, timespan, multiplier, limit=60, window=7, series_type="close"):
    """
    Calculate the Simple Moving Average (SMA) for a given symbol.

    Args:
        symbol (str): The ticker symbol.
        timespan (str): The timespan for the data (e.g., 'day', 'minute').
        multiplier (int): The multiplier for the timespan.
        limit (int, optional): Number of SMA values to return. Defaults to 60.
        window (int, optional): The window size for SMA calculation. Defaults to 50.
        series_type (str, optional): Type of series to use ('close', 'open', 'high', 'low'). Defaults to "close".

    Returns:
        list: A list of dictionaries containing the date and SMA value.
    """
    ohlc_data = get_ohlc(
        symbol,
        timespan,
        multiplier,
        limit=limit + window,
        from_date=int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)).timestamp() * 1000),
        to_date=int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    )
    if not ohlc_data:
        return None

    # Reverse the data to chronological order (oldest first)
    ohlc_data = list(reversed(ohlc_data))

    # Map series_type to the appropriate key
    if series_type == "close":
        series_key = "c"
    elif series_type == "open":
        series_key = "o"
    elif series_type == "high":
        series_key = "h"
    elif series_type == "low":
        series_key = "l"
    else:
        raise ValueError(f"Invalid series_type: {series_type}")

    # Extract the relevant series
    series = [entry[series_key] for entry in ohlc_data]

    sma_values = []

    for i in range(window - 1, len(series)):
        window_slice = series[i - window + 1 : i + 1]
        sma = sum(window_slice) / window
        sma_values.append({
            'date': ohlc_data[i]['date'],
            'sma': sma
        })

    # Limit the results to the specified limit
    return reversed(sma_values)

def get_ema(symbol, timespan, multiplier, limit=60, window=50, series_type="close"):
    url = f"https://api.polygon.io/v1/indicators/ema/{symbol}"
    params = {
        "timespan": timespan,
        "window": window,
        "series_type": series_type,
        "order": "desc",
        "limit": limit,
        "apiKey": REST_API_KEY
    }
    
    data = polygon_request(url, params)
    if data:
        data.reverse()  # Reverse the list to get the most recent data first
        for entry in data:
            entry['date'] = datetime.datetime.fromtimestamp(entry['timestamp'] / 1000).strftime('%Y-%m-%dT%H:%M:%SZ')
        return data
    else:
        return None

def get_macd(symbol, timespan, limit, short_window=12, long_window=26, signal_window=9, series_type="close"):
    url = f"https://api.polygon.io/v1/indicators/macd/{symbol}"
    params = {
        "timespan": timespan,
        "short_window": short_window,
        "long_window": long_window,
        "signal_window": signal_window,
        "series_type": series_type,
        "order": "desc",
        "limit": limit,
        "apiKey": REST_API_KEY
    }
    
    data = polygon_request(url, params)
    if data:
        data.reverse()  # Reverse the list to get the most recent data first
        for entry in data:
            entry['date'] = datetime.datetime.fromtimestamp(entry['timestamp'] / 1000).strftime('%Y-%m-%dT%H:%M:%SZ')
        return data
    else:
        return None

# Get Bollinger Bands by using get_ohlc and calculate from the close price
def get_bbands(symbol, timespan, multiplier, limit=60, window=20, series_type="close"):
    # Get OHLC data
    from_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    to_date = datetime.datetime.now().strftime('%Y-%m-%d')
    ohlc_data = get_ohlc(symbol, 1, timespan, from_date, to_date)
    
    if not ohlc_data:
        return None
    
    # Prepare data for calculations
    close_prices = [entry['c'] for entry in ohlc_data]
    
    # Calculate SMA and standard deviation
    sma = []
    std_dev = []
    for i in range(len(close_prices)):
        if i < window - 1:
            sma.append(None)
            std_dev.append(None)
        else:
            window_prices = close_prices[i-window+1:i+1]
            sma.append(sum(window_prices) / window)
            variance = sum((x - sma[-1]) ** 2 for x in window_prices) / window
            std_dev.append(variance ** 0.5)
    
    # Calculate Bollinger Bands
    bb_data = []
    for i in range(len(ohlc_data)):
        if sma[i] is not None:
            entry = {
                'timestamp': ohlc_data[i]['t'],
                'date': datetime.datetime.fromtimestamp(ohlc_data[i]['t'] / 1000).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'close': ohlc_data[i]['c'],
                'sma': sma[i],
                'upper_band': sma[i] + (2 * std_dev[i]),
                'lower_band': sma[i] - (2 * std_dev[i])
            }
            bb_data.append(entry)
    
    # Limit the results if necessary
    return bb_data[-limit:]

def get_news(symbol, published_before=None, limit=10):
    ticker = symbol.replace("X:", "")
    ticker = ticker.replace("USD", "")
    ticker = ticker.upper()

    url = f"https://api.polygon.io/v2/reference/news"
    params = {
        "apiKey": REST_API_KEY,
        "ticker": ticker,
        "limit": limit,
        "published_utc.lte": published_before
    }
    
    news = []
    data = polygon_request(url, params)
    if data:    # Extract insight from the news data
        for item in data:
            for insight in item['insights']:
                if insight['ticker'] == ticker:
                    content = {}
                    content['ticker'] = ticker
                    content['article_url'] = item['article_url']
                    content['description'] = item['description']
                    content['published_utc'] = item['published_utc']
                    content['sentiment'] = insight['sentiment']
                    content['sentiment_reasoning'] = insight['sentiment_reasoning']
                    news.append(content)
        return news
    else:
        return None
