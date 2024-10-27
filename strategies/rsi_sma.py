from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class RSI_SMA(Strategy):
    def check_entry(self):
        if len(self.data) < 28:  # We need at least 28 data points for RSI(14) and its SMA(14)
            return False

        self.rsi = self.data.ta.rsi(length=14, append=True)
        self.rsi_sma = self.data.ta.sma(close=self.data['RSI_14'], length=14, append=True, suffix='RSI')

        # Check for NaN or None values
        if self.rsi.iloc[-1] is None or pd.isna(self.rsi.iloc[-1]) or \
           self.rsi.iloc[-2] is None or pd.isna(self.rsi.iloc[-2]) or \
           self.rsi_sma.iloc[-1] is None or pd.isna(self.rsi_sma.iloc[-1]) or \
           self.rsi_sma.iloc[-2] is None or pd.isna(self.rsi_sma.iloc[-2]):
            return False
        
        # Get current and previous values for RSI and RSI SMA
        rsi_current = float(self.rsi.iloc[-1])
        rsi_prev = float(self.rsi.iloc[-2])
        rsi_sma_current = float(self.rsi_sma.iloc[-1])
        rsi_sma_prev = float(self.rsi_sma.iloc[-2])
        
        # Check if RSI crosses above its SMA
        if rsi_prev <= rsi_sma_prev and rsi_current > rsi_sma_current:
            self.logger.debug("RSI crossed above SMA. Entering Long")
            return "long"
        return False

    def check_exit(self):
        if len(self.data) < 28:  # We need at least 28 data points for RSI(14) and its SMA(14)
            return False

        self.rsi = self.data.ta.rsi(length=14, append=True)
        self.rsi_sma = self.data.ta.sma(close=self.data['RSI_14'], length=14, append=True, suffix='RSI')
        
        # Check for NaN or None values
        if self.rsi.iloc[-1] is None or pd.isna(self.rsi.iloc[-1]) or \
           self.rsi.iloc[-2] is None or pd.isna(self.rsi.iloc[-2]) or \
           self.rsi_sma.iloc[-1] is None or pd.isna(self.rsi_sma.iloc[-1]) or \
           self.rsi_sma.iloc[-2] is None or pd.isna(self.rsi_sma.iloc[-2]):
            return False
        
        # Get current and previous values for RSI and RSI SMA
        rsi_current = float(self.rsi.iloc[-1])
        rsi_prev = float(self.rsi.iloc[-2])
        rsi_sma_current = float(self.rsi_sma.iloc[-1])
        rsi_sma_prev = float(self.rsi_sma.iloc[-2])

        # Check if RSI crosses below its SMA
        if rsi_prev >= rsi_sma_prev and rsi_current < rsi_sma_current:
            self.logger.debug("RSI crossed below SMA. Exiting Long")
            return True
        return False
    
    def check_partial_close(self):
        return False
