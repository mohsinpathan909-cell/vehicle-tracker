import pandas as pd

from broker.historical_market_data import HistoricalMarketData
from broker.paper_broker import PaperOrderExecutor


def make_market_data(price=100.0):
    df = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=3), "close": [price] * 3})
    return HistoricalMarketData(df, "TEST")


def test_buy_reduces_cash_and_opens_position():
    md = make_market_data(price=100)
    ex = PaperOrderExecutor(md, "TEST", starting_cash=100000, slippage_pct=0)
    result = ex.place_order("TEST", "BUY", 10)
    assert result["status"] == "FILLED"
    assert ex.get_cash() == 100000 - 1000
    assert ex.get_positions()["TEST"]["quantity"] == 10


def test_sell_without_position_is_rejected():
    md = make_market_data()
    ex = PaperOrderExecutor(md, "TEST", starting_cash=100000)
    result = ex.place_order("TEST", "SELL", 10)
    assert result["status"] == "REJECTED"


def test_buy_beyond_cash_is_rejected():
    md = make_market_data(price=100)
    ex = PaperOrderExecutor(md, "TEST", starting_cash=500, slippage_pct=0)
    result = ex.place_order("TEST", "BUY", 10)
    assert result["status"] == "REJECTED"


def test_full_round_trip_updates_cash_correctly():
    md = make_market_data(price=100)
    ex = PaperOrderExecutor(md, "TEST", starting_cash=100000, slippage_pct=0)
    ex.place_order("TEST", "BUY", 10)
    ex.place_order("TEST", "SELL", 10)
    assert ex.get_cash() == 100000
    assert "TEST" not in ex.get_positions()
