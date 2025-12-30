import os
import time
import uuid
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..broker.base import OptionContract, OrderTicket, Quote

try:  # ib_insync is an optional runtime dependency
    from ib_insync import IB, Contract, LimitOrder, MarketOrder, Option, Order, Stock
except Exception:  # pragma: no cover - optional dependency
    IB = None


def _next_friday_date(start: datetime) -> str:
    # return YYYYMMDD for next Friday (or this week's Friday if in future)
    days_ahead = 4 - start.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    friday = (start + timedelta(days=days_ahead)).date()
    return friday.strftime("%Y%m%d")


class IBKRBroker:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[int] = None,
        paper: bool = True,
    ):
        # load defaults from env or settings file
        host = host or os.getenv("IBKR_HOST") or "127.0.0.1"
        port = port or int(os.getenv("IBKR_PORT") or (4002 if paper else 4001))
        client_id = client_id or int(os.getenv("IBKR_CLIENT_ID") or 1)

        self.host = host
        self.port = port
        self.client_id = client_id
        self.paper = paper
        self.ib = IB() if IB else None

    @retry(
        wait=wait_exponential(min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    def connect(self, timeout: int = 10) -> None:
        if not self.ib:
            raise RuntimeError("ib_insync not installed")
        if self.ib.isConnected():
            return
        logger.info(
            "Connecting to IB at %s:%s clientId=%s",
            self.host,
            self.port,
            self.client_id,
        )
        # Await the async connect explicitly to avoid 'coroutine was never awaited' warnings
        loop = self.ib.loop or asyncio.get_event_loop()
        loop.run_until_complete(
            self.ib.connectAsync(
                self.host, self.port, clientId=self.client_id, timeout=timeout
            )
        )

    def is_connected(self) -> bool:
        return bool(self.ib and self.ib.isConnected())

    def market_data(self, symbol: str, timeout: float = 2.0) -> Quote:
        if not self.is_connected():
            self.connect()
        contract = Stock(symbol, "SMART", "USD")
        # request a snapshot ticker
        ticker = self.ib.reqMktData(contract, snapshot=False, regulatorySnapshot=False)
        # wait briefly for data
        start = time.time()
        while time.time() - start < timeout:
            if ticker.bid and ticker.ask and (ticker.last or ticker.close):
                last = float(ticker.last or ticker.close)
                bid = float(ticker.bid)
                ask = float(ticker.ask)
                return Quote(
                    symbol=symbol, last=last, bid=bid, ask=ask, time=time.time()
                )
            time.sleep(0.2)
        # fallback: return empty quote with zeros
        logger.warning("market_data timeout for %s", symbol)
        return Quote(symbol=symbol, last=0.0, bid=0.0, ask=0.0, time=time.time())

    def option_chain(
        self, symbol: str, expiry_hint: str = "weekly"
    ) -> List[OptionContract]:
        """Fetch option expirations and strikes and return a list of OptionContract for nearest weekly ATM calls and puts."""
        if not self.is_connected():
            self.connect()
        # use reqSecDefOptParams to get chain info
        try:
            chains = self.ib.reqSecDefOptParams(symbol, "SMART", "STK")
        except (ConnectionError, TimeoutError, AttributeError) as e:
            logger.exception(
                "failed to fetch option chain params for %s: %s", symbol, type(e).__name__
            )
            return []

        # find first chain matching underlying symbol
        chain = None
        for c in chains:
            if c.underlyingSymbol.upper() == symbol.upper():
                chain = c
                break
        if not chain:
            logger.warning("no option chain found for %s", symbol)
            return []

        expirations = sorted(set(chain.expirations))
        strikes = sorted(set(chain.strikes))

        # pick expiry: next Friday for weekly
        if expiry_hint == "weekly":
            expiry = _next_friday_date(datetime.now(timezone.utc))
            # if expiry not in expirations, choose the nearest future
            if expiry not in expirations:
                expiry = min(
                    expirations,
                    key=lambda d: abs(
                        datetime.strptime(d, "%Y%m%d").date() - datetime.now(timezone.utc).date()
                    ),
                )
        else:
            expiry = expirations[0]

        # get last price to find ATM
        quote = self.market_data(symbol)
        last = quote.last or 0.0
        if not strikes:
            return []
        atm = min(strikes, key=lambda s: abs(s - last))

        contracts: List[OptionContract] = []
        # create ATM Call and Put
        for right in ("C", "P"):
            contracts.append(
                OptionContract(
                    symbol=symbol,
                    right=right,
                    strike=float(atm),
                    expiry=expiry,
                    multiplier=100,
                )
            )
        return contracts

    def _to_ib_contract(self, oc: OptionContract) -> Contract:
        return Option(
            symbol=oc.symbol,
            lastTradeDateOrContractMonth=oc.expiry,
            strike=oc.strike,
            right=oc.right,
            exchange="SMART",
            multiplier=str(oc.multiplier),
        )

    def place_order(self, ticket: OrderTicket) -> str:
        if not self.is_connected():
            self.connect()
        # Only support Option or Stock ticket.contract types
        # Map OrderTicket to ib_insync Order and Contract
        if isinstance(ticket.contract, OptionContract):
            contract = self._to_ib_contract(ticket.contract)
        elif isinstance(ticket.contract, str):
            # assume stock symbol
            contract = Stock(ticket.contract, "SMART", "USD")
        else:
            contract = ticket.contract  # assume already an ib_insync Contract

        # choose order
        if ticket.order_type.upper() == "MKT":
            order: Order = MarketOrder(ticket.action, ticket.quantity)
        else:
            order = LimitOrder(ticket.action, ticket.quantity, ticket.limit_price)

        # handle bracket via TP/SL by creating child orders with same parentId and OCA group
        oca_group = f"oca-{uuid.uuid4().hex[:8]}"

        # transmit parent as False if we have children
        has_children = bool(ticket.take_profit_pct or ticket.stop_loss_pct)
        if has_children:
            order.transmit = False

        trade = self.ib.placeOrder(contract, order)

        parent_order_id = getattr(order, "orderId", None)

        # create child orders
        children_ids = []
        if has_children and parent_order_id is not None:
            # calculate TP/SL based on last price if option contract
            last_price = 0.0
            try:
                q = self.market_data(
                    ticket.contract.symbol
                    if isinstance(ticket.contract, OptionContract)
                    else ticket.contract
                )
                last_price = q.last
            except (ConnectionError, TimeoutError, ValueError, AttributeError) as e:
                logger.debug("failed to fetch last price for order: %s", type(e).__name__)
                last_price = 0.0

            if ticket.take_profit_pct and last_price:
                tp_price = last_price * (1 + ticket.take_profit_pct)
                tp = LimitOrder(
                    "SELL" if ticket.action == "BUY" else "BUY",
                    ticket.quantity,
                    round(tp_price, 2),
                )
                tp.parentId = parent_order_id
                tp.ocaGroup = oca_group
                tp.transmit = False
                self.ib.placeOrder(contract, tp)
                children_ids.append(getattr(tp, "orderId", None))

            if ticket.stop_loss_pct and last_price:
                sl_price = last_price * (1 - ticket.stop_loss_pct)
                sl = LimitOrder(
                    "SELL" if ticket.action == "BUY" else "BUY",
                    ticket.quantity,
                    round(sl_price, 2),
                )
                sl.parentId = parent_order_id
                sl.ocaGroup = oca_group
                sl.transmit = True  # last in group transmits
                self.ib.placeOrder(contract, sl)
                children_ids.append(getattr(sl, "orderId", None))

        # if no children or parent has no id, ensure order is transmitted
        try:
            if not has_children:
                order.transmit = True
            # in ib_insync, placeOrder is enough; return an identifier
            oid = getattr(order, "orderId", None) or str(uuid.uuid4())
            return str(oid)
        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.exception("place_order failed: %s", type(e).__name__)
            raise

    def cancel_order(self, order_id: str) -> None:
        if not self.is_connected():
            self.connect()
        # find order by id and cancel
        for o in list(self.ib.orders()):
            if str(getattr(o, "orderId", "")) == str(order_id):
                self.ib.cancelOrder(o)

    def positions(self) -> List[Dict[str, Any]]:
        if not self.is_connected():
            self.connect()
        out: List[Dict[str, Any]] = []
        for pos in self.ib.positions():
            contract = pos.contract
            out.append(
                {
                    "symbol": getattr(contract, "symbol", str(contract)),
                    "position": pos.position,
                    "avgCost": getattr(pos, "avgCost", None),
                }
            )
        return out

    def pnl(self) -> Dict[str, float]:
        if not self.is_connected():
            self.connect()
        # approximate using accountSummary
        try:
            vals = self.ib.accountValues()
            net = 0.0
            for v in vals:
                if v.tag == "NetLiquidation":
                    net = float(v.value)
            return {"net": net}
        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.exception("failed to fetch PnL: %s", type(e).__name__)
            return {"net": 0.0}

    def account(self) -> Dict[str, Any]:
        if not self.is_connected():
            self.connect()
        try:
            summary = self.ib.accountSummary()
            return {f"{s.tag}": s.value for s in summary}
        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.exception("failed to fetch account summary: %s", type(e).__name__)
            return {}

    def historical_prices(
        self,
        symbol: str,
        duration: str = "60 M",
        bar_size: str = "1 min",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
    ):
        """Fetch historical OHLCV bars as a pandas DataFrame indexed by time.

        Args:
            symbol: Underlying stock symbol.
            duration: IBKR duration string (e.g., '30 M', '60 M', '1 D').
            bar_size: IBKR bar size (e.g., '1 min', '5 mins', '1 hour').
            what_to_show: Data type, default 'TRADES'.
            use_rth: Restrict to Regular Trading Hours.

        Returns:
            pd.DataFrame with columns [open, high, low, close, volume] indexed by timestamp.
        """
        if not self.is_connected():
            self.connect()
        try:
            # import pandas lazily to avoid heavy import at module load
            import pandas as pd  # type: ignore

            contract = Stock(symbol, "SMART", "USD")
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=use_rth,
                formatDate=1,
            )
            rows = [
                {
                    "time": pd.to_datetime(getattr(b, "date", None)),
                    "open": float(getattr(b, "open", 0.0)),
                    "high": float(getattr(b, "high", 0.0)),
                    "low": float(getattr(b, "low", 0.0)),
                    "close": float(getattr(b, "close", 0.0)),
                    "volume": int(getattr(b, "volume", 0) or 0),
                }
                for b in (bars or [])
            ]
            if not rows:
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])  # type: ignore[name-defined]
            df = pd.DataFrame(rows)
            if "time" in df.columns:
                df = df.set_index("time")
            return df
        except Exception:
            logger.exception("historical_prices failed for %s", symbol)
            try:
                import pandas as pd  # type: ignore

                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])  # type: ignore[name-defined]
            except Exception:
                return []  # fallback for environments without pandas

    def disconnect(self) -> None:
        try:
            if self.ib and self.ib.isConnected():
                self.ib.disconnect()
        except Exception as e:
            logger.debug("error during disconnect: %s", type(e).__name__)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.disconnect()
