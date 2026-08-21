import pandas as pd

from broker.historical_market_data import HistoricalMarketData
from broker.paper_broker import PaperOrderExecutor
from risk.risk_manager import RiskManager
from strategy.sma_crossover import SmaCrossoverStrategy


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def run_backtest(df: pd.DataFrame, symbol: str, strategy: SmaCrossoverStrategy,
                  risk_manager: RiskManager, starting_cash: float) -> dict:
    market_data = HistoricalMarketData(df, symbol)
    executor = PaperOrderExecutor(market_data, symbol, starting_cash)

    equity_curve = []
    market_data._cursor = strategy.long_window  # need enough history for the first signal

    while not market_data.is_done():
        history = market_data.get_historical(symbol, interval="1d", lookback_days=strategy.long_window + 5)
        signal = strategy.generate_signal(history)
        positions = executor.get_positions()
        open_count = sum(1 for p in positions.values() if p["quantity"] > 0)

        if signal == "BUY" and risk_manager.can_open_new_position(open_count):
            ltp = market_data.get_ltp(symbol)
            qty = risk_manager.size_position(ltp)
            if qty > 0:
                executor.place_order(symbol, "BUY", qty)

        elif signal == "SELL":
            pos = positions.get(symbol)
            if pos and pos["quantity"] > 0:
                ltp = market_data.get_ltp(symbol)
                pnl = (ltp - pos["avg_price"]) * pos["quantity"]
                executor.place_order(symbol, "SELL", pos["quantity"])
                risk_manager.record_realized_pnl(pnl)

        mark_price = market_data.get_ltp(symbol)
        open_value = sum(p["quantity"] * mark_price for p in executor.get_positions().values())
        equity_curve.append(executor.get_cash() + open_value)

        market_data.advance()

    final_equity = equity_curve[-1] if equity_curve else starting_cash
    peak = starting_cash
    max_drawdown_pct = 0.0
    for eq in equity_curve:
        peak = max(peak, eq)
        drawdown_pct = (peak - eq) / peak * 100 if peak > 0 else 0
        max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

    return {
        "starting_cash": starting_cash,
        "final_equity": final_equity,
        "total_return_pct": (final_equity - starting_cash) / starting_cash * 100,
        "max_drawdown_pct": max_drawdown_pct,
        "num_fills": len(executor.fills),
        "fills": executor.fills,
    }
