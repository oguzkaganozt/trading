from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class MACD_DOUBLE(Strategy):
    def __init__(self, symbol, interval, parent_interval=None, balance=1000, risk_percentage=100, trailing_stop_percentage=0):
        super().__init__(symbol, interval, parent_interval, balance, risk_percentage, trailing_stop_percentage)
        self.macd_surpassed = False

    def get_indicators(self):
        if len(self.data_manager.data) < 35:
            return None, None, None, None
        
        self.parent_interval_supported = False
        ema = self.data_manager.data.ta.ema(close=self.data_manager.data['close'], length=21, append=True, suffix='EMA')
        macd = self.data_manager.data.ta.macd(close=self.data_manager.data['close'], append=True)
        
        # Calculate parent MACD
        macd_parent = self.data_manager.data_parent.ta.macd(close=self.data_manager.data_parent['close'])
        
        # # Create a new DataFrame with parent MACD data
        # parent_data = pd.DataFrame(index=self.data_manager.data_parent.index)
        # parent_data['MACD_12_26_9_Parent'] = macd_parent['MACD_12_26_9']
        # parent_data['MACDs_12_26_9_Parent'] = macd_parent['MACDs_12_26_9']
        # parent_data['MACDh_12_26_9_Parent'] = macd_parent['MACDh_12_26_9']
        
        # # Reindex parent data to match base timeframe and forward fill
        # reindexed_parent = parent_data.reindex(self.data_manager.data.index, method='ffill')
        
        # # Add parent MACD columns to base timeframe data
        # self.data_manager.data['MACD_12_26_9_Parent'] = reindexed_parent['MACD_12_26_9_Parent']
        # self.data_manager.data['MACDs_12_26_9_Parent'] = reindexed_parent['MACDs_12_26_9_Parent']
        # self.data_manager.data['MACDh_12_26_9_Parent'] = reindexed_parent['MACDh_12_26_9_Parent']

        return macd, macd_parent

    def check_entry(self):
        macd, macd_parent = self.get_indicators()
        if macd is None or macd_parent is None:
            return False

        macd_prev = macd.iloc[-2]
        macd_current = macd.iloc[-1]
        macd_parent_current = macd_parent.iloc[-1]
        macd_parent_prev = macd_parent.iloc[-2]

        if self.macd_surpassed:
            if macd_prev['MACD_12_26_9'] < macd_prev['MACDs_12_26_9'] and macd_current['MACD_12_26_9'] > macd_current['MACDs_12_26_9']:
                self.logger.debug("Entering Long")
                return "long"
        else:
            if macd_parent_prev['MACD_12_26_9'] < macd_parent_prev['MACDs_12_26_9'] and macd_parent_current['MACD_12_26_9'] > macd_parent_current['MACDs_12_26_9']:
                self.macd_surpassed = True
        return False

    def check_exit(self):
        macd, macd_parent = self.get_indicators()
        if macd is None or macd_parent is None:
            return False
        
        macd_prev = macd.iloc[-2]
        macd_current = macd.iloc[-1]

        # Check if MACD crosses below its Signal line
        if macd_prev['MACD_12_26_9'] > macd_prev['MACDs_12_26_9'] and macd_current['MACD_12_26_9'] < macd_current['MACDs_12_26_9']:
            self.logger.debug("Exiting Long")
            self.macd_surpassed = False
            return True
        return False
    
    def check_partial_close(self):
        return False
