from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class MFI_SMA(Strategy):
    def get_indicators(self):
        if len(self.data) < 35:  # We need at least 35 data points for MFI(14) and its SMA(14)
            return None, None
        mfi = self.data.ta.mfi(high=self.data['high'], low=self.data['low'], close=self.data['close'], volume=self.data['volume'], length=7, append=True)
        mfi_sma = self.data.ta.sma(close=self.data['MFI_7'], length=14, append=True, suffix='MFI')
        ema = self.data.ta.ema(close=self.data['close'], length=100, append=True, suffix='EMA')
        return mfi, mfi_sma, ema

    def check_entry(self):
        mfi, mfi_sma, ema = self.get_indicators()
        if mfi is None or mfi_sma is None or ema is None:
            return False

        # Get current and previous values for MFI and MFI SMA
        mfi_current = float(mfi.iloc[-1])
        mfi_prev = float(mfi.iloc[-2])
        mfi_sma_current = float(mfi_sma.iloc[-1])
        mfi_sma_prev = float(mfi_sma.iloc[-2])
        ema_current = float(ema.iloc[-1])
        close_current = float(self.data.iloc[-1]['close'])

        # Check if MFI crosses above its SMA
        if mfi_prev <= mfi_sma_prev and mfi_current > mfi_sma_current and close_current > ema_current:
            self.logger.debug("MFI crossed above SMA. Entering Long")
            return "long"
        return False

    def check_exit(self):
        mfi, mfi_sma, ema = self.get_indicators()
        if mfi is None or mfi_sma is None or ema is None:
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
