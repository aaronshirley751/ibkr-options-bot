from datetime import datetime, timedelta
from typing import Dict, Optional


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


def pick_option(chain: Dict, last_price: float, direction: str = "CALL") -> Dict:
    # chain: {'expirations': [...], 'strikes': [...]}
    expiry = nearest_friday(datetime.utcnow())
    strikes = chain.get('strikes', [])
    atm = nearest_atm_strike(last_price, strikes)
    return {"expiry": expiry.isoformat(), "strike": atm, "type": direction}
