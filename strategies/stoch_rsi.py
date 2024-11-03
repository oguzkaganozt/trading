from modules.strategy import Strategy
import pandas as pd
import pandas_ta as ta

class STOCH_RSI(Strategy):
    def get_indicators(self):
        if len(self.data_manager.data) < 35:
            return None, None, None, None
        
        self.parent_interval_supported = False
        ema = self.data_manager.data.ta.ema(close=self.data_manager.data['close'], length=21, append=True, suffix='EMA')
        stoch_rsi = self.data_manager.data.ta.stochrsi(close=self.data_manager.data['close'], append=True)
        stoch_rsi_parent = self.data_manager.data_parent.ta.stochrsi(close=self.data_manager.data_parent['close'], append=True)

        # self.logger.info(stoch_rsi)
        # self.logger.info(stoch_rsi_parent)
        # exit()
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

        return stoch_rsi, stoch_rsi_parent

    def check_entry(self):
        stoch_rsi, stoch_rsi_parent = self.get_indicators()
        if stoch_rsi is None or stoch_rsi_parent is None:
            return False

        stoch_rsi_current = stoch_rsi.iloc[-2]
        stoch_rsi_prev = stoch_rsi.iloc[-3]

        if stoch_rsi_prev['STOCHRSIk_14_14_3_3'] <= stoch_rsi_prev['STOCHRSId_14_14_3_3'] and stoch_rsi_current['STOCHRSIk_14_14_3_3'] > stoch_rsi_current['STOCHRSId_14_14_3_3']:
            self.logger.debug("STOCH-RSI crossed above SMA. Entering Long")
            return "long"
        elif stoch_rsi_prev['STOCHRSIk_14_14_3_3'] >= stoch_rsi_prev['STOCHRSId_14_14_3_3'] and stoch_rsi_current['STOCHRSIk_14_14_3_3'] < stoch_rsi_current['STOCHRSId_14_14_3_3']:
            self.logger.debug("STOCH-RSI crossed below SMA. Entering Short")
            return "short"
        return False

    def check_exit(self):
        stoch_rsi, stoch_rsi_parent = self.get_indicators()
        if stoch_rsi is None or stoch_rsi_parent is None:
            return False
        
        stoch_rsi_prev = stoch_rsi.iloc[-2]
        stoch_rsi_current = stoch_rsi.iloc[-3]

        # Check if MACD crosses below its Signal line
        if stoch_rsi_prev['STOCHRSIk_14_14_3_3'] > stoch_rsi_prev['STOCHRSId_14_14_3_3'] and stoch_rsi_current['STOCHRSIk_14_14_3_3'] <= stoch_rsi_current['STOCHRSId_14_14_3_3']:
            self.logger.debug("STOCH-RSI crossed below SMA. Exiting Long")
            return True
        return False
    
    def check_partial_close(self):
        return False
