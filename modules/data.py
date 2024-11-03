import requests     
import pandas as pd
from modules.logger import logger

class DataManager:
    def __init__(self, symbol, interval, parent_interval):
        self.symbol = symbol
        self.interval = interval
        self.parent_interval = parent_interval
        self.data = pd.DataFrame()
        self.data_parent = pd.DataFrame()
        self.latest_parent_data = None
        self.data_update_counter = 0
        self.parent_interval_supported = True
        self.logger = logger
        self.parent_update_period = 0

        # Validate that parent interval is larger than base interval
        if self.parent_interval_supported:
            base_minutes = self.interval_in_minutes(self.interval)
            parent_minutes = self.interval_in_minutes(self.parent_interval)
            if parent_minutes <= base_minutes:
                raise ValueError(f"Parent interval ({parent_interval}) must be larger than base interval ({interval})")
            self._calculate_parent_update_period()

        # Validate timeframe relationship
        self._validate_timeframe_relationship()
    
    # Interval in minutes
    @staticmethod
    def interval_in_minutes(interval):
        interval_in_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440,
            '1w': 10080,
            '15d': 21600
        }
        if interval not in interval_in_minutes:
            raise ValueError(f"Invalid interval: {interval}")
        return interval_in_minutes[interval]
    
    # Update data
    def update_data(self, limit=180):
        self._get_data(limit=limit)
        self._get_parent_data(limit=int(limit/2))
        self._synchronize_data()

    # Get latest data
    def get_latest_data(self):
        return self.data.iloc[-1]

    # Get latest parent data
    def get_latest_parent_data(self):
        return self.data_parent.iloc[-1]

    # Get latest data index
    def get_latest_data_index(self):
        return self.data.index[-1]

    # Get latest parent data index
    def get_latest_parent_data_index(self):
        return self.data_parent.index[-1]

    # Calculate sleep duration
    def get_sleep_duration(self):
        base_minutes = self.interval_in_minutes(self.interval)
        return base_minutes * 60

    # Kraken request
    def _kraken_request(self, symbol, interval = "1h"):
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

        try:
            response = requests.get(url, params=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data and data['error']:
                raise ValueError(f"Kraken API error: {data['error']}")
            
            return next(iter(data['result'].values()))
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            raise

    def _get_ohlc(self, symbol, interval, limit=180):
        # Get the data from Kraken
        data = self._kraken_request(symbol, interval)

        # If no data is returned, return None
        if data is None:
            return None
        
        # Omit last row
        data = data[:-1]

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
        self._calculate_support_resistance(df)

        # Add additional columns
        df['symbol'] = symbol
        df['interval'] = interval
        df['percent_return'] = df['close'] / df['open'] - 1
        df['entry_data'] = None  # This will be a dictionary
        df['exit_data'] = None   # This will be a dictionary
        df['partial_close_data'] = None  # This will be a dictionary

        return df

    # Calculate support and resistance levels
    def _calculate_support_resistance(self, data, window=15, deviation_threshold=0.005, smoothing_periods=5, volume_factor=1.2):
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

    # Get data
    def _get_data(self, limit=180):       
        try:
            new_data = self._get_ohlc(self.symbol, interval=self.interval, limit=limit)

            if self.data.empty:
                self.data = new_data
            else:
                # Append only new data points
                last_timestamp = self.data.index[-1]
                new_data = new_data[new_data.index > last_timestamp]
                self.data = pd.concat([self.data, new_data])
        except Exception as e:
            self.logger.error(f"Error getting data: {str(e)}")
            raise
    
    # Get parent data
    def _get_parent_data(self, limit=90): 
        if not self.parent_interval_supported:
            return
        
        try:
            # Reset counter if it exceeds the update period
            if self.data_update_counter >= self.parent_update_period:
                self.data_update_counter = 0
                
            if self.data_update_counter == 0:
                new_data_parent = self._get_ohlc(self.symbol, interval=self.parent_interval, limit=limit)
                
                if self.data_parent.empty:
                    self.data_parent = new_data_parent
                else:
                    last_timestamp_parent = self.data_parent.index[-1]
                    new_data_parent = new_data_parent[new_data_parent.index > last_timestamp_parent]
                    self.data_parent = pd.concat([self.data_parent, new_data_parent])
                    
                self.logger.debug(f"Updated parent data at counter {self.data_update_counter}")
            
            self.data_update_counter += 1
            
        except Exception as e:
            self.logger.error(f"Error getting parent data: {str(e)}")
            raise

    # Validate timeframe relationship
    def _validate_timeframe_relationship(self):
        """
        Validate that the parent timeframe is properly related to the base timeframe
        """
        if not self.parent_interval_supported:
            return True
            
        base_minutes = self.interval_in_minutes(self.interval)
        parent_minutes = self.interval_in_minutes(self.parent_interval)
        
        # Parent interval must be larger
        if parent_minutes <= base_minutes:
            raise ValueError(
                f"Parent interval ({self.parent_interval}) must be larger than "
                f"base interval ({self.interval})"
            )
        
        # Ideally, parent should be a multiple of base
        if parent_minutes % base_minutes != 0:
            self.logger.warning(
                f"Parent interval ({parent_minutes}m) is not a clean multiple of "
                f"base interval ({base_minutes}m). This might cause synchronization issues."
            )
        
        return True

    # Calculate parent update period
    def _calculate_parent_update_period(self):
        """
        Calculate how often to update parent timeframe data based on the ratio
        between parent and base intervals
        """
        try:
            base_minutes = self.interval_in_minutes(self.interval)
            parent_minutes = self.interval_in_minutes(self.parent_interval)
            
            # Calculate the ratio between intervals
            self.parent_update_period = int(parent_minutes / base_minutes)
            
            # Validate the relationship
            if parent_minutes % base_minutes != 0:
                self.logger.warning(
                    f"Parent interval ({self.parent_interval}) is not a clean multiple "
                    f"of base interval ({self.interval}). This might cause synchronization issues."
                )
            
            self.logger.info(f"Parent update period set to {self.parent_update_period} base intervals")
            
        except Exception as e:
            self.logger.error(f"Error calculating parent update period: {str(e)}")
            raise

    # Synchronize data and parent data
    def _synchronize_data(self):
        """
        Synchronize parent timeframe data with current timeframe.
        Ensures we're using the correct parent candle for each current timeframe candle.
        """
        if not self.parent_interval_supported or self.data_parent.empty or self.data.empty:
            return

        try:
            current_time = self.data.index[-1]
            
            # Find the parent candle that contains the current time
            parent_data_current = self.data_parent[self.data_parent.index <= current_time]
            
            if parent_data_current.empty:
                self.logger.warning("No parent data found for current timestamp")
                self.latest_parent_data = None
                return

            latest_parent_time = parent_data_current.index[-1]
            next_parent_time = latest_parent_time + pd.Timedelta(self.parent_interval)
            
            # Verify current time falls within the parent candle's timeframe
            if latest_parent_time <= current_time < next_parent_time:
                self.latest_parent_data = parent_data_current.iloc[-1]
                self.logger.debug(f"Synchronized with parent candle: {latest_parent_time}")
            else:
                self.logger.warning(f"Current time {current_time} doesn't align with parent timeframe")
                self.latest_parent_data = None

        except Exception as e:
            self.logger.error(f"Error during data synchronization: {str(e)}")
            self.latest_parent_data = None
