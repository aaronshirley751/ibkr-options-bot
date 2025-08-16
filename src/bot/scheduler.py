import time
from datetime import datetime, time as dtime, date as ddate
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from zoneinfo import ZoneInfo
import traceback
from . import log as _log
logger = _log.logger

from .strategy.scalp_rules import scalp_signal
from .strategy.whale_rules import whale_rules
from .risk import position_size, should_stop_trading_today
from .execution import build_bracket, emulate_oco, is_liquid
from .journal import log_trade
from .data.options import pick_weekly_option
from .monitoring import send_heartbeat, alert_all


# Runs a job every `interval_seconds` during regular trading hours (09:30-16:00 ET)
# Note: consider adding US holiday calendar and pre/post-market handling


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
        cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
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


def run_cycle(broker, settings: Dict[str, Any]):
    """One scheduler cycle: fetch bars, compute signals, and optionally submit orders."""
    symbols = settings.get("symbols", [])

    # Ensure broker access is serialized unless the implementation is known to be thread-safe
    broker_lock = getattr(broker, "_thread_lock", None)
    if broker_lock is None:
        broker_lock = Lock()

    def _with_broker_lock(fn, *args, **kwargs):
        with broker_lock:
            return fn(*args, **kwargs)

    def process_symbol(symbol: str):
        try:
            # Check daily loss guard once per cycle; if triggered, skip new entries
            loss_guard = should_stop_trading_today(broker, settings.get("risk", {}).get("max_daily_loss_pct", 0.15))
            if loss_guard:
                logger.warning("Daily loss guard active; skipping new positions")
                # Alert once per trading day
                ny = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York"))
                if _LOSS_ALERTED_DATE["date"] != ny.date():
                    alert_all(settings, f"Daily loss limit breached. Pausing new entries for {ny.date()}.")
                    _LOSS_ALERTED_DATE["date"] = ny.date()
                return
            # fetch recent 1-min bars; try multiple broker methods
            bars = None
            if hasattr(broker, "historical_prices"):
                bars = _with_broker_lock(broker.historical_prices, symbol)
            elif hasattr(broker, "market_data"):
                # market_data may return historical bars or a snapshot Quote
                try:
                    bars = _with_broker_lock(broker.market_data, symbol)
                except Exception:  # pylint: disable=broad-except
                    bars = None

            df1 = _to_df(bars) if bars is not None else []
            # Proceed only if we have a pandas DataFrame; else skip this symbol gracefully
            is_df = False
            try:
                import importlib

                pd = importlib.import_module("pandas")  # type: ignore
                is_df = isinstance(df1, pd.DataFrame)
            except Exception:  # pylint: disable=broad-except
                is_df = False

            if not is_df:
                count = len(df1) if hasattr(df1, "__len__") else 0
                logger.bind(event="insufficient_bars", symbol=symbol, bars=count).info(
                    "Skipping: insufficient bars (no pandas)"
                )
                return

            bars_len = len(df1) if hasattr(df1, "__len__") else 0
            if bool(getattr(df1, "empty", False)) or bars_len < 30:
                logger.bind(event="insufficient_bars", symbol=symbol, bars=bars_len).info(
                    "Skipping: insufficient bars"
                )
                return

            # compute scalp signal on 1-min bars
            scalp = scalp_signal(df1)  # type: ignore[arg-type]

            # compute whale on 60-min resample (if requested)
            whale = {"signal": "HOLD", "confidence": 0.0}
            if settings.get("mode") in ("hybrid", "growth"):
                resample = getattr(df1, "resample", None)
                if callable(resample):
                    res = resample("60T", label="right", closed="right")
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
                )
                if not opt:
                    logger.bind(event="skip", symbol=symbol, reason="no_viable_option").info(
                        "Skipping: no viable option"
                    )
                    return

                # get option premium
                q = None
                try:
                    q = _with_broker_lock(broker.market_data, getattr(opt, "symbol", opt))
                    premium = getattr(q, "last", 0.0)
                except Exception:  # pylint: disable=broad-except
                    premium = 0.0

                cfg_risk = settings.get("risk", {})
                equity = _with_broker_lock(broker.pnl).get("net", 100000.0)
                size = position_size(equity, cfg_risk.get("max_risk_pct_per_trade", 0.01), cfg_risk.get("stop_loss_pct", 0.2), premium or 0.0)
                if size <= 0:
                    logger.bind(event="skip", symbol=symbol, reason="size_zero").info(
                        "Skipping: size zero"
                    )
                    return

                # check liquidity
                # Re-check liquidity guard with same thresholds
                if q is None or not is_liquid(q, cfg_opts.get("max_spread_pct", 2.0), cfg_opts.get("min_volume", 100)):
                    logger.bind(event="skip", symbol=symbol, reason="illiquid").info(
                        "Skipping: illiquid contract"
                    )
                    return

                # build bracket
                bracket = build_bracket(premium, cfg_risk.get("take_profit_pct"), cfg_risk.get("stop_loss_pct"))

                # submit order via broker.place_order using OrderTicket dataclass
                from .broker.base import OrderTicket

                ticket = OrderTicket(contract=opt, action=("BUY" if action.startswith("BUY") else "SELL"), quantity=size, order_type="MKT", take_profit_pct=cfg_risk.get("take_profit_pct"), stop_loss_pct=cfg_risk.get("stop_loss_pct"))
                if settings.get("dry_run"):
                    logger.bind(event="dry_run", symbol=symbol, ticket=ticket.__dict__).info("Dry-run: would place order")
                    order_id = "DRYRUN"
                else:
                    order_id = _with_broker_lock(broker.place_order, ticket)

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
                    trade = {"timestamp": datetime.utcnow().isoformat(), "symbol": symbol, "action": ticket.action, "quantity": size, "price": premium, "stop": bracket.get("stop_loss"), "target": bracket.get("take_profit"), "contract": getattr(opt, "symbol", None)}
                    log_trade(trade)

        except Exception:  # pylint: disable=broad-except
            err = traceback.format_exc()
            logger.error("Error during run_cycle for %s:\n%s", symbol, err)
            try:
                alert_all(settings, f"run_cycle error for {symbol}: see logs for details.")
            except Exception:  # pylint: disable=broad-except
                pass

    # concurrency: process symbols in a limited thread pool
    max_workers = int(settings.get("schedule", {}).get("max_concurrent_symbols", 2) or 1)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_symbol, sym): sym for sym in symbols}
        for _ in as_completed(futures):
            pass


def run_scheduler(broker, settings: Dict[str, Any]):
    interval_seconds = settings.get("schedule", {}).get("interval_seconds", 180)
    last_day = None
    while True:
        now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        if is_rth(now):
            try:
                # Heartbeat at start of each active cycle
                hb = settings.get("monitoring", {}).get("heartbeat_url")
                send_heartbeat(hb)
                run_cycle(broker, settings)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Scheduler cycle failed")
            last_day = now.date()
        else:
            # if we just ended a trading day, emit a simple summary placeholder
            if last_day is not None and now.date() != last_day:
                logger.bind(event="eod_summary").info("End of day summary emitted (stub)")
                # Reset daily loss alert flag for the new day
                _LOSS_ALERTED_DATE["date"] = None
                last_day = None
        time.sleep(interval_seconds)
