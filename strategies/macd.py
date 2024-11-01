from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class MACD(Strategy):
    def get_indicators(self):
        if len(self.data_manager.data) < 35:
            return None, None, None, None
        
        self.parent_interval_supported = False
        ema = self.data_manager.data.ta.ema(close=self.data_manager.data['close'], length=21, append=True, suffix='EMA')
        macd = self.data_manager.data.ta.macd(close=self.data_manager.data['close'], append=True)
        macd_parent = self.data_manager.data_parent.ta.macd(close=self.data_manager.data_parent['close'], append=True)

        return macd, macd_parent

    def check_entry(self):
        macd, macd_parent = self.get_indicators()
        if macd is None or macd_parent is None:
            return False

        macd_prev = macd.iloc[-2]
        macd_current = macd.iloc[-1]
        macd_parent_current = macd_parent.iloc[-1]

        # Check if MFI crosses above its SMA
        if macd_prev['MACD_12_26_9'] < macd_prev['MACDs_12_26_9'] and macd_current['MACD_12_26_9'] > macd_current['MACDs_12_26_9'] and macd_parent_current['MACD_12_26_9'] > macd_parent_current['MACDs_12_26_9']:
            self.logger.debug("MACD crossed above SMA. Entering Long")
            return "long"
        return False

    def check_exit(self):
        macd, macd_parent = self.get_indicators()
        if macd is None or macd_parent is None:
            return False
        
        macd_prev = macd.iloc[-2]
        macd_current = macd.iloc[-1]
        macd_parent_current = macd_parent.iloc[-1]

        # Check if MFI crosses below its SMA
        if macd_parent_current['MACD_12_26_9'] < macd_parent_current['MACDs_12_26_9'] or macd_current['MACD_12_26_9'] < macd_current['MACDs_12_26_9']:
            self.logger.debug("MACD crossed below SMA. Exiting Long")
            return True
        return False
    
    def check_partial_close(self):
        return False
