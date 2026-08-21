"""Simple, well-known SMA crossover strategy. This is a starting point, not a
proven money-maker — no strategy here or elsewhere guarantees profit.

Signal: BUY when the short SMA crosses above the long SMA, SELL when it
crosses below, HOLD otherwise. Needs at least long_window+1 closes.
"""
import pandas as pd


class SmaCrossoverStrategy:
    def __init__(self, short_window: int, long_window: int):
        if short_window >= long_window:
            raise ValueError("short_window must be less than long_window")
        self.short_window = short_window
        self.long_window = long_window

    def generate_signal(self, df: pd.DataFrame) -> str:
        if len(df) < self.long_window + 1:
            return "HOLD"

        closes = df["close"]
        short_sma = closes.rolling(self.short_window).mean()
        long_sma = closes.rolling(self.long_window).mean()

        prev_diff = short_sma.iloc[-2] - long_sma.iloc[-2]
        curr_diff = short_sma.iloc[-1] - long_sma.iloc[-1]

        if prev_diff <= 0 < curr_diff:
            return "BUY"
        if prev_diff >= 0 > curr_diff:
            return "SELL"
        return "HOLD"
