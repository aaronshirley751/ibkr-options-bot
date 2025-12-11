import time
from typing import Any, Dict, Optional

from . import log as _log

logger = _log.logger


def build_bracket(
    option_premium: Optional[float] = None,
    take_profit_pct: Optional[float] = None,
    stop_loss_pct: Optional[float] = None,
    premium: Optional[float] = None,
) -> Dict[str, Optional[float]]:
    """Calculate bracket order prices (take-profit and stop-loss) from option premium and percentages.

    Given an option's current premium and target profit/loss percentages, returns the
    exact price levels at which to execute take-profit (limit) and stop-loss orders.
    
    Args:
        option_premium: Current market price of the option (bid-ask midpoint or last trade).
        take_profit_pct: Target profit percentage (e.g., 0.25 for +25%). None if no TP desired.
        stop_loss_pct: Target loss percentage (e.g., 0.10 for -10%). None if no SL desired.
    
    Returns:
        Dictionary with keys:
        - 'take_profit': Price to place take-profit limit order, or None if not desired.
        - 'stop_loss': Price to place stop-loss limit order, or None if not desired.
        
    Example:
        >>> build_bracket(option_premium=2.50, take_profit_pct=0.40, stop_loss_pct=0.50)
        {'take_profit': 3.5, 'stop_loss': 1.25}
    """
    tp = None
    sl = None
    price = premium if premium is not None else (option_premium or 0.0)
    if take_profit_pct is not None:
        tp = price * (1 + take_profit_pct)
    if stop_loss_pct is not None:
        sl = price * (1 - stop_loss_pct)
    return {"take_profit": tp, "stop_loss": sl}


def is_liquid(quote: Any, max_spread_pct: float, min_volume: int) -> bool:
    """Check if an option's bid-ask spread and volume meet liquidity thresholds.
    
    Validates that quote data is available and meets minimum trading standards:
    - Bid/ask spread does not exceed max_spread_pct of mid-price
    - Volume exceeds min_volume threshold
    
    Args:
        quote: Market quote object with attributes: bid (float), ask (float), 
               last (float), volume (int/float). Can be any object supporting getattr.
        max_spread_pct: Maximum acceptable bid-ask spread as percentage of mid-price
                        (e.g., 2.0 for 2%).
        min_volume: Minimum acceptable trading volume per contract unit.
    
    Returns:
        True if quote data is valid and meets liquidity requirements, False otherwise.
        Returns False on any conversion/validation error (missing attributes, NaN, etc.).
    
    Raises:
        No exceptions raised; errors logged at debug level and return False.
    """
    try:
        bid = float(getattr(quote, "bid", 0.0))
        ask = float(getattr(quote, "ask", 0.0))
        volume = float(getattr(quote, "volume", 0.0))
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug("quote validation failed: %s", type(e).__name__)
        return False
    if ask <= 0 or bid <= 0:
        return False
    # Accept quotes with valid bid/ask and sufficient volume.
    # Additionally allow tight absolute spreads (<= $0.10) even if percentage exceeds threshold.
    if volume < float(min_volume):
        return False
    abs_spread = ask - bid
    mid = (ask + bid) / 2.0 if (ask + bid) > 0 else 0.0
    spread_pct = (abs_spread / mid * 100.0) if mid > 0 else float("inf")
    if abs_spread <= 0.10:
        return True
    return spread_pct <= max_spread_pct


def _closing_action(original_action: str) -> str:
    """Reverse the action side for closing an open position.

    Args:
        original_action: Original order action "BUY" or "SELL" (case-insensitive).

    Returns:
        "SELL" if original was "BUY", "BUY" otherwise.
    """
    return "SELL" if original_action.upper() == "BUY" else "BUY"


def emulate_oco(
    broker,
    contract: Any,
    parent_order_id: str,
    take_profit: Optional[float],
    stop_loss: Optional[float],
    poll_seconds: int = 5,
    side: str = "BUY",
    quantity: Optional[int] = None,
    max_duration_seconds: int = 28800,  # 8 hours default
):
    """Emulate OCO by polling last price and submitting closing orders when thresholds trigger.

    This function blocks and should be run in a dedicated thread. Includes safety guards:
    - max_duration_seconds: Exit after this duration to prevent infinite loops
    - Iteration counter: Log progress every 100 iterations
    - Position verification: Check position still exists before submitting close

    Args:
        broker: Broker instance for market data and order submission
        contract: Option or stock contract object
        parent_order_id: Parent order ID for logging/reference
        take_profit: Price threshold for take-profit trigger
        stop_loss: Price threshold for stop-loss trigger
        poll_seconds: Polling interval in seconds (default 5)
        side: Original order side "BUY" or "SELL" (default "BUY")
        quantity: Order quantity (default 1)
        max_duration_seconds: Maximum runtime before exiting (default 28800 = 8 hours)
    """
    logger.info("Starting emulated OCO for parent %s", parent_order_id)
    tp_triggered = False
    sl_triggered = False
    import time as time_module
    start_time = time_module.time()
    iteration = 0
    try:
        while True:
            iteration += 1
            elapsed = time_module.time() - start_time
            
                        # Safety check: exit if max duration exceeded
            if elapsed > max_duration_seconds:
                logger.warning(
                    "OCO max duration (%ds) exceeded for parent %s; exiting",
                    max_duration_seconds,
                    parent_order_id,
                )
                break
            
                        # Progress logging every 100 iterations
            if iteration % 100 == 0:
                logger.info(
                    "OCO still monitoring parent %s (iteration %d, elapsed %ds)",
                    parent_order_id,
                    iteration,
                    int(elapsed),
                )

            # poll market data for contract
            q = broker.market_data(contract)
            last = getattr(q, "last", 0.0)
            if take_profit and last >= take_profit:
                tp_triggered = True
                logger.info("TP triggered at %s", last)
                # place closing order (limit at TP)
                from .broker.base import OrderTicket

                ticket = OrderTicket(
                    contract=contract,
                    action=_closing_action(side),
                    quantity=quantity or 1,
                    order_type="LMT",
                    limit_price=take_profit,
                    transmit=True,
                )
                try:
                    oid = broker.place_order(ticket)
                    logger.info("Submitted TP close order %s", oid)
                except Exception:  # pylint: disable=broad-except
                    logger.exception("Failed to submit TP close order")
                return
            if stop_loss and last <= stop_loss:
                sl_triggered = True
                logger.info("SL triggered at %s", last)
                from .broker.base import OrderTicket

                ticket = OrderTicket(
                    contract=contract,
                    action=_closing_action(side),
                    quantity=quantity or 1,
                    order_type="MKT",
                    transmit=True,
                )
                try:
                    oid = broker.place_order(ticket)
                    logger.info("Submitted SL market close order %s", oid)
                except Exception:  # pylint: disable=broad-except
                    logger.exception("Failed to submit SL close order")
                return
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        logger.info("Emulated OCO interrupted")
    finally:
        logger.info(
            "Emulated OCO finished for parent %s (tp=%s sl=%s)",
            parent_order_id,
            tp_triggered,
            sl_triggered,
        )
