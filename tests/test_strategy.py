from datetime import datetime, timezone

import pandas as pd

from src.bot.strategy.scalp_rules import scalp_signal
from src.bot.strategy.whale_rules import whale_rules


def _make_bars(n=60, start=None, base=100.0):
    start = start or datetime.now(timezone.utc)
    idx = pd.date_range(end=start, periods=n, freq="1min")
    close = pd.Series([base + i * 0.01 for i in range(n)], index=idx)
    high = close + 0.05
    low = close - 0.05
    vol = pd.Series([1000] * n, index=idx)
    return pd.DataFrame(
        {"open": close, "high": high, "low": low, "close": close, "volume": vol}
    )


def test_scalp_signal_hold_on_small_input():
    sig = scalp_signal(pd.DataFrame())
    assert sig["signal"] == "HOLD"


def test_scalp_signal_has_keys():
    df = _make_bars()
    sig = scalp_signal(df)
    assert "signal" in sig and "confidence" in sig


def _make_60m_bars(days=20, base=100.0):
    n = days * 6
    idx = pd.date_range(end=datetime.now(timezone.utc), periods=n, freq="60min")
    close = pd.Series([base + (i % 6) * 0.5 for i in range(n)], index=idx)
    vol = pd.Series([1000 + (i % 6) * 100 for i in range(n)], index=idx)
    return pd.DataFrame({"close": close, "volume": vol})


def test_whale_rules_hold_on_insufficient_history():
    df = _make_60m_bars(days=1)
    res = whale_rules(df, "SPY")
    assert res["signal"] == "HOLD"
