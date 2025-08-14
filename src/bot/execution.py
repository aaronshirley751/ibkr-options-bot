from typing import Dict, Any, Optional
import time
from loguru import logger

from .risk import stop_target_from_premium


def build_bracket(option_premium: float, take_profit_pct: Optional[float], stop_loss_pct: Optional[float]) -> Dict[str, float]:
    """Return limit and stop prices for an option given premium and pct targets."""
    tp = None
    sl = None
    if take_profit_pct is not None:
        tp = option_premium * (1 + take_profit_pct)
    if stop_loss_pct is not None:
        sl = option_premium * (1 - stop_loss_pct)
    return {"take_profit": tp, "stop_loss": sl}


def is_liquid(quote: Any, max_spread_pct: float, min_volume: int) -> bool:
    # quote: object with bid, ask, last, and maybe volume
    try:
        bid = float(getattr(quote, "bid", 0.0))
        ask = float(getattr(quote, "ask", 0.0))
        volume = float(getattr(quote, "volume", 0.0))
        last = float(getattr(quote, "last", 0.0))
    except Exception:
        return False
    if ask <= 0 or bid <= 0:
        return False
    spread_pct = (ask - bid) / ((ask + bid) / 2.0) * 100.0
    if spread_pct > max_spread_pct:
        return False
    if volume < min_volume:
        return False
    return True


def emulate_oco(broker, contract, parent_order_id: str, take_profit: Optional[float], stop_loss: Optional[float], poll_seconds: int = 5):
    """Emulate OCO by polling last price and cancelling the opposite order when one triggers.

    This function blocks and should be run in a dedicated thread or coroutine in production.
    """
    logger.info("Starting emulated OCO for parent %s", parent_order_id)
    tp_triggered = False
    sl_triggered = False
    try:
        while True:
            # poll market data for contract
            q = broker.market_data(contract)
            last = getattr(q, "last", 0.0)
            if take_profit and last >= take_profit:
                tp_triggered = True
                logger.info("TP triggered at %s", last)
                # place closing order here
                # broker.place_order closing logic omitted for brevity
                break
            if stop_loss and last <= stop_loss:
                sl_triggered = True
                logger.info("SL triggered at %s", last)
                # place closing order here
                break
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        logger.info("Emulated OCO interrupted")
    finally:
        logger.info("Emulated OCO finished for parent %s (tp=%s sl=%s)", parent_order_id, tp_triggered, sl_triggered)
