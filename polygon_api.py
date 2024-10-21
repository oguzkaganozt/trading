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

def polygon_request(url, params, max_pages=10):
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

def get_ohlc(symbol, timespan, multiplier, limit=120, days_back=1095):
    # Calculate date range
    #  end_date = datetime.datetime.now(datetime.timezone.utc) # open once we got premium
    end_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
    start_date = end_date - datetime.timedelta(days=days_back)

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{int(start_date.timestamp() * 1000)}/{int(end_date.timestamp() * 1000)}"
    params = {
        "adjusted": "true",
        "apiKey": REST_API_KEY,
        "sort": "desc"
    }
    
    data = polygon_request(url, params)
    if not data:
        return None
    
    # Tail the data to get the last limit entries
    if len(data) > limit:
        data = data[:limit]
    
    # Reverse the data to chronological order (oldest first)
    data = list(reversed(data))
    
    # Remap the data to have the date as a datetime object
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['t'], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Rename and reorder columns
    column_mapping = {'o': 'open', 'c': 'close', 'h': 'high', 'l': 'low', 'v': 'volume'}
    df = df.rename(columns=column_mapping)[['date'] + list(column_mapping.values())]
    
    # Set 'date' as index
    df.set_index('date', inplace=True)

    # Add percent return to the dataframe
    df['percent_return'] = df['close'] / df['open'] - 1

    # Add symbol to the dataframe
    df['symbol'] = symbol

    # Put dummy entry and exit points
    df["entry"] = None
    df["exit"] = None
    
    return df

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
    