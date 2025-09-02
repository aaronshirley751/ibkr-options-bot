from datetime import datetime, timedelta
from typing import Any, Dict

import pandas as pd  # type: ignore

# simple in-memory debounce store: symbol -> last_whale_timestamp
_debounce: Dict[str, datetime] = {}


def whale_rules(df_60min: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Low-frequency whale rules using 60-min bars.

    df_60min must contain 'close' and 'volume' columns indexed by timestamp.
    Returns: {"signal": "BUY_CALL"|"BUY_PUT"|"HOLD", "confidence": 0..1}
    """
    # debounce: only one whale per symbol per 3 days
    now = datetime.utcnow()
    last = _debounce.get(symbol)
    if last and now - last < timedelta(days=3):
        return {"signal": "HOLD", "confidence": 0.0}

    if df_60min is None or len(df_60min) < 20:
        return {"signal": "HOLD", "confidence": 0.0}

    close = df_60min["close"].astype(float)
    vol = df_60min["volume"].astype(float)

    # 20-day high/low on 60-min closes (assumes df_60min covers 20 trading days)
    high_20 = close[-(20 * 6) :].max() if len(close) >= 20 * 6 else close.max()
    low_20 = close[-(20 * 6) :].min() if len(close) >= 20 * 6 else close.min()

    avg_vol = vol[-(20 * 6) :].mean() if len(vol) >= 20 * 6 else vol.mean()
    last_close = float(close.iloc[-1])
    last_vol = float(vol.iloc[-1])

    signal = "HOLD"
    confidence = 0.0

    # BUY CALL if 60m close > 20-day high with volume>1.5x avg
    if last_close > high_20 and last_vol > 1.5 * (avg_vol or 1):
        signal = "BUY_CALL"
        strength = (last_close - high_20) / high_20 if high_20 != 0 else 0.0
        vol_score = min(1.0, last_vol / (avg_vol or 1))
        confidence = min(1.0, 0.6 * min(1.0, strength * 5) + 0.4 * vol_score)

    # BUY PUT if 60m close < 20-day low with volume>1.5x avg
    if last_close < low_20 and last_vol > 1.5 * (avg_vol or 1):
        signal = "BUY_PUT"
        strength = (low_20 - last_close) / (low_20 or 1)
        vol_score = min(1.0, last_vol / (avg_vol or 1))
        confidence = min(1.0, 0.6 * min(1.0, strength * 5) + 0.4 * vol_score)

    if signal != "HOLD":
        _debounce[symbol] = now

    return {"signal": signal, "confidence": round(float(confidence), 3)}
