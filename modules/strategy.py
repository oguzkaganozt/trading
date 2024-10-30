from abc import ABC, abstractmethod
import logging
from modules.rest_api import get_ohlc
import datetime
from time import sleep
import pandas as pd
from modules.graph import draw_graph
from logging.handlers import RotatingFileHandler
import os

# A base class for all strategies
class Strategy(ABC):
    def __init__(self, symbol, interval, balance, parent_interval=None, risk_percentage=10, trailing_stop_percentage=0):
        self.name = self.__class__.__name__
        self.symbol = symbol
        self.interval = interval # 30m, 1h, 4h, 1d, 1w
        self.parent_interval = parent_interval # 1h, 4h, 1d, 1w, 15d
        self.active = True
        self.simulation = True
        self.position = None
        self.balance = balance
        self.data = pd.DataFrame()
        self.data_parent = pd.DataFrame()
        self.trailing_stop_percentage = trailing_stop_percentage
        self.risk_percentage = risk_percentage
        self.entry_price = 0
        self.stop_loss_price = 0
        self.extreme_price_since_entry = 0
        self.position_size = 0
        self.trade_history = []
        self.performance_metrics = {}
        self.slippage_percentage = 0.1
        self.parent_interval_supported = True
        self.parent_update_period = None
        self.data_update_counter = 0
        self.latest_parent_data = None
                
        # Clear all logs in file if it exists
        if os.path.exists(f"logs/{self.name}_{self.symbol}.log"):
            with open(f"logs/{self.name}_{self.symbol}.log", 'w') as file:
                file.truncate()
        
        # Set up logger
        self.logger = logging.getLogger(f"{self.name}_{self.symbol}")
        self.logger.setLevel(logging.INFO)
        
        # Create a rotating file handler
        if not os.path.exists('logs'):
            os.makedirs('logs')
        log_file = f"logs/{self.name}_{self.symbol}.log"
        fh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=10)  # 10MB per file, keep 10 old files
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

        # Log strategy details
        self.logger.info(f"Initialized {self.name} strategy for {self.symbol}")
        self.logger.info(f"  - interval: {self.interval}")
        self.logger.info(f"  - parent interval: {self.parent_interval}")
        self.logger.info(f"  - Balance: ${self.balance}")
        self.logger.info(f"  - Trailing Stop Percentage: {self.trailing_stop_percentage}%")
        self.logger.info(f"  - Risk Percentage: {self.risk_percentage}%")
        self.logger.info("--------------------------------")

        # Validate that parent interval is larger than base interval
        if self.parent_interval_supported:
            base_minutes = self.interval_in_minutes(self.interval)
            parent_minutes = self.interval_in_minutes(self.parent_interval)
            if parent_minutes <= base_minutes:
                raise ValueError(f"Parent interval ({parent_interval}) must be larger than base interval ({interval})")
            self.calculate_parent_update_period()

        # Validate timeframe relationship
        self.validate_timeframe_relationship()

    # Check entry
    @abstractmethod
    def check_entry(self):
        self.logger.debug("Checking entry")
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
                self.get_parent_data()
                self.synchronize_data()

                if self.position is None:
                    entry_signal = self.check_entry()
                    if entry_signal == "long":
                        self.long()
                    elif entry_signal == "short":
                        self.short()
                else:
                    if self.check_exit():
                        self.close_position("exit")
                    self.check_trailing_stop_loss()
                    if percentage := self.check_partial_close():
                        self.partial_close(percentage=percentage)
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
    
    # Get parent data
    def get_parent_data(self, limit=50): 
        if not self.parent_interval_supported:
            return
        
        try:
            # Reset counter if it exceeds the update period
            if self.data_update_counter >= self.parent_update_period:
                self.data_update_counter = 0
                
            if self.data_update_counter == 0:
                new_data_parent = get_ohlc(self.symbol, interval=self.parent_interval, limit=limit)
                
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
    def close_position(self, reason="exit"):
        if self.position is not None:
            self.execute_trade("close", self.position_size, reason=reason)
        else:
            self.logger.warning("Attempted to close position, but no position is open")
    
    # Partial close position
    def partial_close(self, percentage):
        if self.position is None:
            self.logger.warning(f"Cannot partially close: no position open")
            return

        if not 0 < percentage <= 100:
            self.logger.warning(f"Invalid percentage for partial close: {percentage}")
            return

        close_size = self.position_size * (percentage / 100)
        self.logger.info(f"Partially closing {percentage}% of position")
        
        # Execute the trade first
        self.execute_trade(f"partial close", close_size)

        # Now perform calculations based on the updated state
        current_price = self.data['close'].iloc[-1]
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
    def execute_trade(self, action, size, reason=None):
        try:
            current_price = self.data['close'].iloc[-1]
            
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
                'symbol': self.symbol,
                'interval': self.interval,
                'index': self.data.index[-1],
                'action': action,
                'price': execution_price,
                'size': size,
                'amount': total_amount,
                'date': datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p'),
                'reason': reason
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
                
                last_index = self.data.index[-1]
                if action == "close":
                    self.data.at[last_index, "exit_data"] = trade_info
                    self.position = None
                    self.position_size = 0
                else:
                    self.data.at[last_index, "partial_close_data"] = trade_info
                    self.position_size -= size

            elif action in ["long", "short"]:
                self.position = action
                self.entry_price = execution_price
                self.position_size = size
                
                # Put entry data in DataFrame
                last_index = self.data.index[-1]
                self.data.at[last_index, "entry_data"] = trade_info

            self.trade_history.append(trade_info)
            self.update_performance_metrics()
        
        except Exception as e:
            self.logger.error(f"Error executing trade: {str(e)}")
            raise
    
    # Calculate position size based on risk percentage
    def calculate_position_size(self):
        if self.data.empty:
            raise ValueError("OHLC data not available. Cannot calculate position size.")

        current_price = self.data['close'].iloc[-1]
        risk_amount = self.balance * (self.risk_percentage / 100)
        self.logger.info(f"Risk amount: ${risk_amount:.2f}")
        
        # Calculate position size based on risk amount
        self.position_size = risk_amount / current_price
        
        self.entry_price = current_price
        self.logger.info(f"Position size: {self.position_size:.4f}")
        
        self.logger.info(f"Position Details:")
        self.logger.info(f"  - Size: {self.position_size:.4f} units")
        self.logger.info(f"  - Entry Price: ${self.entry_price:.2f}")

    # Check trailing stop loss
    def check_trailing_stop_loss(self):
        if self.position is None or self.trailing_stop_percentage == 0:
            return

        is_long = self.position == "long"
        current_price = self.data['close'].iloc[-1]
        
        # Set initial stop loss
        if self.stop_loss_price == 0:
            multiplier = (1 - self.trailing_stop_percentage / 100) if is_long else (1 + self.trailing_stop_percentage / 100)
            self.stop_loss_price = self.entry_price * multiplier
            self.extreme_price_since_entry = self.entry_price
            self.logger.info(f"Initial stop loss set at ${self.stop_loss_price:.2f}")
            return

        prev_candle = self.data.iloc[-2]
        
        # Update extreme price and calculate new stop
        if is_long:
            self.extreme_price_since_entry = max(self.extreme_price_since_entry, prev_candle['close'])
            new_stop = self.extreme_price_since_entry * (1 - self.trailing_stop_percentage / 100)
            should_update = new_stop > self.stop_loss_price
            stop_triggered = current_price <= self.stop_loss_price
        else:
            self.extreme_price_since_entry = min(self.extreme_price_since_entry, prev_candle['close'])
            new_stop = self.extreme_price_since_entry * (1 + self.trailing_stop_percentage / 100)
            should_update = new_stop < self.stop_loss_price
            stop_triggered = current_price >= self.stop_loss_price

        # Update stop if needed
        if should_update:
            old_stop = self.stop_loss_price
            self.stop_loss_price = new_stop
            self.logger.info(f"Updated trailing stop: ${old_stop:.2f} -> ${new_stop:.2f} "
                           f"(Extreme {'high' if is_long else 'low'}: ${self.extreme_price_since_entry:.2f})")

        # Close position if stop is triggered
        if stop_triggered:
            self.logger.info(f"Trailing stop triggered at ${current_price:.2f} (Stop: ${self.stop_loss_price:.2f})")
            self.close_position(reason="trailing stop loss")

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
                self.performance_metrics['win_trades'] = len(winning_trades)
                self.performance_metrics['loss_trades'] = len(losing_trades)
                
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
                self.performance_metrics['total_profit_loss_percentage'] = (self.performance_metrics['total_profit_loss'] / self.balance) * 100
                
                self.logger.info("Updated Performance Metrics:")
                self.logger.info(f"  - Total Trades: {self.performance_metrics['total_trades']}")
                self.logger.info(f"  - Win Rate: {self.performance_metrics['win_rate']:.2%}")
                self.logger.info(f"  - Profit Factor: {self.performance_metrics['profit_factor']:.2f}")
                self.logger.info(f"  - Total Profit/Loss: ${self.performance_metrics['total_profit_loss']:.2f} ({self.performance_metrics['total_profit_loss_percentage']:.2f}%)")
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

        self.logger.info(f"Starting backtest for {duration} periods")

        # Temporarily remove console handler
        console_handler = None
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                console_handler = handler
                self.logger.removeHandler(handler)
                break

        # Calculate appropriate offsets for both timeframes
        offset = 50
        if self.parent_interval_supported:
            parent_offset = max(50, int(offset * self.interval_in_minutes(self.interval) / self.interval_in_minutes(self.parent_interval)))
        else:
            parent_offset = offset

        # Get data for the duration of the backtest
        self.get_data(limit=duration+offset)
        self.get_parent_data(limit=duration+parent_offset)
        original_data = self.data.copy()

        if self.parent_interval_supported:
            original_data_parent = self.data_parent.copy()
        
        total_periods = len(original_data) - offset

        if total_periods < 1:
            self.logger.error("Not enough data to perform backtest")
            return

        for i in range(total_periods):
            # Use data up to the current index
            current_time = original_data.index[i+offset]
            self.data = original_data[:i+1+offset].copy()
            
            if self.parent_interval_supported:
                # Only include parent data up to the current timestamp
                self.data_parent = original_data_parent[original_data_parent.index <= current_time].copy()
                self.synchronize_data()

            # Update progress bar
            self.print_progress_bar(i + 1, total_periods)

            try:
                if self.position is None:
                    entry_signal = self.check_entry()
                    if entry_signal == "long":
                        self.long()
                    elif entry_signal == "short":
                        self.short()
                else:
                    if self.check_exit():
                        self.close_position("exit")
                    self.check_trailing_stop_loss()
                    if percentage := self.check_partial_close():
                        self.partial_close(percentage=percentage)
                    
                # Preserve entry and exit points
                last_index = self.data.index[-1]
                if pd.notna(self.data.at[last_index, 'entry_data']):
                    original_data.at[last_index, 'entry_data'] = self.data.at[last_index, 'entry_data']
                if pd.notna(self.data.at[last_index, 'exit_data']):
                    original_data.at[last_index, 'exit_data'] = self.data.at[last_index, 'exit_data']
                if pd.notna(self.data.at[last_index, 'partial_close_data']):
                    original_data.at[last_index, 'partial_close_data'] = self.data.at[last_index, 'partial_close_data']

            except Exception as e:
                self.logger.error(f"Error during backtest execution: {str(e)}")
                break

        # Restore console handler
        if console_handler:
            self.logger.addHandler(console_handler)

        self.logger.info("Backtest completed")
        self.logger.info("Graphing results")
        summary = self.log_backtest_results()
        draw_graph(self.data, limit=duration, summary=summary)
        self.logger.info("Results graphed")
        return summary
    
    def log_backtest_results(self):
        results = f"""Backtest Results for Strategy: {self.name} {self.symbol} - {self.interval}
                    Total Trades: {self.performance_metrics.get('total_trades', 0)}
                    Win Rate: {self.performance_metrics.get('win_rate', 0):.2%}
                    Profit Factor: {self.performance_metrics.get('profit_factor', 0):.2f}
                    Total Profit/Loss: ${self.performance_metrics.get('total_profit_loss', 0):.2f}
                    Final Balance: ${self.balance:.2f}"""
        
        summary = {}
        summary['name'] = self.name
        summary['symbol'] = self.symbol
        summary['interval'] = self.interval
        summary['win_trades'] = self.performance_metrics.get('win_trades', 0)
        summary['loss_trades'] = self.performance_metrics.get('loss_trades', 0)
        summary['profit_factor'] = self.performance_metrics.get('profit_factor', 0)
        summary['total_profit_loss_percentage'] = self.performance_metrics.get('total_profit_loss_percentage', 0)

        self.logger.info(results)
        return summary

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

    # Calculate parent update period
    def calculate_parent_update_period(self):
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
    
    # Calculate sleep duration
    def calculate_sleep_duration(self):
        base_minutes = self.interval_in_minutes(self.interval)
        return base_minutes * 60
    
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

    def print_progress_bar(self, current, total):
        """
        Print a simple progress bar to the console.
        @params:
            current   - Required  : current iteration (Int)
            total     - Required  : total iterations (Int)
        """
        percent = f"{100 * (current / float(total)):.1f}"
        filled_length = int(30 * current // total)
        bar = '=' * filled_length + '-' * (30 - filled_length)
        print(f'\rProgress: [{bar}] {percent}%', end='')
        
        if current == total: 
            print()

    # Synchronize data and parent data
    def synchronize_data(self):
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

    def validate_timeframe_relationship(self):
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
