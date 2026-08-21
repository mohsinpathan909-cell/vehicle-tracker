from risk.risk_manager import RiskManager


def make_rm(**overrides):
    defaults = dict(capital=100000, risk_per_trade_pct=1, stop_loss_pct=2,
                     target_pct=4, max_daily_loss_pct=3, max_open_positions=1)
    defaults.update(overrides)
    return RiskManager(**defaults)


def test_size_position_risks_the_configured_pct():
    rm = make_rm(capital=100000, risk_per_trade_pct=1, stop_loss_pct=2)
    qty = rm.size_position(entry_price=100)
    # risk_amount = 1000, stop_distance = 2 -> qty = 500
    assert qty == 500


def test_stop_loss_and_target_prices_for_buy():
    rm = make_rm(stop_loss_pct=2, target_pct=4)
    assert rm.stop_loss_price(100, "BUY") == 98
    assert rm.target_price(100, "BUY") == 104


def test_daily_loss_limit_blocks_new_positions():
    rm = make_rm(capital=100000, max_daily_loss_pct=3, max_open_positions=5)
    assert rm.can_open_new_position(0) is True
    rm.record_realized_pnl(-3500)
    assert rm.daily_loss_limit_hit() is True
    assert rm.can_open_new_position(0) is False


def test_max_open_positions_blocks_new_positions():
    rm = make_rm(max_open_positions=1)
    assert rm.can_open_new_position(1) is False


def test_reset_day_clears_pnl():
    rm = make_rm(max_daily_loss_pct=3, capital=100000)
    rm.record_realized_pnl(-5000)
    assert rm.daily_loss_limit_hit() is True
    rm.reset_day()
    assert rm.daily_loss_limit_hit() is False
