from strategy import Strategy

class DBV(Strategy):
    def check_entry(self):
        if len(self.data) < 28:  # We need at least 28 data points for RSI(14) and its SMA(14)
            return None

        self.rsi = self.data.ta.rsi(length=14, append=True)
        self.rsi_sma = self.data.ta.sma(close=self.data['RSI_14'], length=14, append=True, suffix='RSI')
        
        # Get current and previous values for RSI and RSI SMA
        rsi_current = self.rsi.iloc[-1]
        rsi_prev = self.rsi.iloc[-2]
        rsi_sma_current = self.rsi_sma.iloc[-1]
        rsi_sma_prev = self.rsi_sma.iloc[-2]

        self.logger.info(f"RSI: {rsi_current}, RSI SMA: {rsi_sma_current}")
        
        # Check if RSI crosses above its SMA
        if rsi_prev <= rsi_sma_prev and rsi_current > rsi_sma_current:
            self.logger.info("RSI crossed above SMA. Entering Long")
            return "long"
        return None

    def check_exit(self):
        if len(self.data) < 28:  # We need at least 28 data points for RSI(14) and its SMA(14)
            return None

        self.rsi = self.data.ta.rsi(length=14, append=True)
        self.rsi_sma = self.data.ta.sma(close=self.data['RSI_14'], length=14, append=True, suffix='RSI')
        
        # Get current and previous values for RSI and RSI SMA
        rsi_current = self.rsi.iloc[-1]
        rsi_prev = self.rsi.iloc[-2]
        rsi_sma_current = self.rsi_sma.iloc[-1]
        rsi_sma_prev = self.rsi_sma.iloc[-2]
    
        self.logger.info(f"RSI: {rsi_current}, RSI SMA: {rsi_sma_current}")
        
        # Check if RSI crosses below its SMA
        if rsi_prev >= rsi_sma_prev and rsi_current < rsi_sma_current:
            self.logger.info("RSI crossed below SMA. Exiting Long")
            return True
        return False
