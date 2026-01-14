from typing import Any, Dict

import pandas as pd  # type: ignore
# Strategy parameters: tunable constants for scalp signal generation
# RSI (Relative Strength Index) period for momentum calculation
RSI_PERIOD = 14
# EMA (Exponential Moving Average) spans for trend detection
EMA_FAST_SPAN = 8  # Fast EMA: captures recent momentum
EMA_SLOW_SPAN = 21  # Slow EMA: captures intermediate trend
# RSI bounds for BUY signal (momentum not overbought)
RSI_BUY_LOW = 45  # Lower bound: momentum building
RSI_BUY_HIGH = 70  # Upper bound: not yet overbought
# RSI threshold for SELL signal (oversold conditions)
RSI_SELL_THRESHOLD = 40  # Below this indicates weak momentum
# Confidence scoring weights
EMA_WEIGHT = 0.6  # Weight of EMA gap in confidence score
RSI_WEIGHT = 0.4  # Weight of RSI position in confidence score


def _rsi_series(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(alpha=1 / period, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = ma_up / ma_down
    rsi = 100 - (100 / (1 + rs))
    return rsi


def scalp_signal(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute scalp signal from 1-min bars DataFrame.

    df must contain columns: ['open','high','low','close','volume'] indexed by timestamp.
    Returns: {"signal": "BUY"|"SELL"|"HOLD", "confidence": 0..1}
    """
    if df is None or len(df) < 30:
        return {"signal": "HOLD", "confidence": 0.0}
    # Validate required columns exist
    required_cols = {"open", "high", "low", "close", "volume"}
    if not hasattr(df, "columns"):
        return {"signal": "HOLD", "confidence": 0.0, "reason": "not_a_dataframe"}
    
    missing = required_cols - set(df.columns)
    if missing:
        return {
            "signal": "HOLD",
            "confidence": 0.0,
            "reason": f"missing_columns: {missing}",
        }

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    # Handle NaN values
    if close.isna().all() or high.isna().all() or low.isna().all() or vol.isna().all():
        return {"signal": "HOLD", "confidence": 0.0, "reason": "all_nan_values"}
    
    # Drop NaN rows for calculations
    close = close.dropna()
    high = high.dropna()
    low = low.dropna()
    vol = vol.dropna()
    
    if len(close) < 30:
        return {
            "signal": "HOLD",
            "confidence": 0.0,
            "reason": f"insufficient_valid_bars: {len(close)}",
        }

    # VWAP (typical price * vol) / vol
    tp = (high + low + close) / 3.0
    vwap_val = (tp * vol).sum() / vol.sum() if vol.sum() > 0 else close.iloc[-1]

    ema_fast = close.ewm(span=EMA_FAST_SPAN, adjust=False).mean().iloc[-1]
    ema_slow = close.ewm(span=EMA_SLOW_SPAN, adjust=False).mean().iloc[-1]

    rsi_series = _rsi_series(close, period=RSI_PERIOD)
    rsi_val = (
        float(rsi_series.iloc[-1])
        if not rsi_series.empty and pd.notna(rsi_series.iloc[-1])
        else 50.0
    )

    last_price = float(close.iloc[-1])

    signal = "HOLD"
    confidence = 0.0

    # BUY if ema_fast>ema_slow, price>vwap, rsi between RSI_BUY_LOW..RSI_BUY_HIGH
    if ema_fast > ema_slow and last_price > vwap_val and RSI_BUY_LOW <= rsi_val <= RSI_BUY_HIGH:
        signal = "BUY"
        # confidence based on strength of ema gap and rsi position
        gap = max(0.0, (ema_fast - ema_slow) / ema_slow) if ema_slow != 0 else 0.0
        rsi_score = (rsi_val - RSI_BUY_LOW) / (RSI_BUY_HIGH - RSI_BUY_LOW)
        confidence = min(1.0, EMA_WEIGHT * min(1.0, gap * 500) + RSI_WEIGHT * rsi_score)

    # SELL if ema_fast<ema_slow or rsi < RSI_SELL_THRESHOLD
    elif ema_fast < ema_slow or rsi_val < RSI_SELL_THRESHOLD:
        signal = "SELL"
        gap = max(
            0.0,
            (ema_slow - ema_fast) / (ema_fast if ema_fast != 0 else ema_slow or 1.0),
        )
        rsi_score = max(0.0, (RSI_SELL_THRESHOLD - rsi_val) / RSI_SELL_THRESHOLD)
        confidence = min(1.0, EMA_WEIGHT * min(1.0, gap * 500) + RSI_WEIGHT * rsi_score)

    return {"signal": signal, "confidence": round(float(confidence), 3)}
