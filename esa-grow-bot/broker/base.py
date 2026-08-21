from abc import ABC, abstractmethod

import pandas as pd


class MarketData(ABC):
    """Read-only price data. Safe to use in both paper and live mode."""

    @abstractmethod
    def get_ltp(self, symbol: str) -> float:
        """Last traded price for symbol."""

    @abstractmethod
    def get_historical(self, symbol: str, interval: str, lookback_days: int) -> pd.DataFrame:
        """OHLC history with at least a 'close' column, oldest row first."""


class OrderExecutor(ABC):
    """Places orders and tracks positions/cash. The only component that can move real money."""

    @abstractmethod
    def place_order(self, symbol: str, transaction_type: str, quantity: int,
                     order_type: str = "MARKET", price: float | None = None) -> dict:
        """transaction_type is 'BUY' or 'SELL'. Returns a dict describing the fill/order."""

    @abstractmethod
    def get_positions(self) -> dict:
        """symbol -> {'quantity': int, 'avg_price': float}"""

    @abstractmethod
    def get_cash(self) -> float:
        """Available cash balance."""
