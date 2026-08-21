"""Replays a historical OHLC DataFrame bar-by-bar for backtesting. Not for
live use — get_ltp/get_historical only ever look at data up to the current
replay position, so a strategy can't accidentally peek into the future."""
import pandas as pd

from broker.base import MarketData


class HistoricalMarketData(MarketData):
    def __init__(self, df: pd.DataFrame, symbol: str):
        required = {"timestamp", "close"}
        if not required.issubset(df.columns):
            raise ValueError(f"historical data must have columns {required}, got {list(df.columns)}")
        self._df = df.sort_values("timestamp").reset_index(drop=True)
        self._symbol = symbol
        self._cursor = 0

    def __len__(self):
        return len(self._df)

    def advance(self):
        self._cursor += 1

    def is_done(self) -> bool:
        return self._cursor >= len(self._df)

    def get_ltp(self, symbol: str) -> float:
        return float(self._df.iloc[self._cursor]["close"])

    def get_historical(self, symbol: str, interval: str, lookback_days: int) -> pd.DataFrame:
        start = max(0, self._cursor - lookback_days)
        return self._df.iloc[start:self._cursor + 1].reset_index(drop=True)
