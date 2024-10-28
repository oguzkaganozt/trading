from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class MACD_MFI(Strategy):
    parent_interval_supported = True

    def calculate_mfi(self, period=14):
        # Calculate typical price
        typical_price = (self.data['high'] + self.data['low'] + self.data['close']) / 3
        
        # Calculate raw money flow
        raw_money_flow = typical_price * self.data['volume']
        
        # Calculate positive and negative money flow
        positive_flow = pd.Series(0.0, index=raw_money_flow.index)
        negative_flow = pd.Series(0.0, index=raw_money_flow.index)
        
        # Calculate price changes
        price_diff = typical_price.diff()
        
        # Assign flows based on price movement
        positive_flow[price_diff > 0] = raw_money_flow[price_diff > 0]
        negative_flow[price_diff < 0] = raw_money_flow[price_diff < 0]
        
        # Calculate 14-period positive and negative flow sums
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()
        
        # Calculate money flow ratio
        money_flow_ratio = positive_mf / negative_mf
        
        # Calculate MFI
        mfi = 100 - (100 / (1 + money_flow_ratio))
        
        return mfi
    
    def get_indicators(self):
        # Check if we have enough data
        if len(self.data) < 35:  # We need at least 35 data points for MFI(14) and its SMA(14)
            return None, None, None
        
        # Get indicators
        macd = self.data_parent.ta.macd(close=self.data_parent['close'], append=True)
        mfi = self.calculate_mfi(period=7)
        mfi_sma = self.data.ta.sma(close=mfi, length=7, append=True, suffix='MFI')
        self.data['MFI'] = mfi
        self.data['MFI_SMA'] = mfi_sma

        return macd, mfi, mfi_sma

    def check_entry(self):
        macd, mfi, mfi_sma = self.get_indicators()
        if mfi is None or mfi_sma is None or macd is None:
            self.logger.info("No indicators found")
            return False

        # Get current and previous values for MFI and MFI SMA
        mfi_current = float(mfi.iloc[-1])
        mfi_prev = float(mfi.iloc[-2])
        mfi_sma_current = float(mfi_sma.iloc[-1])
        mfi_sma_prev = float(mfi_sma.iloc[-2])

        self.logger.info(f"MACD: {macd}")

        # Check if MACD crosses above its signal
        if macd['MACD_12_26_9'].iloc[-1] > macd['MACDs_12_26_9'].iloc[-1]:
            # Check if MFI crosses above its SMA
            if mfi_prev <= mfi_sma_prev and mfi_current > mfi_sma_current*1.2:
                self.logger.info("MFI crossed above SMA. Entering Long")
                return "long"
        return False

    def check_exit(self):
        macd, mfi, mfi_sma = self.get_indicators()
        if mfi is None or mfi_sma is None or macd is None:
            return False

        # Get current and previous values for MFI and MFI SMA
        mfi_current = float(mfi.iloc[-1])
        mfi_prev = float(mfi.iloc[-2])
        mfi_sma_current = float(mfi_sma.iloc[-1])
        mfi_sma_prev = float(mfi_sma.iloc[-2])

        # Check if MFI crosses below its SMA
        if mfi_current < mfi_prev:
            self.logger.info("MFI crossed below SMA. Exiting Long")
            return True
        return False
    
    def check_partial_close(self):
        return False
