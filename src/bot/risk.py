import json
from datetime import datetime, timezone
from math import floor
from pathlib import Path
from typing import Optional, Tuple


def position_size(
    equity: float, max_risk_pct: float, stop_loss_pct: float, option_premium: float
) -> int:
    """Calculate option contract size based on account equity and risk parameters.
    
    Uses the Kelly-like formula: size = (account_risk_dollars) / (risk_per_contract)
    where account_risk_dollars = equity * max_risk_pct and 
    risk_per_contract = option_premium * stop_loss_pct (max loss if SL hits).
    
    Args:
        equity: Current account equity/balance in dollars.
        max_risk_pct: Maximum percentage of equity to risk on this trade (e.g., 0.01 for 1%).
        stop_loss_pct: Stop loss percentage from entry (e.g., 0.50 for 50% loss if triggered).
        option_premium: Current option price in dollars (determines per-contract notional).
    
    Returns:
        Number of option contracts to trade. Minimum 1 if parameters allow trading,
        0 if inputs are invalid (zero or negative values).
        
    Example:
        >>> position_size(equity=100000, max_risk_pct=0.01, stop_loss_pct=0.50, option_premium=2.50)
        4  # Risk $1000, lose $1.25 per share × $2.50 premium × 4 contracts = $1000
    """
    if equity <= 0 or option_premium <= 0 or stop_loss_pct <= 0:
        return 0
    
    # 1. Risk-based sizing (Kelly-like)
    # How many contracts can we handle based on max loss?
    raw_shares = (equity * max_risk_pct) / (option_premium * stop_loss_pct)
    size_risk = floor(raw_shares / 100.0)
    # Allow at least 1 contract if within risk tolerance boundaries or logical rounding
    size_risk = max(1, size_risk)

    # 2. Cash-based capping (The "Cash Guard")
    # Cap total cost at 95% of equity to avoid margin rejection
    cost_per_contract = option_premium * 100.0
    max_cost = equity * 0.95
    size_cash = floor(max_cost / cost_per_contract)

    # 3. Final sizing: strict minimum of both
    sz = min(size_risk, size_cash)
    
    return int(sz)


def guard_daily_loss(
    equity_start_day: float, equity_now: float, max_daily_loss_pct: float
) -> bool:
    """Check if daily loss exceeds the configured maximum threshold.
    
    Calculates loss percentage as (start_equity - current_equity) / start_equity
    and returns True if this percentage meets or exceeds the max_daily_loss_pct threshold.
    Used to halt trading for the remainder of the trading day after loss limit is hit.
    
    Args:
        equity_start_day: Account equity at start of trading day (reference point).
        equity_now: Current account equity.
        max_daily_loss_pct: Maximum acceptable daily loss as percentage (e.g., 0.05 for 5%).
    
    Returns:
        True if loss_percentage >= max_daily_loss_pct (guard should trigger), False otherwise.
        Returns False if start_equity <= 0 (edge case: no reference to measure loss).
    
    Example:
        >>> guard_daily_loss(100000, 95000, 0.10)  # Lost $5k, 5% < 10% limit
        False  # Keep trading
        >>> guard_daily_loss(100000, 94999, 0.05)  # Lost $5001, 5.001% > 5% limit
        True   # Stop trading for the day
    """
    if equity_start_day <= 0:
        return False
    loss = equity_start_day - equity_now
    loss_pct = loss / equity_start_day
    return loss_pct >= abs(max_daily_loss_pct)


def stop_target_from_premium(
    premium: float, stop_pct: float, target_pct: float
) -> Tuple[float, float]:
    """Calculate stop-loss and take-profit prices from option premium and percentages.

    Convenience function for computing bracket order thresholds.

    Args:
        premium: Current option premium/price in dollars.
        stop_pct: Stop-loss percentage below premium (e.g., 0.50 for -50%).
        target_pct: Take-profit percentage above premium (e.g., 0.25 for +25%).

    Returns:
        Tuple of (stop_loss_price, take_profit_price).

    Example:
        >>> stop_target_from_premium(2.50, stop_pct=0.50, target_pct=0.25)
        (1.25, 3.125)  # Stop at $1.25, profit at $3.125
    """
    stop = premium * (1 - stop_pct)
    target = premium * (1 + target_pct)
    return stop, target


# --- Daily loss guard persistence ---

DEFAULT_STATE_PATH = Path("logs/daily_state.json")


def _today_key() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def load_equity_state(path: Path = DEFAULT_STATE_PATH) -> dict:
    """Load daily equity state from persistent JSON file.
    
        File format: {"YYYY-MM-DD": equity_float, ...}
        Used to persist start-of-day equity across process restarts.
    
        Args:
            path: Path to the JSON state file (default: logs/daily_state.json).
    
        Returns:
            Dictionary mapping date strings to equity values. Empty dict if file missing or corrupted.
        """
    try:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # pylint: disable=broad-except
        return {}


def save_equity_state(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    """Save daily equity state to persistent JSON file with atomic writes.
    
        Uses temp file + rename pattern to avoid data corruption on crashes.
        Creates parent directories as needed.
    
        Args:
            state: Dictionary mapping date strings to equity float values.
            path: Path to the JSON state file (default: logs/daily_state.json).
        """
    import os
    import uuid
    
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use unique temp file to prevent race conditions
    tmp = path.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f)
        tmp.replace(path)
    finally:
        # Clean up temp file if replace failed
        if tmp.exists():
            tmp.unlink()


def get_start_of_day_equity(broker, path: Path = DEFAULT_STATE_PATH) -> Optional[float]:
    """Load or initialize start-of-day equity from persistent storage.

    Checks if today's date has a recorded start-of-day equity. If missing, queries
    broker for current equity and saves it as the day's reference point. This allows
    the daily loss guard to survive process restarts.

    Args:
        broker: Broker instance with pnl() method returning dict with 'net' key.
        path: Path to the JSON state file (default: logs/daily_state.json).

    Returns:
        Start-of-day equity in dollars. Creates new entry if today missing.
        Returns 0.0 if broker.pnl() fails.
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


def reset_daily_loss_guard(path: Path = DEFAULT_STATE_PATH) -> None:
    """Clear today's entry from daily loss guard state.
    
    Used for extended dry-run testing across multiple restarts. Should only be
    called when reset_daily_guard_on_start is True in settings.
    
    Args:
        path: Path to the JSON state file (default: logs/daily_state.json).
    """
    state = load_equity_state(path)
    key = _today_key()
    if key in state:
        del state[key]
        save_equity_state(state, path)


def should_stop_trading_today(
    broker, max_daily_loss_pct: float, path: Path = DEFAULT_STATE_PATH
) -> bool:
    """Check if daily loss limit has been exceeded, halting new entries."""
    sod = get_start_of_day_equity(broker, path)
    try:
        now = float(broker.pnl().get("net", 0.0))
    except Exception:  # pylint: disable=broad-except
        now = 0.0
    return guard_daily_loss(sod or 0.0, now, max_daily_loss_pct)
