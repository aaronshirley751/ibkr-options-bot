import time
from datetime import datetime, time as dtime
from typing import Callable, Dict, Any
from zoneinfo import ZoneInfo
import traceback
import pandas as pd
from loguru import logger

from .strategy.scalp_rules import scalp_signal
from .strategy.whale_rules import whale_rules
from .risk import position_size, should_stop_trading_today
from .execution import build_bracket, emulate_oco, is_liquid
from .journal import log_trade
from .data.options import pick_weekly_option


# Runs a job every `interval_seconds` during regular trading hours (09:30-16:00 ET)
# TODO: add US holiday calendar and pre/post-market handling


def is_rth(now_utc: datetime) -> bool:
    ny = now_utc.astimezone(ZoneInfo("America/New_York"))
    start = dtime(hour=9, minute=30)
    end = dtime(hour=16, minute=0)
    return start <= ny.time() <= end


def _to_df(bars_iter) -> pd.DataFrame:
    """Convert an iterable of bar dicts to pandas DataFrame if possible."""
    try:
        df = pd.DataFrame(bars_iter)
        if df.empty:
            return df
        # ensure columns
        cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        if not cols:
            return pd.DataFrame()
        # Always produce a DataFrame even if a single column
        subset = df.loc[:, cols if len(cols) > 1 else [cols[0]]]
        subset_df = pd.DataFrame(subset)
        return subset_df.copy()
    except Exception:
        return pd.DataFrame()


def run_cycle(broker, settings: Dict[str, Any]):
    """One scheduler cycle: fetch bars, compute signals, and optionally submit orders."""
    symbols = settings.get("symbols", [])
    for symbol in symbols:
        try:
            # Check daily loss guard once per cycle; if triggered, skip new entries
            loss_guard = should_stop_trading_today(broker, settings.get("risk", {}).get("max_daily_loss_pct", 0.15))
            if loss_guard:
                logger.warning("Daily loss guard active; skipping new positions")
                return
            # fetch recent 1-min bars; try multiple broker methods
            bars = None
            if hasattr(broker, "historical_prices"):
                bars = broker.historical_prices(symbol)
            elif hasattr(broker, "market_data"):
                # market_data may return historical bars or a snapshot Quote
                try:
                    bars = broker.market_data(symbol)
                except Exception:
                    bars = None

            df1 = _to_df(bars) if bars is not None else pd.DataFrame()
            if df1.empty or len(df1) < 30:
                logger.info("Not enough bars for %s, skipping", symbol)
                continue

            # compute scalp signal on 1-min bars
            scalp = scalp_signal(df1)

            # compute whale on 60-min resample (if requested)
            whale = {"signal": "HOLD", "confidence": 0.0}
            if settings.get("mode") in ("hybrid", "growth"):
                df60 = df1.resample("60T", label="right", closed="right").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"})
                whale = whale_rules(df60, symbol)

            # decide final action
            action = scalp.get("signal", "HOLD")
            if whale.get("signal", "HOLD") != "HOLD":
                action = whale["signal"]

            if action in ("BUY", "SELL", "BUY_CALL", "BUY_PUT"):
                # pick option using refined selection
                direction = "C" if action.startswith("BUY") else "P"
                last_under_q = broker.market_data(symbol)
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
                    logger.info("No viable option found for %s", symbol)
                    continue

                # get option premium
                q = None
                try:
                    q = broker.market_data(getattr(opt, "symbol", opt))
                    premium = getattr(q, "last", 0.0)
                except Exception:
                    premium = 0.0

                cfg_risk = settings.get("risk", {})
                equity = broker.pnl().get("net", 100000.0)
                size = position_size(equity, cfg_risk.get("max_risk_pct_per_trade", 0.01), cfg_risk.get("stop_loss_pct", 0.2), premium or 0.0)
                if size <= 0:
                    logger.info("Computed size 0 for %s, skipping", symbol)
                    continue

                # check liquidity
                # Re-check liquidity guard with same thresholds
                if q is None or not is_liquid(q, cfg_opts.get("max_spread_pct", 2.0), cfg_opts.get("min_volume", 100)):
                    logger.info("Option contract illiquid for %s, skipping", symbol)
                    continue

                # build bracket
                bracket = build_bracket(premium, cfg_risk.get("take_profit_pct"), cfg_risk.get("stop_loss_pct"))

                # submit order via broker.place_order using OrderTicket dataclass
                from .broker.base import OrderTicket

                ticket = OrderTicket(contract=opt, action=("BUY" if action.startswith("BUY") else "SELL"), quantity=size, order_type="MKT", take_profit_pct=cfg_risk.get("take_profit_pct"), stop_loss_pct=cfg_risk.get("stop_loss_pct"))
                order_id = broker.place_order(ticket)

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
                trade = {"timestamp": datetime.utcnow().isoformat(), "symbol": symbol, "action": ticket.action, "quantity": size, "price": premium, "stop": bracket.get("stop_loss"), "target": bracket.get("take_profit")}
                log_trade(trade)

        except Exception:
            logger.error("Error during run_cycle for %s:\n%s", symbol, traceback.format_exc())


def run_scheduler(broker, settings: Dict[str, Any]):
    interval_seconds = settings.get("schedule", {}).get("interval_seconds", 180)
    while True:
        now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        if is_rth(now):
            try:
                run_cycle(broker, settings)
            except Exception:
                logger.exception("Scheduler cycle failed")
        time.sleep(interval_seconds)
