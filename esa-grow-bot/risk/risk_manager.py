"""Position sizing and hard stop rules. This is what keeps a bad strategy
from wiping out the account in one session -- it does not make the
strategy profitable."""


class RiskManager:
    def __init__(self, capital: float, risk_per_trade_pct: float, stop_loss_pct: float,
                 target_pct: float, max_daily_loss_pct: float, max_open_positions: int):
        self.capital = capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.stop_loss_pct = stop_loss_pct
        self.target_pct = target_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_open_positions = max_open_positions
        self.realized_pnl_today = 0.0

    def size_position(self, entry_price: float) -> int:
        """Quantity such that a stop-loss hit loses ~risk_per_trade_pct of capital."""
        risk_amount = self.capital * self.risk_per_trade_pct / 100
        stop_distance = entry_price * self.stop_loss_pct / 100
        if stop_distance <= 0:
            return 0
        return max(0, int(risk_amount / stop_distance))

    def stop_loss_price(self, entry_price: float, side: str) -> float:
        delta = entry_price * self.stop_loss_pct / 100
        return entry_price - delta if side == "BUY" else entry_price + delta

    def target_price(self, entry_price: float, side: str) -> float:
        delta = entry_price * self.target_pct / 100
        return entry_price + delta if side == "BUY" else entry_price - delta

    def record_realized_pnl(self, pnl: float):
        self.realized_pnl_today += pnl

    def daily_loss_limit_hit(self) -> bool:
        max_loss = self.capital * self.max_daily_loss_pct / 100
        return self.realized_pnl_today <= -max_loss

    def can_open_new_position(self, open_position_count: int) -> bool:
        return open_position_count < self.max_open_positions and not self.daily_loss_limit_hit()

    def reset_day(self):
        self.realized_pnl_today = 0.0
