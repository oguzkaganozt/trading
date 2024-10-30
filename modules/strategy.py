from abc import ABC, abstractmethod
import datetime
from time import sleep
import pandas as pd
from modules.graph import draw_graph
from modules.logger import logger 
from modules.data import DataManager

# A base class for all strategies
class Strategy(ABC):
    def __init__(self, symbol, interval, balance, parent_interval=None, risk_percentage=10, trailing_stop_percentage=0):
        self.name = self.__class__.__name__
        self.symbol = symbol
        self.balance = balance
        self.interval = interval # 30m, 1h, 4h, 1d, 1w
        self.parent_interval = parent_interval # 1h, 4h, 1d, 1w, 15d
        self.data_manager = DataManager(symbol, interval, parent_interval)
        self.logger = logger
        self.active = True
        self.simulation = True
        self.trailing_stop_percentage = trailing_stop_percentage
        self.risk_percentage = risk_percentage
        self.position = None
        self.entry_price = 0
        self.stop_loss_price = 0
        self.position_size = 0
        self.trade_history = []
        self.performance_metrics = {}
        self.slippage_percentage = 0.1

        # Log strategy details
        self.logger.info(f"Initialized {self.name} strategy for {self.symbol}")
        self.logger.info(f"  - interval: {self.interval}")
        self.logger.info(f"  - parent interval: {self.parent_interval}")
        self.logger.info(f"  - Balance: ${self.balance}")
        self.logger.info(f"  - Trailing Stop Percentage: {self.trailing_stop_percentage}%")
        self.logger.info(f"  - Risk Percentage: {self.risk_percentage}%")
        self.logger.info("--------------------------------")

    # Check entry
    @abstractmethod
    def check_entry(self):
        self.logger.debug("Checking entry")
        pass

    # Check exit
    @abstractmethod
    def check_exit(self):
        pass
    
    # Check partial close
    @abstractmethod
    def check_partial_close(self):
        pass
    
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
        current_price = self.data_manager.data['close'].iloc[-1]
        if self.position == "long":
            profit_loss = (current_price - self.entry_price) * close_size
        else:  # short position
            profit_loss = (self.entry_price - current_price) * close_size

        # Update position size
        self.position_size -= close_size

        # Adjust entry price after partial close
        self.adjust_entry_price(close_size, profit_loss)
    
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
    
    # Run strategy
    def run(self):
        if not self.active:
            self.logger.warning("Strategy is not active. Skipping run.")
            return

        def run_strategy():
            try:
                self.data_manager.update_data()

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
            
            sleep(self.data_manager.get_sleep_duration())

        from threading import Thread
        thread = Thread(target=run_strategy)
        thread.start()

    # Execute trade
    def execute_trade(self, action, size, reason=None):
        try:
            current_price = self.data_manager.data['close'].iloc[-1]
            
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
                'index': self.data_manager.data.index[-1],
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
                
                last_index = self.data_manager.data.index[-1]
                if action == "close":
                    self.data_manager.data.at[last_index, "exit_data"] = trade_info
                    self.position = None
                    self.position_size = 0
                else:
                    self.data_manager.data.at[last_index, "partial_close_data"] = trade_info
                    self.position_size -= size

            elif action in ["long", "short"]:
                self.position = action
                self.entry_price = execution_price
                self.position_size = size
                
                # Put entry data in DataFrame
                last_index = self.data_manager.data.index[-1]
                self.data_manager.data.at[last_index, "entry_data"] = trade_info

            self.trade_history.append(trade_info)
            self.update_performance_metrics()
        
        except Exception as e:
            self.logger.error(f"Error executing trade: {str(e)}")
            raise
    
    # Calculate position size based on risk percentage
    def calculate_position_size(self):
        if self.data_manager.data.empty:
            raise ValueError("OHLC data not available. Cannot calculate position size.")

        current_price = self.data_manager.data['close'].iloc[-1]
        risk_amount = self.balance * (self.risk_percentage / 100)
        self.logger.info(f"Risk amount: ${risk_amount:.2f}")
        
        # Calculate position size based on risk amount
        self.position_size = risk_amount / current_price
        
        self.entry_price = current_price
        self.logger.info(f"Position size: {self.position_size:.4f}")
        
        self.logger.info(f"Position Details:")
        self.logger.info(f"  - Size: {self.position_size:.4f} units")
        self.logger.info(f"  - Entry Price: ${self.entry_price:.2f}")
    
    # Adjust entry price
    def adjust_entry_price(self, closed_size, realized_pnl):
        if self.position is None or self.position_size == 0:
            return

        # Calculate the remaining cost basis
        remaining_cost = (self.entry_price * (self.position_size + closed_size)) - realized_pnl
        
        # Calculate the new entry price
        self.entry_price = remaining_cost / self.position_size
        
        self.logger.info(f"Adjusted entry price to: ${self.entry_price:.2f}")

    # Check trailing stop loss
    def check_trailing_stop_loss(self):
        pass

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

        # Get data for the duration of the backtest
        self.data_manager.update_data(limit=duration+offset)
        original_data = self.data_manager.data.copy()

        if self.data_manager.parent_interval_supported:
            original_data_parent = self.data_manager.data_parent.copy()
        
        total_periods = len(original_data) - offset

        if total_periods < 1:
            self.logger.error("Not enough data to perform backtest")
            return

        for i in range(total_periods):
            # Use data up to the current index
            current_time = original_data.index[i+offset]
            self.data_manager.data = original_data[:i+1+offset].copy()
            
            if self.data_manager.parent_interval_supported:
                # Only include parent data up to the current timestamp
                self.data_manager.data_parent = original_data_parent[original_data_parent.index <= current_time].copy()
                self.data_manager._synchronize_data()

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
                last_index = self.data_manager.data.index[-1]
                if pd.notna(self.data_manager.data.at[last_index, 'entry_data']):
                    original_data.at[last_index, 'entry_data'] = self.data_manager.data.at[last_index, 'entry_data']
                if pd.notna(self.data_manager.data.at[last_index, 'exit_data']):
                    original_data.at[last_index, 'exit_data'] = self.data_manager.data.at[last_index, 'exit_data']
                if pd.notna(self.data_manager.data.at[last_index, 'partial_close_data']):
                    original_data.at[last_index, 'partial_close_data'] = self.data_manager.data.at[last_index, 'partial_close_data']

            except Exception as e:
                self.logger.error(f"Error during backtest execution: {str(e)}")
                break

        self.logger.info("Backtest completed, Graphing results")
        summary = self.log_backtest_results()
        print(summary)
        draw_graph(self.data_manager.data, limit=duration, summary=summary)
        self.logger.info("Results graphed")
        return summary
    
    # Log backtest results
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
        summary['total_profit_loss'] = self.performance_metrics.get('total_profit_loss', 0)
        summary['total_profit_loss_percentage'] = self.performance_metrics.get('total_profit_loss_percentage', 0)

        self.logger.info(results)
        return summary

    # Update strategy parameters dynamically
    def update_parameters(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                self.logger.info(f"Updated {key} to {value}")
            else:
                self.logger.warning(f"Attribute {key} not found in strategy")

    # Print progress bar
    def print_progress_bar(self, current, total):
        percent = f"{100 * (current / float(total)):.1f}"
        filled_length = int(30 * current // total)
        bar = '=' * filled_length + '-' * (30 - filled_length)
        print(f'\rProgress: [{bar}] {percent}%', end='')
        
        if current == total: 
            print()
