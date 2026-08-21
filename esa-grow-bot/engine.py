import time
from datetime import datetime

from broker.base import MarketData, OrderExecutor
from journal import TradeJournal
from risk.risk_manager import RiskManager
from strategy.sma_crossover import SmaCrossoverStrategy


def is_market_open(now: datetime | None = None) -> bool:
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False
    open_t = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now <= close_t


class TradingEngine:
    """Live/paper loop: poll market data, ask the strategy for a signal, size
    it via the risk manager, and send it to whichever OrderExecutor was
    injected (PaperOrderExecutor never touches real money; GrowwOrderExecutor
    does)."""

    def __init__(self, market_data: MarketData, order_executor: OrderExecutor,
                 strategy: SmaCrossoverStrategy, risk_manager: RiskManager,
                 symbol: str, mode: str, poll_interval_seconds: int = 60,
                 journal: TradeJournal | None = None):
        self.market_data = market_data
        self.order_executor = order_executor
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.symbol = symbol
        self.mode = mode
        self.poll_interval_seconds = poll_interval_seconds
        self.journal = journal or TradeJournal()

    def step(self):
        history = self.market_data.get_historical(self.symbol, interval="5m", lookback_days=self.strategy.long_window + 5)
        signal = self.strategy.generate_signal(history)
        positions = self.order_executor.get_positions()
        open_count = sum(1 for p in positions.values() if p["quantity"] > 0)

        if signal == "BUY" and self.risk_manager.can_open_new_position(open_count):
            ltp = self.market_data.get_ltp(self.symbol)
            qty = self.risk_manager.size_position(ltp)
            if qty > 0:
                result = self.order_executor.place_order(self.symbol, "BUY", qty)
                self.journal.log(self.mode, self.symbol, "BUY", qty, result.get("price", ltp), result.get("status", "?"))

        elif signal == "SELL":
            pos = positions.get(self.symbol)
            if pos and pos["quantity"] > 0:
                ltp = self.market_data.get_ltp(self.symbol)
                pnl = (ltp - pos["avg_price"]) * pos["quantity"]
                result = self.order_executor.place_order(self.symbol, "SELL", pos["quantity"])
                self.risk_manager.record_realized_pnl(pnl)
                self.journal.log(self.mode, self.symbol, "SELL", pos["quantity"], result.get("price", ltp), result.get("status", "?"))

    def run_forever(self):
        print(f"[{self.mode}] engine starting for {self.symbol}, polling every {self.poll_interval_seconds}s. Ctrl+C to stop.")
        last_day = datetime.now().date()
        while True:
            today = datetime.now().date()
            if today != last_day:
                self.risk_manager.reset_day()
                last_day = today

            if is_market_open():
                try:
                    self.step()
                except Exception as e:
                    print(f"engine step failed: {e}")
            else:
                print("market closed, waiting...")

            time.sleep(self.poll_interval_seconds)
