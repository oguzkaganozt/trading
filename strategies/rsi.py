from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class RSI(Strategy):    
    def get_indicators(self):
        if len(self.data_manager.data) < 35:
            return None, None
        
        ema = self.data_manager.data.ta.ema(close=self.data_manager.data['close'], length=21, append=True, suffix='EMA')
        rsi = self.data_manager.data.ta.rsi(close=self.data_manager.data['close'], length=7, append=True)
        rsi_sma = self.data_manager.data.ta.sma(close=self.data_manager.data['RSI_7'], length=14, append=True, suffix='RSI')
        return rsi, rsi_sma

    def check_entry(self):
        rsi, rsi_sma = self.get_indicators()
        if rsi is None or rsi_sma is None:
            return False

        # Get current and previous values for RSI and RSI SMA
        rsi_current = float(rsi.iloc[-2])
        rsi_prev = float(rsi.iloc[-3])
        rsi_sma_current = float(rsi_sma.iloc[-2])
        rsi_sma_prev = float(rsi_sma.iloc[-3])
  
        # Check if RSI crosses above its SMA
        if rsi_prev <= rsi_sma_prev and rsi_current > rsi_sma_current:
            self.logger.info("--------------------------------")
            self.logger.info(f"Symbol: {self.symbol} - RSI crossed above SMA. Entering Long")
            self.logger.info(f"RSI: {rsi_current}, RSI SMA: {rsi_sma_current}")
            self.logger.info(f"RSI PREV: {rsi_prev}, RSI SMA PREV: {rsi_sma_prev}")
            return "long"
        elif rsi_prev >= rsi_sma_prev and rsi_current < rsi_sma_current:
            self.logger.info("--------------------------------")
            self.logger.info(f"Symbol: {self.symbol} - RSI crossed below SMA. Entering Short")
            self.logger.info(f"RSI: {rsi_current}, RSI SMA: {rsi_sma_current}")
            self.logger.info(f"RSI PREV: {rsi_prev}, RSI SMA PREV: {rsi_sma_prev}")
            return "short"
        return False

    def check_exit(self):
        rsi, rsi_sma = self.get_indicators()
        if rsi is None or rsi_sma is None:
            return False

        # Get current and previous values for RSI and RSI SMA
        rsi_current = float(rsi.iloc[-2])
        rsi_prev = float(rsi.iloc[-3])
        rsi_sma_current = float(rsi_sma.iloc[-2])
        rsi_sma_prev = float(rsi_sma.iloc[-3])

        # Check if RSI crosses below its SMA
        if rsi_prev >= rsi_sma_prev and rsi_current < rsi_sma_current:
            self.logger.info("--------------------------------")
            self.logger.info("Symbol: " + self.symbol)
            self.logger.info("Interval: " + self.interval)
            self.logger.info("RSI crossed below SMA. Exiting Long")
            self.logger.info(f"RSI: {rsi_current}, RSI SMA: {rsi_sma_current}")
            self.logger.info(f"RSI PREV: {rsi_prev}, RSI SMA PREV: {rsi_sma_prev}")
            return True
        return False
    
    def check_partial_close(self):
        return False
