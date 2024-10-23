from abc import ABC, abstractmethod
import logging
from modules.rest_api import get_ohlc
import datetime
from time import sleep
import pandas as pd
import pandas_ta as ta
from modules.graph import draw_graph
from logging.handlers import RotatingFileHandler
import numpy as np
import sys

# A base class for all strategies
class Strategy(ABC):
    def __init__(self, symbol, interval, balance, risk_percentage=1, stop_loss_percentage=8):
        self.name = self.__class__.__name__
        self.symbol = symbol
        self.interval = interval # minute, hour, 4-hour, day, week, 15-days
        self.active = True
        self.simulation = True
        self.position = None
        self.balance = balance
        self.data = pd.DataFrame()
        self.stop_loss_percentage = stop_loss_percentage
        self.risk_percentage = risk_percentage
        self.entry_price = 0
        self.stop_loss_price = 0
        self.position_size = 0
        self.trade_history = []
        self.performance_metrics = {}
        self.slippage_percentage = 0.1
        
        # Check if symbol is valid
        # try:
        #     if get_symbol_details(self.symbol) is None:
        #         raise ValueError(f"Symbol {self.symbol} not found")
        # except Exception as e:
        #     print(f"Error initializing strategy: {str(e)}")
        #     exit()

        # Set up logger
        self.logger = logging.getLogger(f"{self.name}_{self.symbol}")
        self.logger.setLevel(logging.INFO)
        
        # Create a rotating file handler
        import os
        if not os.path.exists('logs'):
            os.makedirs('logs')
        log_file = f"logs/{self.name}_{self.symbol}.log"
        fh = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)  # 1MB per file, keep 5 old files
        fh.setLevel(logging.INFO)
        
        # Create a console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create a more readable formatter
        class ColoredFormatter(logging.Formatter):
            COLORS = {
                'INFO': '\033[92m',  # Green
                'WARNING': '\033[93m',  # Yellow
                'ERROR': '\033[91m',  # Red
                'CRITICAL': '\033[91m\033[1m',  # Bold Red
                'RESET': '\033[0m'  # Reset color
            }

            def format(self, record):
                log_message = super().format(record)
                return f"{self.COLORS.get(record.levelname, self.COLORS['RESET'])}{log_message}{self.COLORS['RESET']}"

        formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add the handlers to the logger
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        self.logger.info(f"Initialized {self.name} strategy for {self.symbol}")
        self.logger.info(f"  - interval: {self.interval}")
        self.logger.info(f"  - Balance: ${self.balance}")
        self.logger.info(f"  - Stop Loss Percentage: {self.stop_loss_percentage}%")
        self.logger.info(f"  - Risk Percentage: {self.risk_percentage}%")
        self.logger.info("--------------------------------")

    # Check entry
    @abstractmethod
    def check_entry(self):
        pass

    # Check exit
    @abstractmethod
    def check_exit(self):
        pass

    @abstractmethod
    def check_partial_close(self):
        pass

    # Run strategy
    def run(self):
        if not self.active:
            self.logger.warning("Strategy is not active. Skipping run.")
            return

        def run_strategy():
            try:
                self.get_data()

                if self.position is None:
                    entry_signal = self.check_entry()
                    if entry_signal == "long":
                        self.long()
                    elif entry_signal == "short":
                        self.short()
                else:
                    if self.check_exit():
                        self.close_position()
                    self.check_trailing_stop_loss()
                    self.check_partial_close()
            except Exception as e:
                self.logger.error(f"Error during strategy execution: {str(e)}")
                self.active = False
            
            sleep_duration = self.calculate_sleep_duration()
            sleep(sleep_duration)

        from threading import Thread
        thread = Thread(target=run_strategy)
        thread.start()
    
    # Get data
    def get_data(self, limit=180):
        try:
            new_data = get_ohlc(self.symbol, interval=self.interval, limit=limit)
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
    
    # Long position
    def long(self):
        self.logger.info("Entering Long")
        self.position = "long"
        self.calculate_position_size()
        self.execute_trade("long", self.position_size)

    # Short position
    def short(self):
        self.logger.info("Entering Short")
        self.position = "short"
        self.calculate_position_size()
        self.execute_trade("short", self.position_size)

    # Close position
    def close_position(self):
        if self.position is not None:
            self.execute_trade("close", self.position_size)
        else:
            self.logger.warning("Attempted to close position, but no position is open")
    
    # Partial close position
    def partial_close(self, percentage, reason):
        if self.position is None:
            self.logger.warning(f"Cannot partially close: no position open")
            return

        if not 0 < percentage <= 100:
            self.logger.warning(f"Invalid percentage for partial close: {percentage}")
            return

        close_size = self.position_size * (percentage / 100)
        self.logger.info(f"{reason} - Partially closing {percentage}% of position")
        
        # Execute the trade first
        self.execute_trade(f"partial close ({reason})", close_size)

        # Now perform calculations based on the updated state
        current_price = self.data['close'][-1]
        if self.position == "long":
            profit_loss = (current_price - self.entry_price) * close_size
        else:  # short position
            profit_loss = (self.entry_price - current_price) * close_size

        # Update position size
        self.position_size -= close_size

        # Adjust entry price after partial close
        self.adjust_entry_price(close_size, profit_loss)

    # Adjust entry price
    def adjust_entry_price(self, closed_size, realized_pnl):
        if self.position is None or self.position_size == 0:
            return

        # Calculate the remaining cost basis
        remaining_cost = (self.entry_price * (self.position_size + closed_size)) - realized_pnl
        
        # Calculate the new entry price
        self.entry_price = remaining_cost / self.position_size
        
        self.logger.info(f"Adjusted entry price to: ${self.entry_price:.2f}")

    # Execute trade
    def execute_trade(self, action, size):
        try:
            current_price = self.data['close'][-1]
            
            # Apply slippage if simulation is active
            if self.simulation:
                if action == "long":
                    execution_price = current_price * (1 + self.slippage_percentage / 100)
                elif action == "short":
                    execution_price = current_price * (1 - self.slippage_percentage / 100)
                elif action.startswith("partial close") or action == "close":
                    if self.position == "long":
                        execution_price = current_price * (1 - self.slippage_percentage / 100)
                    else:  # short position
                        execution_price = current_price * (1 + self.slippage_percentage / 100)
            else:
                # Actual trade execution from broker
                # execution_price = current_price
                pass

            total_amount = size * execution_price
            self.logger.info(f"Executing {action} trade for {size:.4f} units of {self.symbol} at ${execution_price:.2f} (Total: ${total_amount:.2f})")
            
            trade_info = {
                'action': action,
                'price': execution_price,
                'size': size,
                'date': datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
            }
            if action == "close" or action.startswith("partial close"):
                if self.position == "long":
                    profit_loss = (execution_price - self.entry_price) * size
                    percentage_gain_loss = ((execution_price / self.entry_price) - 1) * 100
                else:  # short position
                    profit_loss = (self.entry_price - execution_price) * size
                    percentage_gain_loss = ((self.entry_price / execution_price) - 1) * 100
                
                trade_info['profit_loss'] = profit_loss
                trade_info['percentage_gain_loss'] = percentage_gain_loss
                trade_result = "win" if profit_loss > 0 else "loss"
                trade_info['result'] = trade_result
                
                result_str = "Profit" if profit_loss > 0 else "Loss"
                self.logger.info(f"Trade Result: {result_str} of ${abs(profit_loss):.2f} ({percentage_gain_loss:.2f}%) - Outcome: {trade_result.title()}")
                
                # Update balance
                self.balance += profit_loss
                
                if action == "close":
                    self.position = None
                    self.position_size = 0
                    self.data.loc[self.data.index[-1], "exit"] = execution_price # Put exit point in data for full close
                else:
                    self.position_size -= size
                    self.data.loc[self.data.index[-1], "partial_close"] = execution_price # Put partial close point in data
                    
                # Update position size in data
                self.data.loc[self.data.index[-1], "position_size"] = self.position_size
                self.data.loc[self.data.index[-1], "percentage_gain_loss"] = percentage_gain_loss

            elif action in ["long", "short"]:
                self.position = action
                self.entry_price = execution_price
                self.position_size = size
                
                # Put entry point in data
                self.data.loc[self.data.index[-1], "entry"] = execution_price
                self.data.loc[self.data.index[-1], "position_size"] = size
            
            self.trade_history.append(trade_info)
            self.update_performance_metrics()
        
        except Exception as e:
            self.logger.error(f"Error executing trade: {str(e)}")
            raise
    
    # Calculate position size based on risk percentage
    def calculate_position_size(self):
        if self.data.empty:
            raise ValueError("OHLC data not available. Cannot calculate position size.")

        current_price = self.data['close'][-1]
        stop_loss_amount = current_price * (self.stop_loss_percentage / 100)
        
        risk_amount = self.balance * (self.risk_percentage / 100)
        self.logger.info(f"Risk amount: ${risk_amount:.2f}")
        self.logger.info(f"Stop loss amount: ${stop_loss_amount:.2f}")

        if stop_loss_amount == 0:
            self.logger.warning("Stop loss amount is zero. Cannot calculate position size.")
            self.position_size = 0
        else:
            self.position_size = risk_amount / stop_loss_amount
        self.entry_price = current_price

        self.logger.info(f"Position size: {self.position_size:.4f}")

        if self.position == "long":
            self.stop_loss_price = current_price - stop_loss_amount
        elif self.position == "short":
            self.stop_loss_price = current_price + stop_loss_amount
        else:
            raise ValueError("Position type not set. Cannot calculate stop loss price.")

        self.logger.info(f"Position Details:")
        self.logger.info(f"  - Size: {self.position_size:.4f} units")
        self.logger.info(f"  - Entry Price: ${self.entry_price:.2f}")
        self.logger.info(f"  - Stop Loss: ${self.stop_loss_price:.2f}")

    # Check trailing stop loss
    def check_trailing_stop_loss(self, trail_percentage=1):
        if self.position is None:
            return

        current_price = self.data['close'][-1]
        trail_amount = self.entry_price * (trail_percentage / 100)

        if self.position == "long":
            trail_stop = current_price - trail_amount
            if trail_stop > self.stop_loss_price:
                self.stop_loss_price = trail_stop
                self.logger.info(f"Updated trailing stop loss: ${self.stop_loss_price:.2f}")
            
            if current_price <= self.stop_loss_price:
                self.logger.info(f"Trailing stop loss triggered at ${current_price:.2f}")
                self.close_position()

        elif self.position == "short":
            trail_stop = current_price + trail_amount
            if trail_stop < self.stop_loss_price or self.stop_loss_price == 0:
                self.stop_loss_price = trail_stop
                self.logger.info(f"Updated trailing stop loss: ${self.stop_loss_price:.2f}")
            
            if current_price >= self.stop_loss_price:
                self.logger.info(f"Trailing stop loss triggered at ${current_price:.2f}")
                self.close_position()
    
    # Calculate support and resistance levels
    def calculate_support_resistance(self, window=20, deviation_threshold=0.01, smoothing_periods=5, volume_factor=1.5):
        """
        Calculate support and resistance levels using local minima and maxima with additional filtering.
        
        :param window: The number of periods to consider for local extrema
        :param deviation_threshold: The minimum price deviation to consider as a new level
        :param smoothing_periods: Number of periods for moving average smoothing
        :param volume_factor: Factor to consider a volume spike
        :return: A dictionary containing lists of support and resistance levels
        """
        self.logger.info("Calculating support and resistance levels")
        
        # Apply smoothing to reduce noise
        highs = self.data['high'].rolling(window=smoothing_periods).mean()
        lows = self.data['low'].rolling(window=smoothing_periods).mean()
        volumes = self.data['volume']
        
        resistance_levels = []
        support_levels = []
        
        # Calculate average volume
        avg_volume = volumes.mean()
        
        for i in range(window, len(self.data) - window):
            # Check for resistance
            if all(highs[i] > highs[i-window:i]) and all(highs[i] > highs[i+1:i+window+1]):
                # Check if this is a significant new level
                if not resistance_levels or abs(highs[i] - resistance_levels[-1]) / resistance_levels[-1] > deviation_threshold:
                    # Check for volume confirmation
                    if volumes[i] > avg_volume * volume_factor:
                        resistance_levels.append(highs[i])
            
            # Check for support
            if all(lows[i] < lows[i-window:i]) and all(lows[i] < lows[i+1:i+window+1]):
                # Check if this is a significant new level
                if not support_levels or abs(lows[i] - support_levels[-1]) / support_levels[-1] > deviation_threshold:
                    # Check for volume confirmation
                    if volumes[i] > avg_volume * volume_factor:
                        support_levels.append(lows[i])
        
        # Cluster nearby levels
        resistance_levels = self.cluster_levels(resistance_levels)
        support_levels = self.cluster_levels(support_levels)
        
        self.logger.info(f"Found {len(resistance_levels)} resistance levels and {len(support_levels)} support levels")
        
        return {
            'resistance': resistance_levels,
            'support': support_levels
        }

    def cluster_levels(self, levels, cluster_threshold=0.01):
        """
        Cluster nearby levels to reduce redundancy.
        
        :param levels: List of price levels
        :param cluster_threshold: Maximum deviation to consider levels as part of the same cluster
        :return: List of clustered levels
        """
        if not levels:
            return []
        
        levels.sort()
        clustered = [levels[0]]
        
        for level in levels[1:]:
            if (level - clustered[-1]) / clustered[-1] > cluster_threshold:
                clustered.append(level)
            else:
                clustered[-1] = (clustered[-1] + level) / 2  # Average of the cluster
        
        return clustered

    # Update performance metrics
    def update_performance_metrics(self):
        try:
            if len(self.trade_history) > 0:
                closed_trades = [trade for trade in self.trade_history if trade['action'] == 'close']

                if len(closed_trades) < 1:
                    return
                
                self.performance_metrics['total_trades'] = len(closed_trades)
                
                winning_trades = [trade for trade in closed_trades if trade['result'] == 'win']
                losing_trades = [trade for trade in closed_trades if trade['result'] == 'loss']
                
                self.performance_metrics['win_rate'] = len(winning_trades) / len(closed_trades) if closed_trades else 0
                
                total_profit = sum(trade['profit_loss'] for trade in winning_trades)
                total_loss = abs(sum(trade['profit_loss'] for trade in losing_trades))
                
                if total_loss == 0:
                    if total_profit > 0:
                        self.performance_metrics['profit_factor'] = float('inf')
                    else:
                        self.performance_metrics['profit_factor'] = 0
                else:
                    self.performance_metrics['profit_factor'] = total_profit / total_loss
                
                self.performance_metrics['total_profit_loss'] = total_profit - total_loss
                
                self.logger.info("Updated Performance Metrics:")
                self.logger.info(f"  - Total Trades: {self.performance_metrics['total_trades']}")
                self.logger.info(f"  - Win Rate: {self.performance_metrics['win_rate']:.2%}")
                self.logger.info(f"  - Profit Factor: {self.performance_metrics['profit_factor']:.2f}")
                self.logger.info(f"  - Total Profit/Loss: ${self.performance_metrics['total_profit_loss']:.2f}")
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {str(e)}")

    # Update strategy parameters dynamically
    def update_parameters(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                self.logger.info(f"Updated {key} to {value}")
            else:
                self.logger.warning(f"Attribute {key} not found in strategy")
    
    # Put live
    def put_live(self):
        self.simulation = False
        self.active = True
    
    # Put live simulation
    def put_live_simulation(self):
        self.simulation = True
        self.active = True
    
    # Put inactive
    def put_inactive(self):
        self.simulation = False
        self.active = False

    def print_progress_bar(self, current, total, prefix='', suffix='', decimals=1, length=30, fill='=', print_end="\r"):
        """
        Call in a loop to create terminal progress bar
        @params:
            current   - Required  : current iteration (Int)
            total     - Required  : total iterations (Int)
            prefix    - Optional  : prefix string (Str)
            suffix    - Optional  : suffix string (Str)
            decimals  - Optional  : positive number of decimals in percent complete (Int)
            length    - Optional  : character length of bar (Int)
            fill      - Optional  : bar fill character (Str)
            print_end - Optional  : end character (e.g. "\r", "\r\n") (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (current / float(total)))
        filled_length = int(length * current // total)
        bar = fill * filled_length + '-' * (length - filled_length)
        print(f'\r{prefix} [{bar}] {percent}% {suffix}', end=print_end)
        # Print New Line on Complete
        if current == total: 
            print()

    # Backtest
    def backtest(self, duration):
        self.position = None
        self.balance = 1000
        self.trade_history = []
        self.performance_metrics = {}
        self.entry_price = 0
        self.stop_loss_price = 0
        self.position_size = 0
        self.simulation = True
        self.backtest = True
        offset = 50
        
        # Clear all logs in file
        with open(f"logs/{self.name}_{self.symbol}.log", 'w') as file:
            file.truncate()

        self.logger.info(f"Starting backtest for {duration} periods")

        # Temporarily remove console handler
        console_handler = None
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                console_handler = handler
                self.logger.removeHandler(handler)
                break

        # Get data for the duration of the backtest
        self.get_data(limit=duration+offset)
        original_data = self.data.copy()
        
        total_periods = len(original_data) - offset
        for i in range(total_periods):
            # Use data up to the current index
            self.data = original_data[:i+1+offset].copy()

            # Update progress bar
            self.print_progress_bar(i + 1, total_periods, prefix='Backtesting:', suffix='Complete', length=30)

            try:
                if self.position is None:
                    entry_signal = self.check_entry()
                    if entry_signal == "long":
                        self.long()
                    elif entry_signal == "short":
                        self.short()
                else:
                    if self.check_exit():
                        self.close_position()
                    self.check_trailing_stop_loss()
                    self.check_partial_close()
                    
                # Preserve entry and exit points
                if 'entry' in self.data.columns:
                    original_data.loc[self.data.index[-1], 'entry'] = self.data['entry'].iloc[-1]
                if 'exit' in self.data.columns:
                    original_data.loc[self.data.index[-1], 'exit'] = self.data['exit'].iloc[-1]
                
            except Exception as e:
                self.logger.error(f"Error during backtest execution: {str(e)}")
                break

        # Print a newline after the progress bar is complete
        print()

        # Restore console handler
        if console_handler:
            self.logger.addHandler(console_handler)

        self.logger.info("Backtest completed")
        self.log_backtest_results()
        self.logger.info("Graphing results")
        draw_graph(self.data, limit=duration)
        self.logger.info("Results graphed")

    def log_backtest_results(self):
        self.logger.info("Backtest Results:")
        self.logger.info(f"Total Trades: {self.performance_metrics.get('total_trades', 0)}")
        self.logger.info(f"Win Rate: {self.performance_metrics.get('win_rate', 0):.2%}")
        self.logger.info(f"Profit Factor: {self.performance_metrics.get('profit_factor', 0):.2f}")
        self.logger.info(f"Total Profit/Loss: ${self.performance_metrics.get('total_profit_loss', 0):.2f}")
        self.logger.info(f"Final Balance: ${self.balance:.2f}")

    # Calculate sleep duration
    def calculate_sleep_duration(self):
        interval_in_seconds = {
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
        return interval_in_seconds.get(self.interval, 60)
    
