from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class RSI_SMA(Strategy):
    parent_interval_supported = False
    
    def get_indicators(self):
        if len(self.data) < 35:
            return None, None
        
        rsi = self.data.ta.rsi(close=self.data['close'], length=14, append=True)
        sma = self.data.ta.sma(close=rsi['RSI_14'], length=14, append=True, suffix='RSI')
        return rsi, sma

    def check_entry(self):
        rsi, sma = self.get_indicators()
        if rsi is None or sma is None:
            return False

        # Get current and previous values for RSI and SMA
        rsi_current = float(rsi.iloc[-1])
        rsi_prev = float(rsi.iloc[-2])
        sma_current = float(sma.iloc[-1])
        sma_prev = float(sma.iloc[-2])
  
        # Check if MFI crosses above its SMA
        if rsi_prev <= sma_prev and rsi_current > sma_current:
            self.logger.debug("RSI crossed above SMA. Entering Long")
            return "long"
        return False

    def check_exit(self):
        rsi, sma = self.get_indicators()
        if rsi is None or sma is None:
            return False

        # Get current and previous values for MFI and MFI SMA
        rsi_current = float(rsi.iloc[-1])
        rsi_prev = float(rsi.iloc[-2])
        sma_current = float(sma.iloc[-1])
        sma_prev = float(sma.iloc[-2])

        # Check if RSI crosses below its SMA
        if rsi_prev >= sma_prev and rsi_current < sma_current:
            self.logger.debug("RSI crossed below SMA. Exiting Long")
            return True
        return False
    
    def check_partial_close(self):
        return False
