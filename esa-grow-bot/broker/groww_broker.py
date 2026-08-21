"""
Real Groww adapter, built against the documented growwapi SDK surface
(pip install growwapi). Network access to groww.in was not reachable while
writing this, so verify method/constant names against
https://groww.in/trade-api/docs/python-sdk before running live.

GrowwMarketData is read-only and safe to use even while paper trading
(it never places an order). GrowwOrderExecutor is the only class in this
project that can move real money — it is only wired up in --mode live.
"""
import pandas as pd
from growwapi import GrowwAPI

from broker.base import MarketData, OrderExecutor


def make_access_token(api_key: str, api_secret: str = "", totp: str = "") -> str:
    if totp:
        return GrowwAPI.get_access_token(api_key=api_key, totp=totp)
    if api_secret:
        return GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
    raise ValueError("Provide either GROWW_API_SECRET or a TOTP to authenticate.")


class GrowwMarketData(MarketData):
    def __init__(self, client: GrowwAPI):
        self._client = client

    def get_ltp(self, symbol: str) -> float:
        quote = self._client.get_quote(
            trading_symbol=symbol,
            exchange=GrowwAPI.EXCHANGE_NSE,
            segment=GrowwAPI.SEGMENT_CASH,
        )
        return float(quote["last_price"])

    def get_historical(self, symbol: str, interval: str, lookback_days: int) -> pd.DataFrame:
        candles = self._client.get_historical_candles(
            trading_symbol=symbol,
            exchange=GrowwAPI.EXCHANGE_NSE,
            segment=GrowwAPI.SEGMENT_CASH,
            interval=interval,
            lookback_days=lookback_days,
        )
        df = pd.DataFrame(candles)
        df = df.rename(columns={"last_price": "close"}) if "close" not in df.columns else df
        return df.sort_values("timestamp").reset_index(drop=True)


class GrowwOrderExecutor(OrderExecutor):
    """Places REAL orders on a REAL Groww account. Handle with care."""

    def __init__(self, client: GrowwAPI):
        self._client = client

    def place_order(self, symbol: str, transaction_type: str, quantity: int,
                     order_type: str = "MARKET", price: float | None = None) -> dict:
        txn = GrowwAPI.TRANSACTION_TYPE_BUY if transaction_type == "BUY" else GrowwAPI.TRANSACTION_TYPE_SELL
        otype = GrowwAPI.ORDER_TYPE_MARKET if order_type == "MARKET" else GrowwAPI.ORDER_TYPE_LIMIT
        return self._client.place_order(
            trading_symbol=symbol,
            quantity=quantity,
            validity=GrowwAPI.VALIDITY_DAY,
            exchange=GrowwAPI.EXCHANGE_NSE,
            segment=GrowwAPI.SEGMENT_CASH,
            product=GrowwAPI.PRODUCT_CNC,
            order_type=otype,
            transaction_type=txn,
            price=price or 0,
        )

    def get_positions(self) -> dict:
        positions = self._client.get_positions()
        return {
            p["trading_symbol"]: {"quantity": int(p["quantity"]), "avg_price": float(p["avg_price"])}
            for p in positions
        }

    def get_cash(self) -> float:
        margin = self._client.get_available_margin()
        return float(margin["available_cash"])
