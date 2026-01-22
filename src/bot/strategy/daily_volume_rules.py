from typing import Any, Dict
import pandas as pd  # type: ignore

# Aggressive Daily Volume Strategy Parameters
# Extremely short lookback to catch intraday momentum
# Relaxed volume requirements to ensure frequent activity

DV_LOOKBACK_BARS = 10         # ~1.5 days of trading hours (on 1h bars)
DV_VOLUME_THRESHOLD = 0.8     # 0.8x Avg Vol (Deliberate pace per briefing)
DV_PRICE_MOMENTUM = 0.001     # 0.1% price move required (minimal filter to avoid flat chop)

def daily_volume_rules(df_60min: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """
    Aggressive volume-supported trend following.
    
    Logic:
    1. Calculate 10-period SMA and Average Volume.
    2. If Volume > 0.8 * Avg (Relaxed filter):
       - If Close > SMA + Momentum: BUY_CALL
       - If Close < SMA - Momentum: BUY_PUT
    3. No debounce (trades every cycle if condition met).
    """
    # 1. Validation
    if df_60min is None or not hasattr(df_60min, "columns"):
        return {"signal": "HOLD", "confidence": 0.0, "reason": "invalid_data"}

    required_cols = {"close", "volume"}
    if not required_cols.issubset(df_60min.columns):
        return {"signal": "HOLD", "confidence": 0.0, "reason": "missing_cols"}

    # Need very few bars for this aggressive strategy
    if len(df_60min) < DV_LOOKBACK_BARS + 1:
        return {"signal": "HOLD", "confidence": 0.0, "reason": "insufficient_bars"}

    # 2. Data Prep
    close = df_60min["close"].astype(float)
    vol = df_60min["volume"].astype(float)
    
    # Calculate indicators on the lookback window
    # We use the window ending at -1 (previous completed bars) to establish baseline
    # But usually we compare 'last' against 'window'. 
    
    # Last complete bar (or current forming bar? Scheduler usually passes history including latest)
    last_close = float(close.iloc[-1])
    last_vol = float(vol.iloc[-1])
    
    # Baseline: Average of previous N bars
    # Note: excluding the last bar from the average prevents the spike itself from skewing the average too much
    recent_vol = vol.iloc[-(DV_LOOKBACK_BARS+1):-1] 
    recent_close = close.iloc[-(DV_LOOKBACK_BARS+1):-1]
    
    avg_vol = recent_vol.mean() if not recent_vol.empty else last_vol
    sma = recent_close.mean() if not recent_close.empty else last_close

    # 3. Aggressive Logic
    signal = "HOLD"
    confidence = 0.0
    reason = []

    # Volume Gate (Very relaxed: 80% of average)
    vol_ratio = last_vol / (avg_vol or 1)
    if vol_ratio >= DV_VOLUME_THRESHOLD:
        # Price Momentum Gate
        # Is price deviating from the short-term mean?
        pct_dev = (last_close - sma) / (sma or 1)
        
        if pct_dev > DV_PRICE_MOMENTUM:
            signal = "BUY_CALL"
            # Confidence scales with volume and spread
            confidence = min(1.0, 0.5 + (vol_ratio * 0.1)) 
            reason.append(f"Bullish break SMA ({pct_dev:.2%}) with Vol {vol_ratio:.2f}x")
            
        elif pct_dev < -DV_PRICE_MOMENTUM:
            signal = "BUY_PUT"
            confidence = min(1.0, 0.5 + (vol_ratio * 0.1))
            reason.append(f"Bearish break SMA ({pct_dev:.2%}) with Vol {vol_ratio:.2f}x")
        else:
            reason.append(f"Flat price ({pct_dev:.2%})")
            
    else:
        reason.append(f"Low Vol ({vol_ratio:.2f}x < {DV_VOLUME_THRESHOLD})")

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "reason": "; ".join(reason) if reason else "Logic fallthrough"
    }
