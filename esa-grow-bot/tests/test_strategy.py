import pandas as pd

from strategy.sma_crossover import SmaCrossoverStrategy


def make_df(closes):
    return pd.DataFrame({"close": closes})


def test_hold_when_not_enough_history():
    strat = SmaCrossoverStrategy(2, 4)
    assert strat.generate_signal(make_df([1, 2, 3])) == "HOLD"


def test_buy_on_upward_crossover():
    strat = SmaCrossoverStrategy(2, 4)
    # short SMA (90->115) crosses above long SMA (95->105) on the last bar
    closes = [100, 100, 100, 90, 90, 140]
    assert strat.generate_signal(make_df(closes)) == "BUY"


def test_sell_on_downward_crossover():
    strat = SmaCrossoverStrategy(2, 4)
    # short SMA (110->85) crosses below long SMA (105->95) on the last bar
    closes = [100, 100, 100, 110, 110, 60]
    assert strat.generate_signal(make_df(closes)) == "SELL"


def test_hold_when_no_crossover():
    strat = SmaCrossoverStrategy(2, 4)
    closes = [10, 10, 10, 10, 10, 10]
    assert strat.generate_signal(make_df(closes)) == "HOLD"


def test_invalid_windows_raise():
    try:
        SmaCrossoverStrategy(5, 5)
        assert False, "expected ValueError"
    except ValueError:
        pass
