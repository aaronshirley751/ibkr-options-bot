import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date as ddate
from datetime import datetime
from datetime import time as dtime
from datetime import timezone
from threading import Event, Lock
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from . import log as _log

logger = _log.logger

from .data.options import pick_weekly_option
from .execution import build_bracket, emulate_oco, is_liquid
from .journal import log_trade
from .monitoring import alert_all, send_heartbeat, trade_alert
from .risk import position_size, should_stop_trading_today
from .strategy.scalp_rules import scalp_signal
from .strategy.whale_rules import whale_rules

# Runs a job every `interval_seconds` during regular trading hours (09:30-16:00 ET)
# Note: consider adding US holiday calendar and pre/post-market handling


class GatewayCircuitBreaker:
    """Detect and prevent cascading failures from sustained Gateway issues.
    
    After N consecutive failures, opens circuit to prevent overwhelming Gateway
    with retry requests. Allows periodic recovery attempts (half-open state).
    """
    
    def __init__(self, failure_threshold: int = 3, reset_timeout_seconds: int = 300):
        self.failures = 0
        self.threshold = failure_threshold
        self.state = "CLOSED"  # CLOSED=healthy, OPEN=tripped, HALF_OPEN=testing
        self.last_failure_time = 0
        self.reset_timeout = reset_timeout_seconds
    
    def record_failure(self):
        """Record a failure and update circuit state."""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold:
            self.state = "OPEN"
            logger.warning("GatewayCircuitBreaker OPEN: %d consecutive failures", self.failures)
    
    def record_success(self):
        """Record a success and reset circuit."""
        if self.failures > 0:
            logger.info("GatewayCircuitBreaker reset after %d failures", self.failures)
        self.failures = 0
        self.state = "CLOSED"
    
    def should_attempt(self) -> bool:
        """Determine if operation should be attempted based on circuit state."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            # Allow recovery attempt after timeout
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.reset_timeout:
                self.state = "HALF_OPEN"
                logger.info("GatewayCircuitBreaker HALF_OPEN: attempting recovery")
                return True
            return False
        else:  # HALF_OPEN
            return True  # Allow recovery attempt


_gateway_circuit_breaker = GatewayCircuitBreaker(failure_threshold=3, reset_timeout_seconds=300)



def is_rth(now_utc: datetime) -> bool:
    ny = now_utc.astimezone(ZoneInfo("America/New_York"))
    start = dtime(hour=9, minute=30)
    end = dtime(hour=16, minute=0)
    return start <= ny.time() <= end


def _to_df(bars_iter) -> Any:
    """Convert an iterable of bar dicts to pandas DataFrame if possible."""
    try:
        import importlib

        pd = importlib.import_module("pandas")  # type: ignore
        df = pd.DataFrame(bars_iter)
        if df.empty:
            return df
        # ensure columns
        cols = [
            c for c in ["open", "high", "low", "close", "volume"] if c in df.columns
        ]
        if not cols:
            return importlib.import_module("pandas").DataFrame()  # type: ignore
        # Always produce a DataFrame even if a single column
        subset = df.loc[:, cols if len(cols) > 1 else [cols[0]]]
        subset_df = importlib.import_module("pandas").DataFrame(subset)  # type: ignore
        return subset_df.copy()
    except Exception:  # pylint: disable=broad-except
        try:
            import importlib

            return importlib.import_module("pandas").DataFrame()  # type: ignore
        except Exception:  # pylint: disable=broad-except
            return []


_LOSS_ALERTED_DATE: Dict[str, Optional[ddate]] = {"date": None}
_loss_alert_lock = Lock()

# Track consecutive historical data timeouts per symbol for backoff logic
_timeout_tracker: Dict[str, int] = {}  # symbol -> consecutive timeout count
_TIMEOUT_BACKOFF_THRESHOLD = 3  # Skip after N consecutive timeouts
_TIMEOUT_BACKOFF_CYCLES = 2  # Skip for M cycles after threshold hit

# Request throttling: add delay between symbol processing to prevent Gateway buffer overflow
_LAST_REQUEST_TIME: Dict[str, float] = {}  # symbol -> last request timestamp
_REQUEST_THROTTLE_DELAY = 0.2  # 200ms delay between symbol requests (prevents 1.3MB+ buffers)
_throttle_lock = Lock()  # Thread-safe access to _LAST_REQUEST_TIME


def run_cycle(broker, settings: Dict[str, Any]):
    """One scheduler cycle: fetch bars, compute signals, and optionally submit orders."""
    cycle_start = time.time()
    symbols = settings.get("symbols", [])

    # Ensure broker access is serialized unless the implementation is known to be thread-safe
    broker_lock = getattr(broker, "_thread_lock", None)
    if broker_lock is None:
        broker_lock = Lock()

    def _with_broker_lock(fn, *args, **kwargs):
        # Ensure event loop exists in calling thread (for ib_insync calls from worker threads)
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        
        with broker_lock:
            return fn(*args, **kwargs)

    historical_cfg = settings.get("historical", {})
    hist_duration = historical_cfg.get("duration", "3600 S")  # Default to 1 hour (was 7200 S)
    hist_use_rth = bool(historical_cfg.get("use_rth", True))  # Default to RTH (was False)
    hist_bar_size = historical_cfg.get("bar_size", "1 min")
    hist_what = historical_cfg.get("what_to_show", "TRADES")
    # Calculate timeout based on duration: ~1.5 seconds per minute of data requested
    duration_seconds = int(hist_duration.split()[0])
    hist_timeout = historical_cfg.get("timeout", max(60, duration_seconds // 40 + 30))

    def process_symbol(symbol: str):
        try:
            # Check circuit breaker: if Gateway has failed consistently, skip this cycle
            if not _gateway_circuit_breaker.should_attempt():
                logger.bind(
                    symbol=symbol,
                    event="circuit_breaker_open",
                    circuit_state=_gateway_circuit_breaker.state,
                ).warning("Skipping symbol; circuit breaker is OPEN (Gateway recovery in progress)")
                return
            
            # Throttle requests: 200ms delay between symbols to prevent Gateway EBuffer overflow
            # Use lock for thread-safe access when max_concurrent_symbols > 1
            with _throttle_lock:
                last_req = _LAST_REQUEST_TIME.get(symbol, 0)
                elapsed = time.time() - last_req
                if elapsed < _REQUEST_THROTTLE_DELAY:
                    time.sleep(_REQUEST_THROTTLE_DELAY - elapsed)
                _LAST_REQUEST_TIME[symbol] = time.time()

            # Check backoff: skip symbol if it's in timeout backoff period
            if symbol in _timeout_tracker:
                timeout_count = _timeout_tracker[symbol]
                if timeout_count >= _TIMEOUT_BACKOFF_THRESHOLD:
                    # Decrement backoff counter
                    _timeout_tracker[symbol] = timeout_count - 1
                    if _timeout_tracker[symbol] <= 0:
                        del _timeout_tracker[symbol]
                        logger.bind(symbol=symbol, event="backoff_cleared").info(
                            "Historical data backoff cleared; will retry next cycle"
                        )
                    else:
                        logger.bind(
                            symbol=symbol,
                            event="backoff_skip",
                            remaining_cycles=_timeout_tracker[symbol],
                        ).info(
                            "Skipping due to historical data backoff ({}  remaining)",
                            _timeout_tracker[symbol],
                        )
                    return

            # Ensure broker is connected before processing
            if hasattr(broker, "is_connected") and callable(getattr(broker, "is_connected")):
                if not broker.is_connected():
                    logger.warning("Broker disconnected; attempting reconnection for {}", symbol)
                    try:
                        broker.connect()
                        logger.info("Broker reconnected successfully")
                    except Exception as conn_err:  # pylint: disable=broad-except
                        logger.error(
                            "Failed to reconnect broker: {}: {}",
                            type(conn_err).__name__,
                            str(conn_err),
                        )
                        return
            # Check daily loss guard once per cycle; if triggered, skip new entries
            loss_guard = should_stop_trading_today(
                broker, settings.get("risk", {}).get("max_daily_loss_pct", 0.15)
            )
            if loss_guard:
                logger.warning("Daily loss guard active; skipping new positions")
                # Alert once per trading day
                ny = (
                    datetime.now(timezone.utc)
                    .replace(tzinfo=ZoneInfo("UTC"))
                    .astimezone(ZoneInfo("America/New_York"))
                )
                with _loss_alert_lock:
                    if _LOSS_ALERTED_DATE["date"] != ny.date():
                        alert_all(
                            settings,
                            f"Daily loss limit breached. Pausing new entries for {ny.date()}.",
                        )
                        _LOSS_ALERTED_DATE["date"] = ny.date()
                return
            # fetch recent 1-min bars; try multiple broker methods
            bars = None
            data_fetch_failed = False
            try:
                if hasattr(broker, "historical_prices"):
                    logger.debug(
                        "Requesting historical data: symbol={}, duration={}, use_rth={}, timeout={}",
                        symbol, hist_duration, hist_use_rth, hist_timeout
                    )
                    bars = _with_broker_lock(
                        broker.historical_prices,
                        symbol,
                        duration=hist_duration,
                        bar_size=hist_bar_size,
                        what_to_show=hist_what,
                        use_rth=hist_use_rth,
                        timeout=hist_timeout,  # NEW: Pass timeout parameter
                    )
                elif hasattr(broker, "market_data"):
                    # market_data may return historical bars or a snapshot Quote
                    try:
                        bars = _with_broker_lock(broker.market_data, symbol)
                    except (ConnectionError, TimeoutError, AttributeError) as e:
                        logger.debug("market_data failed for %s: %s", symbol, type(e).__name__)
                        bars = None
                        data_fetch_failed = True
            except (TimeoutError, Exception) as fetch_err:  # pylint: disable=broad-except
                logger.bind(
                    symbol=symbol,
                    event="historical_data_timeout",
                    error=str(fetch_err),
                ).warning("Historical data fetch failed: {}", type(fetch_err).__name__)
                data_fetch_failed = True
                bars = None
                # Record failure to circuit breaker for Gateway health detection
                _gateway_circuit_breaker.record_failure()

            df1 = _to_df(bars) if bars is not None else []
            # Proceed only if we have a pandas DataFrame; else skip this symbol gracefully
            is_df = False
            try:
                import importlib

                pd = importlib.import_module("pandas")  # type: ignore
                is_df = isinstance(df1, pd.DataFrame)
            except ImportError as e:
                logger.debug("pandas import failed: %s", type(e).__name__)
                is_df = False

            logger.bind(symbol=symbol, event="data_check").info(
                "[DEBUG] After fetch: bars type={}, is_df={}, df_shape={}",
                type(df1).__name__ if df1 is not None else "None",
                is_df,
                df1.shape if is_df else "N/A"
            )

            if not is_df:
                count = len(df1) if hasattr(df1, "__len__") else 0
                logger.bind(event="insufficient_bars", symbol=symbol, bars=count).info(
                    "Skipping: insufficient bars (no pandas)"
                )
                # Increment timeout counter if fetch failed
                if data_fetch_failed:
                    _timeout_tracker[symbol] = _timeout_tracker.get(symbol, 0) + 1
                    if _timeout_tracker[symbol] >= _TIMEOUT_BACKOFF_THRESHOLD:
                        logger.bind(
                            symbol=symbol,
                            consecutive_failures=_timeout_tracker[symbol],
                        ).warning(
                            "Historical data fetch failed {} times; entering backoff (skip {} cycles)",
                            _timeout_tracker[symbol],
                            _TIMEOUT_BACKOFF_CYCLES,
                        )
                        if settings.get("risk", {}).get("data_loss_exit_on_backoff", True):
                            try:
                                open_positions = _with_broker_lock(broker.positions)
                            except Exception:  # pylint: disable=broad-except
                                open_positions = []
                            alert_all(
                                settings,
                                f"Data unavailable for {symbol} in {_timeout_tracker[symbol]} consecutive attempts; entering backoff and recommending manual exit check. Positions: {open_positions}",
                            )
                        _timeout_tracker[symbol] = _TIMEOUT_BACKOFF_CYCLES
                return

            bars_len = len(df1) if hasattr(df1, "__len__") else 0
            if bool(getattr(df1, "empty", False)) or bars_len < 30:
                logger.bind(
                    event="insufficient_bars", symbol=symbol, bars=bars_len
                ).info("Skipping: insufficient bars")
                # Increment timeout counter if we have no bars
                if bars_len == 0 or data_fetch_failed:
                    _timeout_tracker[symbol] = _timeout_tracker.get(symbol, 0) + 1
                    if _timeout_tracker[symbol] >= _TIMEOUT_BACKOFF_THRESHOLD:
                        logger.bind(
                            symbol=symbol,
                            consecutive_failures=_timeout_tracker[symbol],
                        ).warning(
                            "Historical data unavailable {} times; entering backoff (skip {} cycles)",
                            _timeout_tracker[symbol],
                            _TIMEOUT_BACKOFF_CYCLES,
                        )
                        if settings.get("risk", {}).get("data_loss_exit_on_backoff", True):
                            try:
                                open_positions = _with_broker_lock(broker.positions)
                            except Exception:  # pylint: disable=broad-except
                                open_positions = []
                            alert_all(
                                settings,
                                f"Data unavailable for {symbol} in {_timeout_tracker[symbol]} consecutive attempts; entering backoff and recommending manual exit check. Positions: {open_positions}",
                            )
                        _timeout_tracker[symbol] = _TIMEOUT_BACKOFF_CYCLES
                return

            # Success: clear timeout counter for this symbol
            if symbol in _timeout_tracker:
                logger.bind(symbol=symbol, event="data_recovered").info(
                    "Historical data fetch successful; clearing timeout counter"
                )
                del _timeout_tracker[symbol]

            # compute scalp signal on 1-min bars
            scalp = scalp_signal(df1)  # type: ignore[arg-type]

            # compute whale on 60-min resample (if requested)
            whale = {"signal": "HOLD", "confidence": 0.0}
            if settings.get("mode") in ("hybrid", "growth"):
                resample = getattr(df1, "resample", None)
                if callable(resample):
                    res = resample("60min", label="right", closed="right")
                    agg = getattr(res, "agg", None)
                    if callable(agg):
                        df60 = agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})  # type: ignore[call-arg]
                        whale = whale_rules(df60, symbol)  # type: ignore[arg-type]

            # decide final action
            action = scalp.get("signal", "HOLD")
            if whale.get("signal", "HOLD") != "HOLD":
                action = whale["signal"]

            logger.bind(
                event="signal",
                symbol=symbol,
                scalp=scalp,
                whale=whale,
                action=action,
            ).info("Cycle decision")

            if action in ("BUY", "SELL", "BUY_CALL", "BUY_PUT"):
                # pick option using refined selection
                direction = "C" if action.startswith("BUY") else "P"
                last_under_q = _with_broker_lock(broker.market_data, symbol)
                last_under = getattr(last_under_q, "last", 0.0)
                cfg_opts = settings.get("options", {})
                opt = pick_weekly_option(
                    broker,
                    underlying=symbol,
                    right=direction,
                    last_price=last_under,
                    moneyness=cfg_opts.get("moneyness", "atm"),
                    min_volume=cfg_opts.get("min_volume", 100),
                    max_spread_pct=cfg_opts.get("max_spread_pct", 2.0),
                    strike_count=cfg_opts.get("strike_count", 3),
                )
                if not opt:
                    logger.bind(
                        event="skip", symbol=symbol, reason="no_viable_option"
                    ).info("Skipping: no viable option")
                    return

                # get option premium
                q = None
                try:
                    q = _with_broker_lock(
                        broker.market_data, getattr(opt, "symbol", opt)
                    )
                    premium = getattr(q, "last", 0.0)
                except (ConnectionError, TimeoutError, AttributeError, ValueError) as e:
                    logger.debug("market_data failed for option: %s", type(e).__name__)
                    premium = 0.0

                cfg_risk = settings.get("risk", {})
                equity = _with_broker_lock(broker.pnl).get("net", 100000.0)
                size = position_size(
                    equity,
                    cfg_risk.get("max_risk_pct_per_trade", 0.01),
                    cfg_risk.get("stop_loss_pct", 0.2),
                    premium or 0.0,
                )
                if size <= 0:
                    logger.bind(event="skip", symbol=symbol, reason="size_zero").info(
                        "Skipping: size zero"
                    )
                    return

                # check liquidity
                # Re-check liquidity guard with same thresholds
                if q is None or not is_liquid(
                    q,
                    cfg_opts.get("max_spread_pct", 2.0),
                    cfg_opts.get("min_volume", 100),
                ):
                    logger.bind(event="skip", symbol=symbol, reason="illiquid").info(
                        "Skipping: illiquid contract"
                    )
                    return

                # build bracket
                bracket = build_bracket(
                    premium,
                    cfg_risk.get("take_profit_pct"),
                    cfg_risk.get("stop_loss_pct"),
                )

                # submit order via broker.place_order using OrderTicket dataclass
                from .broker.base import OrderTicket

                ticket = OrderTicket(
                    contract=opt,
                    action=("BUY" if action.startswith("BUY") else "SELL"),
                    quantity=size,
                    order_type="MKT",
                    take_profit_pct=cfg_risk.get("take_profit_pct"),
                    stop_loss_pct=cfg_risk.get("stop_loss_pct"),
                )
                if settings.get("dry_run"):
                    logger.bind(
                        event="dry_run", symbol=symbol, ticket=ticket.__dict__
                    ).info("Dry-run: would place order")
                    order_id = "DRYRUN"
                else:
                    order_id = _with_broker_lock(broker.place_order, ticket)

                # Send entry alert with P/L placeholder for both live and dry-run
                trade_alert(
                    settings,
                    stage="Entry",
                    symbol=getattr(opt, "symbol", symbol),
                    action=ticket.action,
                    quantity=size,
                    price=float(premium or 0.0),
                    order_id=str(order_id) if order_id is not None else None,
                    pnl=None,
                )

                # if broker doesn't support native OCO, emulate
                # run emulate_oco in background thread
                import threading

                if bracket.get("take_profit") or bracket.get("stop_loss"):
                    t = threading.Thread(
                        target=emulate_oco,
                        args=(
                            broker,
                            opt,
                            order_id,
                            bracket.get("take_profit"),
                            bracket.get("stop_loss"),
                            settings.get("schedule", {}).get("interval_seconds", 180),
                            ticket.action,
                            ticket.quantity,
                        ),
                        daemon=True,
                    )
                    t.start()

                # log trade
                if not settings.get("dry_run"):
                    trade = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "symbol": symbol,
                        "action": ticket.action,
                        "quantity": size,
                        "price": premium,
                        "stop": bracket.get("stop_loss"),
                        "target": bracket.get("take_profit"),
                        "contract": getattr(opt, "symbol", None),
                    }
                    log_trade(trade)
                    # Record successful cycle to circuit breaker
                    _gateway_circuit_breaker.record_success()

        except (ConnectionError, TimeoutError, ValueError, RuntimeError) as e:
            logger.exception("symbol processing failed: %s", type(e).__name__)
            # Record error to circuit breaker
            _gateway_circuit_breaker.record_failure()
        except Exception as e:
            logger.exception("unexpected error during symbol processing: %s", type(e).__name__)
            # Record unexpected error to circuit breaker
            _gateway_circuit_breaker.record_failure()
            try:
                alert_all(settings, f"symbol processing error for {symbol}: see logs")
            except Exception as e:
                logger.debug("alert_all failed: %s", type(e).__name__)

    # concurrency: process symbols in a limited thread pool
    max_workers = int(
        settings.get("schedule", {}).get("max_concurrent_symbols", 2) or 1
    )
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_symbol, sym): sym for sym in symbols}
        for _ in as_completed(futures):
            pass

    # Emit end-of-cycle event for monitoring/analytics
    duration = round(time.time() - cycle_start, 3)
    try:
        logger.bind(
            event="cycle_complete",
            symbols=len(symbols),
            duration_seconds=duration,
            circuit_state=_gateway_circuit_breaker.state,
        ).info("Cycle complete: {} symbols in {:.2f}s", len(symbols), duration)
    except Exception:
        # Don't let logging issues disrupt scheduling
        logger.debug("cycle_complete logging failed")


def run_scheduler(broker, settings: Dict[str, Any], stop_event: Optional[Event] = None):
    interval_seconds = settings.get("schedule", {}).get("interval_seconds", 180)
    last_day = None
    while True:
        if stop_event and stop_event.is_set():
            logger.info("Stop requested; exiting scheduler loop")
            break

        now = datetime.now(timezone.utc).replace(tzinfo=ZoneInfo("UTC"))
        if is_rth(now):
            try:
                # Heartbeat at start of each active cycle
                hb = settings.get("monitoring", {}).get("heartbeat_url")
                send_heartbeat(hb)
                run_cycle(broker, settings)
            except (ConnectionError, TimeoutError, ValueError, RuntimeError) as e:
                logger.exception("scheduler cycle failed: %s", type(e).__name__)
            except Exception as e:
                logger.exception("unexpected scheduler error: %s", type(e).__name__)
            last_day = now.date()
        else:
            # if we just ended a trading day, emit a simple summary placeholder
            if last_day is not None and now.date() != last_day:
                logger.bind(event="eod_summary").info(
                    "End of day summary emitted (stub)"
                )
                # Reset daily loss alert flag for the new day
                _LOSS_ALERTED_DATE["date"] = None
                last_day = None

        if stop_event:
            # Wait with interruptible sleep so signals are honored promptly
            if stop_event.wait(interval_seconds):
                logger.info("Stop requested during sleep; exiting scheduler loop")
                break
        else:
            time.sleep(interval_seconds)
