from strategy import Strategy

class DBV(Strategy):
    def check_entry(self):
        if self.rsi['value'][-1] < 30:
            return "long"
        elif self.rsi['value'][-1] > 70:
            return "short"
        return None

    def check_exit(self):
        if self.position == "long" and self.rsi['value'][-1] > 70:
            return "close"
        elif self.position == "short" and self.rsi['value'][-1] < 30:
            return "close"
        return None