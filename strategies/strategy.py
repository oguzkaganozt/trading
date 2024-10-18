from abc import ABC, abstractmethod
import logging
from polygon_api import get_ohlc, get_rsi, get_macd, get_ema, get_sma, get_bb, get_news, get_symbol_details
import datetime

# A base class for all strategies
class Strategy(ABC):
    def __init__(self, name, symbol, balance, timeframe, multiplier, stop_loss_percentage, risk_percentage, take_profit_percentage):
        self.name = name
        self.symbol = symbol
        self.timeframe = timeframe
        self.multiplier = multiplier
        self.active = True
        self.simulation = True
        self.position = None
        self.balance = balance
        self.stop_loss_percentage = stop_loss_percentage
        self.risk_percentage = risk_percentage
        self.take_profit_percentage = take_profit_percentage
        self.entry_price = 0
        self.stop_loss_price = 0
        self.take_profit_price = 0
        self.position_size = 0
        self.rsi = {}
        self.macd = {}
        self.ema = {}
        self.sma = {}
        self.bb = {}
        self.ohlc = {}
        self.news = {}
        self.trade_history = []
        self.performance_metrics = {}

        try:
            # Check if symbol is valid
            if get_symbol_details(self.symbol) is None:
                raise ValueError(f"Symbol {self.symbol} not found")
        except Exception as e:
            print(f"Error initializing strategy: {str(e)}")
            exit()

        # Set up logger
        self.logger = logging.getLogger(f"{self.name}_{self.symbol}")
        self.logger.setLevel(logging.INFO)
        
        # Create a file handler
        fh = logging.FileHandler(f"{self.name}_{self.symbol}.log")
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

    # Run strategy
    def run(self, backtest=False):
        if not self.active:
            self.logger.warning("Strategy is not active. Skipping run.")
            return

        try:
            if not backtest:
                self.update_indicators()

            if self.position is None:
                entry_signal = self.check_entry()
                if entry_signal == "long":
                    self.long()
                elif entry_signal == "short":
                    self.short()
            else:
                if self.check_exit() == "close":
                    self.close_position()
                self.check_trailing_stop_loss()
                self.check_trailing_take_profit()
        except Exception as e:
            self.logger.error(f"Error during strategy execution: {str(e)}")
            self.active = False

    # Check entry
    @abstractmethod
    def check_entry(self):
        pass

    # Check exit
    @abstractmethod
    def check_exit(self):
        pass
    
    # Check trailing stop loss
    def check_trailing_stop_loss(self, close_percentage=50):
        if self.position == "long":
            new_stop_loss = self.ohlc['c'][-1] - (self.entry_price - self.stop_loss_price)
            if new_stop_loss > self.stop_loss_price:
                self.stop_loss_price = new_stop_loss
                self.logger.info(f"Updated trailing stop loss: {self.stop_loss_price}")
            elif self.ohlc['c'][-1] <= self.stop_loss_price:
                self.logger.info(f"Trailing stop loss triggered at {self.ohlc['c'][-1]}")
                self.partial_close(close_percentage, "Trailing stop loss")

        elif self.position == "short":
            new_stop_loss = self.ohlc['c'][-1] + (self.stop_loss_price - self.entry_price)
            if new_stop_loss < self.stop_loss_price:
                self.stop_loss_price = new_stop_loss
                self.logger.info(f"Updated trailing stop loss: {self.stop_loss_price}")
            elif self.ohlc['c'][-1] >= self.stop_loss_price:
                self.logger.info(f"Trailing stop loss triggered at {self.ohlc['c'][-1]}")
                self.partial_close(close_percentage, "Trailing stop loss")
        else:
            self.logger.warning("Position type not set. Cannot check trailing stop loss.")

    # Check trailing take profit
    def check_trailing_take_profit(self, close_percentage=50):
        if self.position == "long":
            if self.ohlc['c'][-1] > self.take_profit_price:
                self.take_profit_price = self.ohlc['c'][-1]
                self.logger.info(f"Updated trailing take profit: {self.take_profit_price}")
            elif self.ohlc['c'][-1] < self.take_profit_price:
                self.logger.info(f"Trailing take profit triggered at {self.ohlc['c'][-1]}")
                self.partial_close(close_percentage, "Trailing take profit")
        elif self.position == "short":
            if self.ohlc['c'][-1] < self.take_profit_price:
                self.take_profit_price = self.ohlc['c'][-1]
                self.logger.info(f"Updated trailing take profit: {self.take_profit_price}")
            elif self.ohlc['c'][-1] > self.take_profit_price:
                self.logger.info(f"Trailing take profit triggered at {self.ohlc['c'][-1]}")
                self.partial_close(close_percentage, "Trailing take profit")
        else:
            self.logger.warning("Position type not set. Cannot check trailing take profit.")

    # Adjust entry price
    def adjust_entry_price(self):
        if self.position is None or self.position_size == 0:
            return

        # Calculate the average entry price based on remaining position and realized profit/loss
        total_cost = self.entry_price * self.position_size
        realized_pnl = sum(trade['profit_loss'] for trade in self.trade_history if trade['action'].startswith('partial close'))
        
        # Adjust the total cost by subtracting the realized profit/loss
        adjusted_total_cost = total_cost - realized_pnl
        
        # Calculate the new entry price
        self.entry_price = adjusted_total_cost / self.position_size
        
        self.logger.info(f"Adjusted entry price to: ${self.entry_price:.2f}")

    # Update indicators
    def update_indicators(self):
        try:
            self.rsi = get_rsi(self.symbol, self.timeframe, self.multiplier)
            self.macd = get_macd(self.symbol, self.timeframe, self.multiplier)
            self.ema = get_ema(self.symbol, self.timeframe, self.multiplier)
            self.sma = get_sma(self.symbol, self.timeframe, self.multiplier)
            self.ohlc = get_ohlc(self.symbol, self.timeframe, self.multiplier)
            self.bb = get_bb(self.symbol, self.timeframe, self.multiplier)
            self.news = get_news(self.symbol, self.timeframe, self.multiplier)
        except Exception as e:
            self.logger.error(f"Error updating indicators: {str(e)}")
            raise

    # Log trade
    def log_trade(self, action, price, size, profit_loss=None, result=None):
        action_str = action.replace('_', ' ').title()
        self.logger.info(f"Trade: {action_str} {size:.4f} units of {self.symbol} at ${price:.2f}")
        trade_info = {
            'action': action,
            'price': price,
            'size': size,
            'date': datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        }
        if profit_loss is not None:
            trade_info['profit_loss'] = profit_loss
            trade_info['result'] = result
            result_str = "Profit" if profit_loss > 0 else "Loss"
            self.logger.info(f"Trade Result: {result_str} of ${abs(profit_loss):.2f}" + (f" - Outcome: {result.title()}" if result else ""))
        
        self.trade_history.append(trade_info)
        self.update_performance_metrics()

    # Calculate position size based on risk percentage
    def calculate_position_size(self):
        try:
            if not self.ohlc:
                raise ValueError("OHLC data not available. Cannot calculate position size.")

            current_price = self.ohlc['c'][-1]
            stop_loss_amount = current_price * (self.stop_loss_percentage / 100)
            
            risk_amount = self.balance * (self.risk_percentage / 100)
            if stop_loss_amount == 0:
                self.logger.warning("Stop loss amount is zero. Cannot calculate position size.")
                self.position_size = 0
            else:
                self.position_size = risk_amount / stop_loss_amount
            self.entry_price = current_price

            if self.position == "long":
                self.stop_loss_price = current_price - stop_loss_amount
                self.take_profit_price = current_price + (current_price * (self.take_profit_percentage / 100))
            elif self.position == "short":
                self.stop_loss_price = current_price + stop_loss_amount
                self.take_profit_price = current_price - (current_price * (self.take_profit_percentage / 100))
            else:
                raise ValueError("Position type not set. Cannot calculate stop loss and take profit prices.")

            self.logger.info(f"Position Details:")
            self.logger.info(f"  - Size: {self.position_size:.4f} units")
            self.logger.info(f"  - Entry Price: ${self.entry_price:.2f}")
            self.logger.info(f"  - Stop Loss: ${self.stop_loss_price:.2f}")
            self.logger.info(f"  - Take Profit: ${self.take_profit_price:.2f}")
        except Exception as e:
            self.logger.error(f"Error calculating position size: {str(e)}")
            raise

    # Long position
    def long(self):
        self.position = "long"
        self.calculate_position_size()
        self.execute_trade("long", self.position_size)

    # Short position
    def short(self):
        self.position = "short"
        self.calculate_position_size()
        self.execute_trade("short", self.position_size)

    # Close position
    def close_position(self):
        if self.position is not None:
            close_price = self.ohlc['c'][-1]
            self.execute_trade("close", self.position_size)
            
            # Calculate profit/loss for the final close
            if self.position == "long":
                final_profit_loss = (close_price - self.entry_price) * self.position_size
            else:  # short position
                final_profit_loss = (self.entry_price - close_price) * self.position_size
            
            # Calculate total profit/loss including partial closes
            total_profit_loss = final_profit_loss
            for trade in self.trade_history:
                if trade['action'].startswith('partial close'):
                    total_profit_loss += trade['profit_loss']
            
            # Determine if it's a win or loss based on total profit/loss
            trade_result = "win" if total_profit_loss > 0 else "loss"
            
            self.log_trade("close", close_price, self.position_size, total_profit_loss, trade_result)
            self.position = None
            self.position_size = 0
            self.balance += total_profit_loss  # Update balance
        else:
            self.logger.warning("Attempted to close position, but no position is open")
    
    # Partial close position
    def partial_close(self, percentage, reason):
        if self.position is None:
            self.logger.warning(f"Cannot partially close: no position open")
            return

        close_price = self.ohlc['c'][-1]
        close_size = self.position_size * (percentage / 100)
        remaining_size = self.position_size - close_size

        # Calculate profit/loss for this partial close
        if self.position == "long":
            profit_loss = (close_price - self.entry_price) * close_size
        else:  # short position
            profit_loss = (self.entry_price - close_price) * close_size

        self.logger.info(f"{reason} - Partially closing {percentage}% of position")
        self.log_trade(f"partial close ({reason})", close_price, close_size, profit_loss)

        # Update position size and balance
        self.position_size = remaining_size
        self.balance += profit_loss

        if remaining_size == 0:
            self.position = None
            self.logger.info("Position fully closed")
        else:
            self.logger.info(f"Remaining position size: {remaining_size}")
        
        self.execute_trade("partial close", close_size)

        # Adjust entry price after partial close
        self.adjust_entry_price()

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
    
    # Execute trade
    def execute_trade(self, action, size):
        try:
            self.logger.info(f"Executing {action} trade for {size} units of {self.symbol}")
            if not self.simulation:
                # Here you would implement the actual trade execution
                # This might involve interacting with an exchange API or broker
                pass
            if action == "close" or action == "partial close":
                self.log_trade(action, self.ohlc['c'][-1], size)
            else:
                self.log_trade(action, self.entry_price, size)
        except Exception as e:
            self.logger.error(f"Error executing trade: {str(e)}")
            raise

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
    
    # Put simulation
    def put_simulation(self):
        self.simulation = True
        self.active = True
    
    # Put inactive
    def put_inactive(self):
        self.simulation = False
        self.active = False

    # Backtest
    def backtest(self):
        # Get historical data in array
        # Run strategy as long as we have historical data
        # while self.ohlc:
        #     self.run(backtest=True)
        # Show performance metrics
        self.logger.info(f"Performance metrics: {self.performance_metrics}")