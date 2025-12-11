from typing import Any, Dict

import pandas as pd  # type: ignore


def _rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
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

    ema_fast = close.ewm(span=8, adjust=False).mean().iloc[-1]
    ema_slow = close.ewm(span=21, adjust=False).mean().iloc[-1]

    rsi_series = _rsi_series(close, period=14)
    rsi_val = (
        float(rsi_series.iloc[-1])
        if not rsi_series.empty and pd.notna(rsi_series.iloc[-1])
        else 50.0
    )

    last_price = float(close.iloc[-1])

    signal = "HOLD"
    confidence = 0.0

    # BUY if ema_fast>ema_slow, price>vwap, rsi between 45..70
    if ema_fast > ema_slow and last_price > vwap_val and 45 <= rsi_val <= 70:
        signal = "BUY"
        # confidence based on strength of ema gap and rsi position
        gap = max(0.0, (ema_fast - ema_slow) / ema_slow) if ema_slow != 0 else 0.0
        rsi_score = (rsi_val - 45) / (70 - 45)
        confidence = min(1.0, 0.6 * min(1.0, gap * 5) + 0.4 * rsi_score)

    # SELL if ema_fast<ema_slow or rsi<40
    elif ema_fast < ema_slow or rsi_val < 40:
        signal = "SELL"
        gap = max(
            0.0,
            (ema_slow - ema_fast) / (ema_fast if ema_fast != 0 else ema_slow or 1.0),
        )
        rsi_score = max(0.0, (40 - rsi_val) / 40)
        confidence = min(1.0, 0.6 * min(1.0, gap * 5) + 0.4 * rsi_score)

    return {"signal": signal, "confidence": round(float(confidence), 3)}
