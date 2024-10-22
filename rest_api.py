import requests
import datetime
from collections import deque
import pandas as pd

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

def polygon_request(symbol, interval, multiplier, start_date, end_date, max_pages=10):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{interval}/{int(start_date.timestamp() * 1000)}/{int(end_date.timestamp() * 1000)}"
    params = {
        "adjusted": "true",
        "apiKey": REST_API_KEY,
        "sort": "desc"
    }

    try:
        response = requests.get(url, params=params)
        print(f"Initial request URL: {response.request.url}")
        if response.status_code == 200:
            data = response.json()
            page_count = 1
            while 'next_url' in data and page_count < max_pages:
                print(f"Fetching page {page_count + 1}")
                next_url = data['next_url']
                next_response = requests.get(next_url, params=params)
                if next_response.status_code == 200:
                    next_data = next_response.json()
                    if 'results' in next_data:
                        if 'values' in next_data['results']:
                            data['results']['values'].extend(next_data['results']['values'])
                        else:
                            data['results'].extend(next_data['results'])
                    data['next_url'] = next_data.get('next_url')
                    page_count += 1
                elif next_response.status_code == 429:
                    print(f"Rate limit reached. Stopping pagination.")
                    break
                else:
                    print(f"Failed to fetch page {page_count + 1}: {next_response.status_code}")
                    break
            
            print(f"Total pages fetched: {page_count}")
            if 'results' in data and 'values' in data['results']:
                return data['results']['values']
            else:
                return data['results']
        elif response.status_code == 429:
            print("Rate limit reached. Please try again later.")
            return None
        else:
            print(f"API request failed with status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

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

def get_ohlc(symbol, interval, limit=120):
    
    # Get the data from Kraken
    data = kraken_request(symbol, interval)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
    df[['open', 'high', 'low', 'close', 'vwap', 'volume', 'count']] = df[['open', 'high', 'low', 'close', 'vwap', 'volume', 'count']].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
    df.set_index('timestamp', inplace=True)
    data = df

    # If no data is returned, return None
    if data.size == 0:
        return None
    
    # Tail the data to get the last limit entries
    if len(data) > limit:
        data = data[-limit:]

    # Add percent return to the dataframe
    data['percent_return'] = data['close'] / data['open'] - 1

    # Add symbol to the dataframe
    data['symbol'] = symbol

    # Put dummy entry and exit points
    data["entry"] = None
    data["exit"] = None
    data["position_size"] = None
    return data

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
    