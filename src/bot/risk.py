import json
from datetime import datetime, timezone
from math import floor
from pathlib import Path
from typing import Optional, Tuple


def position_size(
    equity: float, max_risk_pct: float, stop_loss_pct: float, option_premium: float
) -> int:
    """Calculate option contract size given equity and risk parameters.

    size = floor((equity * max_risk_pct) / (option_premium * stop_loss_pct))
    size is clamped to be at least 1.
    """
    if equity <= 0 or option_premium <= 0 or stop_loss_pct <= 0:
        return 0
    raw = (equity * max_risk_pct) / (option_premium * stop_loss_pct)
    sz = floor(raw)
    return max(1, sz)


def guard_daily_loss(
    equity_start_day: float, equity_now: float, max_daily_loss_pct: float
) -> bool:
    """Return True if daily loss guard should trigger (i.e., stop trading).

    Computes loss percentage from equity_start_day to equity_now and returns True
    when loss >= max_daily_loss_pct.
    """
    if equity_start_day <= 0:
        return False
    loss = equity_start_day - equity_now
    loss_pct = loss / equity_start_day
    return loss_pct >= abs(max_daily_loss_pct)


def stop_target_from_premium(
    premium: float, stop_pct: float, target_pct: float
) -> Tuple[float, float]:
    stop = premium * (1 - stop_pct)
    target = premium * (1 + target_pct)
    return stop, target


# --- Daily loss guard persistence ---

DEFAULT_STATE_PATH = Path("logs/daily_state.json")


def _today_key() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def load_equity_state(path: Path = DEFAULT_STATE_PATH) -> dict:
    try:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # pylint: disable=broad-except
        return {}


def save_equity_state(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f)
    tmp.replace(path)


def get_start_of_day_equity(broker, path: Path = DEFAULT_STATE_PATH) -> Optional[float]:
    """Load or initialize start-of-day equity from persistent storage.

    If today is not present, record current equity as start-of-day.
    """
    state = load_equity_state(path)
    key = _today_key()
    if key in state and isinstance(state[key], (int, float)):
        return float(state[key])
    # initialize
    try:
        cur = float(broker.pnl().get("net", 0.0))
    except Exception:  # pylint: disable=broad-except
        cur = 0.0
    state[key] = cur
    save_equity_state(state, path)
    return cur


def should_stop_trading_today(
    broker, max_daily_loss_pct: float, path: Path = DEFAULT_STATE_PATH
) -> bool:
    """Return True if daily loss exceeds threshold, based on persisted start-of-day equity."""
    sod = get_start_of_day_equity(broker, path)
    try:
        now = float(broker.pnl().get("net", 0.0))
    except Exception:  # pylint: disable=broad-except
        now = 0.0
    return guard_daily_loss(sod or 0.0, now, max_daily_loss_pct)
