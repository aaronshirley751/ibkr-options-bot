from typing import Any, Dict, Optional

from .. import log as _log
from ..data.options import find_strategic_option # Intention: Use in scheduler, logic defines criteria here

logger = _log.logger

# Constants for VIX Regimes
VIX_COMPLACENCY = 15.0
VIX_NORMAL = 20.0
VIX_ELEVATED = 30.0

# Strategic Universes (Hardcoded for initial release as per strategy doc)
PUT_UNIVERSE = {
    "SPY": {"otm": (0.05, 0.10), "dte": (30, 60), "desc": "Index Protection"},
    "QQQ": {"otm": (0.00, 0.10), "dte": (30, 45), "desc": "Tech Hedge"},
    "IWM": {"otm": (0.05, 0.10), "dte": (30, 60), "desc": "Small Cap Hedge"},
    "NVDA": {"otm": (0.00, 0.10), "dte": (30, 60), "desc": "Semi Risk"},
    "TSLA": {"otm": (0.10, 0.20), "dte": (30, 60), "desc": "Vol Hedge"},
}

CALL_UNIVERSE = {
    "GLD": {"otm": (0.02, 0.05), "dte": (60, 90), "desc": "Safe Haven"},
    "LMT": {"otm": (0.02, 0.05), "dte": (45, 90), "desc": "Defense"},
    "XLE": {"otm": (0.02, 0.05), "dte": (30, 60), "desc": "Energy Shock"},
}

def identify_regime(vix_value: float) -> str:
    """Determine market regime based on VIX."""
    if vix_value < VIX_COMPLACENCY:
        return "COMPLACENCY"
    elif vix_value < VIX_NORMAL:
        return "NORMAL"
    elif vix_value < VIX_ELEVATED:
        return "ELEVATED"
    else:
        return "PEAK_FEAR"

def geo_rules(symbol: str, vix_value: float) -> Dict[str, Any]:
    """Determine geopolitical strategy action based on VIX regime and symbol.
    
    Returns:
        Dict with keys: signal, confidence, reason, params (dict for option picker)
    """
    regime = identify_regime(vix_value)
    
    # 1. PEAK FEAR (>30) -> Sell Volatility / Cash / Reduce Hedges (Too expensive)
    if regime == "PEAK_FEAR":
        return {
            "signal": "HOLD",
            "confidence": 0.0,
            "reason": f"Peak Fear (VIX {vix_value:.2f}): Hedges too expensive/Take Profit zone."
        }
        
    # 2. COMPLACENCY (<15) -> Buy Cheap Protection (Puts)
    if regime == "COMPLACENCY":
        if symbol in PUT_UNIVERSE:
            cfg = PUT_UNIVERSE[symbol]
            return {
                "signal": "BUY_PUT",
                "confidence": 0.85,
                "reason": f"Complacency (VIX {vix_value:.2f}): Buying cheap protection.",
                "params": {
                    "min_dte": cfg["dte"][0],
                    "max_dte": cfg["dte"][1],
                    "otm_pct_min": cfg["otm"][0],
                    "otm_pct_max": cfg["otm"][1]
                }
            }
        return {"signal": "HOLD", "confidence": 0.0, "reason": "Not in Put Universe"}
        
    # 3. NORMAL (15-20) -> Balanced
    if regime == "NORMAL":
        # In Normal regime, we selectively buy calls in Defense/Gold or Calls in Index if bullish
        # Strategy Doc says "Maintain Baseline".
        # We can look for Opportunistic Calls here.
        if symbol in CALL_UNIVERSE:
            cfg = CALL_UNIVERSE[symbol]
            return {
                "signal": "BUY_CALL",
                "confidence": 0.60,
                "reason": f"Normal Regime (VIX {vix_value:.2f}): Opportunistic Defense/Gold.",
                "params": {
                    "min_dte": cfg["dte"][0],
                    "max_dte": cfg["dte"][1],
                    "otm_pct_min": cfg["otm"][0],
                    "otm_pct_max": cfg["otm"][1]
                }
            }
        return {"signal": "HOLD", "confidence": 0.0, "reason": "Normal Regime: Only opportunistic trades."}
        
    # 4. ELEVATED (20-30) -> Selective Hedging / Vol Harvesting
    if regime == "ELEVATED":
        # Priority: Defense Stocks (Calls) + Existing Hedges (Hold/Profit)
        if symbol in CALL_UNIVERSE:
             cfg = CALL_UNIVERSE[symbol]
             return {
                "signal": "BUY_CALL",
                "confidence": 0.75,
                "reason": f"Elevated Regime (VIX {vix_value:.2f}): Flight to safety assets.",
                "params": {
                    "min_dte": cfg["dte"][0],
                    "max_dte": cfg["dte"][1],
                    "otm_pct_min": cfg["otm"][0],
                    "otm_pct_max": cfg["otm"][1]
                }
            }
        # Avoid buying fresh Puts here unless specific breakdown (too expensive already?)
        # Strategy doc says "Selective Hedging". We can allow it but lower confidence?
        # Let's stick to Calls for Defense in elevated, or Puts for SPY if not held.
        return {"signal": "HOLD", "confidence": 0.0, "reason": "Elevated Regime: Holding existing."}
        
    return {"signal": "HOLD", "confidence": 0.0, "reason": "Unknown State"}
