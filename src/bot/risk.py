from math import floor
from typing import Tuple


def position_size(equity: float, max_risk_pct: float, stop_loss_pct: float, option_premium: float) -> int:
    """Calculate option contract size given equity and risk parameters.

    size = floor((equity * max_risk_pct) / (option_premium * stop_loss_pct))
    size is clamped to be at least 1.
    """
    if equity <= 0 or option_premium <= 0 or stop_loss_pct <= 0:
        return 0
    raw = (equity * max_risk_pct) / (option_premium * stop_loss_pct)
    sz = floor(raw)
    return max(1, sz)


def guard_daily_loss(equity_start_day: float, equity_now: float, max_daily_loss_pct: float) -> bool:
    """Return True if daily loss guard should trigger (i.e., stop trading).

    Computes loss percentage from equity_start_day to equity_now and returns True
    when loss >= max_daily_loss_pct.
    """
    if equity_start_day <= 0:
        return False
    loss = equity_start_day - equity_now
    loss_pct = loss / equity_start_day
    return loss_pct >= abs(max_daily_loss_pct)


def stop_target_from_premium(premium: float, stop_pct: float, target_pct: float) -> Tuple[float, float]:
    stop = premium * (1 - stop_pct)
    target = premium * (1 + target_pct)
    return stop, target
