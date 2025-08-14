from typing import List
import numpy as np


def moving_average(prices: List[float], period: int) -> List[float]:
    """Simple moving average (valid values only).

    Returns a list of MA values length = len(prices) - period + 1.
    """
    prices = np.asarray(prices, dtype=float)
    if len(prices) < period:
        return []
    return np.convolve(prices, np.ones(period) / period, mode="valid").tolist()


def vwap(prices: List[float], volumes: List[float], period: int) -> List[float]:
    """Rolling VWAP over a fixed window. Returns only valid values.

    Simple implementation: for each window compute sum(price*vol)/sum(vol).
    """
    if not prices or not volumes:
        return []
    p = np.asarray(prices, dtype=float)
    v = np.asarray(volumes, dtype=float)
    if p.shape != v.shape:
        return []
    n = len(p)
    if n < period:
        return []
    out = []
    for i in range(period - 1, n):
        window_p = p[i - period + 1 : i + 1]
        window_v = v[i - period + 1 : i + 1]
        denom = window_v.sum()
        out.append((window_p * window_v).sum() / denom if denom != 0 else float('nan'))
    return out


def rsi(prices: List[float], period: int = 14) -> List[float]:
    """Return RSI values. Uses Wilder smoothing.

    Returns list with length = len(prices) - period.
    """
    prices = np.asarray(prices, dtype=float)
    if prices.size <= period:
        return []
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else float('inf')
    rsi_vals = [100 - 100 / (1 + rs)]
    for delta in deltas[period:]:
        up_val = max(delta, 0)
        down_val = -min(delta, 0)
        up = (up * (period - 1) + up_val) / period
        down = (down * (period - 1) + down_val) / period
        rs = up / down if down != 0 else float('inf')
        rsi_vals.append(100 - 100 / (1 + rs))
    return rsi_vals
