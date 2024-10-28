from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class MFI_SMA_MACD(Strategy):
    parent_interval_supported = False
    
    def get_indicators(self):
        if len(self.data) < 35:
            return None, None
        
        mfi = self.data.ta.mfi(high=self.data['high'], low=self.data['low'], close=self.data['close'], volume=self.data['volume'], length=7, append=True)
        mfi_sma = self.data.ta.sma(close=self.data['MFI_7'], length=14, append=True, suffix='MFI')
        macd = self.data.ta.macd(close=self.data['close'], append=True)
        return mfi, mfi_sma, macd

    def check_entry(self):
        mfi, mfi_sma, macd = self.get_indicators()
        if mfi is None or mfi_sma is None or macd is None:
            return False

        # Get current and previous values for MFI and MFI SMA
        mfi_current = float(mfi.iloc[-1])
        mfi_prev = float(mfi.iloc[-2])
        mfi_sma_current = float(mfi_sma.iloc[-1])
        mfi_sma_prev = float(mfi_sma.iloc[-2])
        # macd_current = macd.iloc[-1]

        self.logger.info(f"{self.data['MACD_12_26_9'].iloc[-1]}")
        self.logger.info(f"{self.data['MACDs_12_26_9'].iloc[-1]}")

        # Check if close price near to any resistance level +- 5%
        # resistance_levels = self.data['resistance'].tolist()
        # for resistance_level in resistance_levels:
        #     if self.data['close'].iloc[-1] > resistance_level * 0.95 and self.data['close'].iloc[-1] < resistance_level * 1.05:
        #         self.logger.info(f"Close price near to resistance level: {resistance_level}")
        #         return False

        # Check if MFI crosses above its SMA
        if mfi_prev <= mfi_sma_prev and mfi_current > mfi_sma_current and self.data['MACD_12_26_9'].iloc[-1] > self.data['MACDs_12_26_9'].iloc[-1]:
            self.logger.debug("MFI crossed above SMA. Entering Long")
            return "long"
        return False

    def check_exit(self):
        mfi, mfi_sma, macd = self.get_indicators()
        if mfi is None or mfi_sma is None or macd is None:
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
