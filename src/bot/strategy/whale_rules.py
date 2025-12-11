from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict

import pandas as pd  # type: ignore
# Strategy parameters: tunable constants for whale signal generation
# Whale debounce period: prevents rapid repeated signals on same symbol
WHALE_DEBOUNCE_DAYS = 3
# Lookback window for high/low and volume calculations (in 60-min bars)
# 20 trading days ≈ 120 60-min bars (assuming 6 bars per trading day)
WHALE_LOOKBACK_BARS = 120
# Volume multiplier: unusual activity must exceed average by this factor
WHALE_VOLUME_SPIKE_THRESHOLD = 1.5
# Confidence scoring weights
WHALE_STRENGTH_WEIGHT = 0.6  # Weight of price extremity in confidence
WHALE_VOLUME_WEIGHT = 0.4  # Weight of volume spike in confidence

# simple in-memory debounce store: symbol -> last_whale_timestamp
_debounce: Dict[str, datetime] = {}
_debounce_lock = Lock()


def whale_rules(df_60min: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Low-frequency whale rules using 60-min bars.

    df_60min must contain 'close' and 'volume' columns indexed by timestamp.
    Returns: {"signal": "BUY_CALL"|"BUY_PUT"|"HOLD", "confidence": 0..1}
    """
        # Validate input type and required columns
        if df_60min is None:
            return {"signal": "HOLD", "confidence": 0.0, "reason": "none_dataframe"}
    
        if not hasattr(df_60min, "columns"):
            return {"signal": "HOLD", "confidence": 0.0, "reason": "not_a_dataframe"}
    
        required_cols = {"close", "volume"}
        missing = required_cols - set(df_60min.columns)
        if missing:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": f"missing_columns: {missing}",
            }
    
        if len(df_60min) < 20:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": f"insufficient_bars: {len(df_60min)}",
            }

    # debounce: only one whale per symbol per 3 days
    now = datetime.now(timezone.utc)
    with _debounce_lock:
        last = _debounce.get(symbol)
    if last and now - last < timedelta(days=WHALE_DEBOUNCE_DAYS):
        return {"signal": "HOLD", "confidence": 0.0}
    


    close = df_60min["close"].astype(float)
    vol = df_60min["volume"].astype(float)
    
    # Handle NaN values
    if close.isna().all() or vol.isna().all():
        return {"signal": "HOLD", "confidence": 0.0, "reason": "all_nan_values"}
    
    # Clean NaN values
    close = close.dropna()
    vol = vol.dropna()
    
    if len(close) < 20 or len(vol) < 20:
        return {
            "signal": "HOLD",
            "confidence": 0.0,
            "reason": f"insufficient_valid_data: close={len(close)} vol={len(vol)}",
        }

    # 20-day high/low on 60-min closes (assumes df_60min covers 20 trading days)
    high_20 = (
        close[-WHALE_LOOKBACK_BARS:].max()
        if len(close) >= WHALE_LOOKBACK_BARS
        else close.max()
    )
    low_20 = (
        close[-WHALE_LOOKBACK_BARS:].min()
        if len(close) >= WHALE_LOOKBACK_BARS
        else close.min()
    )
    avg_vol = (
        vol[-WHALE_LOOKBACK_BARS:].mean()
        if len(vol) >= WHALE_LOOKBACK_BARS
        else vol.mean()
    )
    last_close = float(close.iloc[-1])
    last_vol = float(vol.iloc[-1])

    signal = "HOLD"
    confidence = 0.0

    # BUY CALL if 60m close > high with volume spike
    if last_close > high_20 and last_vol > WHALE_VOLUME_SPIKE_THRESHOLD * (avg_vol or 1):
        signal = "BUY_CALL"
        strength = (last_close - high_20) / high_20 if high_20 != 0 else 0.0
        vol_score = min(1.0, last_vol / (avg_vol or 1))
        confidence = min(
            1.0, WHALE_STRENGTH_WEIGHT * min(1.0, strength * 5) + WHALE_VOLUME_WEIGHT * vol_score
        )

    # BUY PUT if 60m close < low with volume spike
    if last_close < low_20 and last_vol > WHALE_VOLUME_SPIKE_THRESHOLD * (avg_vol or 1):
        signal = "BUY_PUT"
        strength = (low_20 - last_close) / (low_20 or 1)
        vol_score = min(1.0, last_vol / (avg_vol or 1))
        confidence = min(
            1.0, WHALE_STRENGTH_WEIGHT * min(1.0, strength * 5) + WHALE_VOLUME_WEIGHT * vol_score
        )

    if signal != "HOLD":
        with _debounce_lock:
            _debounce[symbol] = now

    return {"signal": signal, "confidence": round(float(confidence), 3)}
