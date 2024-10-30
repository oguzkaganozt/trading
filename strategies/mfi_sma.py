from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class MFI_SMA(Strategy):    
    def get_indicators(self):
        if len(self.data_manager.data) < 35:
            return None, None
        
        mfi = self.data_manager.data.ta.mfi(high=self.data_manager.data['high'], low=self.data_manager.data['low'], close=self.data_manager.data['close'], volume=self.data_manager.data['volume'], length=7, append=True)
        mfi_sma = self.data_manager.data.ta.sma(close=self.data_manager.data['MFI_7'], length=14, append=True, suffix='MFI')
        return mfi, mfi_sma

    def check_entry(self):
        mfi, mfi_sma = self.get_indicators()
        if mfi is None or mfi_sma is None:
            return False

        # Get current and previous values for MFI and MFI SMA
        mfi_current = float(mfi.iloc[-1])
        mfi_prev = float(mfi.iloc[-2])
        mfi_sma_current = float(mfi_sma.iloc[-1])
        mfi_sma_prev = float(mfi_sma.iloc[-2])
  
        # Check if MFI crosses above its SMA
        if mfi_prev <= mfi_sma_prev and mfi_current > mfi_sma_current:
            self.logger.debug("MFI crossed above SMA. Entering Long")
            return "long"
        return False

    def check_exit(self):
        mfi, mfi_sma = self.get_indicators()
        if mfi is None or mfi_sma is None:
            return False

        # Get current and previous values for MFI and MFI SMA
        mfi_current = float(mfi.iloc[-1])
        mfi_prev = float(mfi.iloc[-2])
        mfi_sma_current = float(mfi_sma.iloc[-1])
        mfi_sma_prev = float(mfi_sma.iloc[-2])

        # Check if MFI crosses below its SMA
        if mfi_prev >= mfi_sma_prev and mfi_current < mfi_sma_current:
            self.logger.debug("MFI crossed below SMA. Exiting Long")
            return True
        return False
    
    def check_partial_close(self):
        return False
