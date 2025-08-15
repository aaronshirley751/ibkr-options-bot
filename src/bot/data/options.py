from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple

from loguru import logger

# Types expected from broker.option_chain() and broker.market_data():
# - option contracts carry fields: symbol, right, strike, expiry, multiplier
# - market_data(contract_or_symbol) returns object with bid, ask, last, volume


def nearest_friday(start: datetime) -> datetime:
    # find next Friday (weekly expiry)
    days_ahead = 4 - start.weekday()  # Monday=0
    if days_ahead <= 0:
        days_ahead += 7
    return (start + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)


def nearest_atm_strike(last_price: float, strikes: list) -> Optional[float]:
    if not strikes:
        return None
    return min(strikes, key=lambda s: abs(s - last_price))


def _strike_from_moneyness(last_price: float, strikes: List[float], moneyness: str) -> Optional[float]:
    if not strikes:
        return None
    # offset logic: itmp1 = one step in-the-money; otmp1 = one step out-of-the-money
    sorted_strikes = sorted(strikes)
    # find ATM index
    atm = nearest_atm_strike(last_price, sorted_strikes)
    if atm is None:
        return None
    idx = sorted_strikes.index(atm)
    if moneyness == "atm":
        return atm
    if moneyness == "itmp1":
        # call: strike below last; put: strike above last -> decided later by right
        # here we just move one step towards ITM on the strike ladder; sign handled later
        return sorted_strikes[max(0, idx - 1)]
    if moneyness == "otmp1":
        return sorted_strikes[min(len(sorted_strikes) - 1, idx + 1)]
    return atm


def pick_weekly_option(
    broker,
    underlying: str,
    right: str,
    last_price: float,
    moneyness: str = "atm",
    min_volume: int = 100,
    max_spread_pct: float = 2.0,
) -> Optional[object]:
    """Pick nearest-Friday weekly option for the given underlying and right ("C"/"P").

    Applies moneyness offsets and filters by volume and bid-ask spread percent.
    Returns the best OptionContract or None.
    """
    try:
        contracts = broker.option_chain(underlying, expiry_hint="weekly")
    except Exception:
        logger.exception("option_chain failed for %s", underlying)
        return None
    if not contracts:
        return None

    # Narrow by right
    contracts = [c for c in contracts if getattr(c, "right", "").upper() == right.upper()]
    if not contracts:
        return None

    # Gather available strikes from contracts
    strikes = sorted({float(getattr(c, "strike", 0.0)) for c in contracts})
    target_strike = _strike_from_moneyness(last_price, strikes, moneyness)
    if target_strike is None:
        return None

    # candidates at or near strike (prefer exact, else nearest)
    def _strike_distance(c) -> float:
        return abs(float(getattr(c, "strike", 0.0)) - float(target_strike))

    candidates = sorted(contracts, key=_strike_distance)[:5]

    # Filter by liquidity using current quotes
    viable: List[Tuple[object, float]] = []
    for c in candidates:
        try:
            q = broker.market_data(getattr(c, "symbol", c))
        except Exception:
            continue
        bid = float(getattr(q, "bid", 0.0) or 0.0)
        ask = float(getattr(q, "ask", 0.0) or 0.0)
        vol = int(getattr(q, "volume", 0) or 0)
        if vol < int(min_volume):
            continue
        if bid <= 0 or ask <= 0 or ask < bid:
            continue
        spread_pct = (ask - bid) / ask * 100.0
        if spread_pct > float(max_spread_pct):
            continue
        viable.append((c, spread_pct))

    if not viable:
        return None
    # choose the most liquid (lowest spread pct)
    viable.sort(key=lambda t: (t[1], _strike_distance(t[0])))
    return viable[0][0]
