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
    def connect(self, timeout: int = 10, max_client_id_retries: int = 5) -> None:
        if not self.ib:
            raise RuntimeError("ib_insync not installed")
        if self.ib.isConnected():
            return
        logger.info(
            "Connecting to IB at {}:{} clientId={}",
            self.host,
            self.port,
            self.client_id,
        )
        try:
            # Ensure an event loop exists in this thread for ib_insync
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Prefer synchronous connect for compatibility; ib_insync will use the loop above
            attempts = 0
            while True:
                try:
                    self.ib.connect(
                        self.host, self.port, clientId=self.client_id, timeout=timeout
                    )
                    break
                except Exception as exc:  # pragma: no cover
                    msg = str(exc).lower()
                    # Detect client-id in use (IB error 326) and retry with next id
                    if ("client" in msg and "id" in msg and "use" in msg) or "326" in msg:
                        old = self.client_id
                        attempts += 1
                        if attempts > max_client_id_retries:
                            logger.error(
                                "ClientId retry exhausted (last id={}); giving up", old
                            )
                            raise
                        self.client_id = int(self.client_id) + 1
                        logger.warning(
                            "ClientId {} in use; retrying with {} (attempt {}/{})",
                            old,
                            self.client_id,
                            attempts,
                            max_client_id_retries,
                        )
                        time.sleep(1)
                        continue
                    # Other errors: re-raise to let tenacity handle backoff
                    raise
        except Exception as exc:  # pragma: no cover
            logger.exception("IB connect failed: {}", exc)
            raise

    def is_connected(self) -> bool:
        return bool(self.ib and self.ib.isConnected())
    
    def is_gateway_healthy(self) -> bool:
        """Verify Gateway connection is responsive, not just 'connected'.
        
        This is a lightweight health check that detects degraded connections
        without triggering market data requests.
        
        Returns:
            True if Gateway is healthy, False if degraded or disconnected.
        """
        if not self.is_connected():
            return False
        
        try:
            # managedAccounts() is a fast, read-only call that doesn't create subscriptions
            accounts = self.ib.managedAccounts()
            return bool(accounts)
        except Exception as e:
            logger.debug("Gateway health check failed: %s", type(e).__name__)
            return False

    def market_data(self, symbol, timeout: float = 5.0) -> Quote:
        """Get market data snapshot for symbol or contract.
        
        Uses snapshot mode to avoid persistent streaming subscriptions
        that would overwhelm Gateway buffers with Greeks/model updates.
        
        Args:
            symbol: Either a string symbol (for stocks) or an OptionContract object
            timeout: Max seconds to wait for data (increased for snapshot mode)
        """
        if not self.is_connected():
            self.connect()
        
        from ib_insync import util, Option
        import asyncio
        
        # Handle both string symbols (stocks) and OptionContract objects (options)
        if isinstance(symbol, str):
            contract = Stock(symbol, "SMART", "USD")
            symbol_str = symbol
        else:
            # If it's already a Contract-compatible object (like OptionContract from options.py), 
            # we should avoid reconstructing it locally if possible, or reconstruct accurately.
            # Our options.py returns OptionContract, but we've seen rejections when rebuilding it.
            # Ideally, we map attributes carefully.
            contract = Option(
                symbol=getattr(symbol, "symbol", ""),
                lastTradeDateOrContractMonth=getattr(symbol, "expiry", ""),
                strike=float(getattr(symbol, "strike", 0.0)),
                right=getattr(symbol, "right", "C"),
                exchange="SMART",
                multiplier="100",
                currency="USD"
            )
            symbol_str = f"{contract.symbol} {contract.lastTradeDateOrContractMonth} {contract.strike} {contract.right}"
        
        async def _get_quote():
            # Qualify contract first
            await self.ib.qualifyContractsAsync(contract)
            
            # CRITICAL: Use snapshot=True to prevent streaming subscriptions
            # This eliminates automatic Greeks/model parameter subscriptions
            # that cause Gateway buffer overflow
            ticker = self.ib.reqMktData(contract, snapshot=True, regulatorySnapshot=False)
            
            # Wait for snapshot data to arrive
            start = time.time()
            while time.time() - start < timeout:
                await asyncio.sleep(0.1)
                
                # Extract values with proper None/NaN handling for snapshot mode
                bid = ticker.bid if (ticker.bid is not None and ticker.bid > 0) else None
                ask = ticker.ask if (ticker.ask is not None and ticker.ask > 0) else None
                last = ticker.last if (ticker.last is not None and ticker.last > 0) else None
                close = ticker.close if ticker.close else None
                
                if bid and ask:
                    price = last or close or ((bid + ask) / 2)
                    return Quote(
                        symbol=symbol_str, 
                        last=float(price),
                        bid=float(bid), 
                        ask=float(ask), 
                        time=time.time()
                    )
            return None
        
        try:
            quote = util.run(_get_quote())
            if quote:
                return quote
            logger.warning(f"market_data timeout for {symbol_str} after {timeout}s")
            return Quote(symbol=symbol_str, last=0.0, bid=0.0, ask=0.0, time=time.time())
        except Exception as e:
            logger.exception(f"market_data failed for {symbol_str}: {type(e).__name__}")
            return Quote(symbol=symbol_str, last=0.0, bid=0.0, ask=0.0, time=time.time())

    def option_chain(
        self, symbol: str, expiry_hint: str = "weekly"
    ) -> List[OptionContract]:
        """Fetch option expirations and strikes and return a list of OptionContract for nearest weekly ATM calls and puts."""
        if not self.is_connected():
            self.connect()
        
        # First resolve the underlying contract to get its conId
        try:
            underlying = Stock(symbol, "SMART", "USD")
            contracts = self.ib.qualifyContracts(underlying)
            if not contracts:
                logger.warning("could not qualify underlying contract for %s", symbol)
                return []
            underlying_conid = contracts[0].conId
        except (ConnectionError, TimeoutError, AttributeError) as e:
            logger.exception(
                "failed to qualify underlying contract for %s: %s", symbol, type(e).__name__
            )
            return []
        
        # use reqSecDefOptParams to get chain info with underlyingConId
        # Note: Use async API via util.run() to avoid event loop conflicts after connectAsync
        try:
            from ib_insync import util
            chains = util.run(self.ib.reqSecDefOptParamsAsync(symbol, "", "STK", underlying_conid))
            logger.info(f"reqSecDefOptParams returned {len(chains) if chains else 0} chains for {symbol} (conId={underlying_conid})")
        except (ConnectionError, TimeoutError, AttributeError, TypeError) as e:
            logger.exception(
                "failed to fetch option chain params for %s: %s", symbol, type(e).__name__
            )
            return []

        if not chains:
            logger.warning("reqSecDefOptParams returned empty chain list for %s (underlying conId=%s)", symbol, underlying_conid)
            return []

        # find first chain matching underlying symbol (check tradingClass attribute)
        chain = None
        for c in chains:
            if c.tradingClass.upper() == symbol.upper():
                chain = c
                break
        if not chain:
            logger.warning("no option chain found for %s in %d chains returned", symbol, len(chains))
            return []

        expirations = sorted(set(chain.expirations))
        strikes = sorted(set(chain.strikes))
        
        logger.info(f"Option chain for {symbol}: {len(expirations)} expirations, {len(strikes)} strikes")
        logger.debug(f"First 3 expirations: {expirations[:3]}, strike range: {strikes[0]}-{strikes[-1]}")

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

        # REFACTOR: Validate strikes for this specific expiry to avoid "phantom contracts"
        # reqSecDefOptParams returns a superset of strikes. Not all exist for every expiry.
        # We query reqContractDetails to get the exact list of valid strikes for this expiry.
        try:
            # Wildcard search for the specific expiry we chose
            logger.info(f"Validating contracts for expiry {expiry} via reqContractDetails...")
            validate_contract = Option(symbol, lastTradeDateOrContractMonth=expiry, exchange="SMART", currency="USD")
            
            # Use sync call (safe within IB context usually) or util.run if needed. 
            # Given previous pattern used util.run for params, we'll try standard sync first.
            # If this hangs, we may need util.run(ib.reqContractDetailsAsync(...))
            details = self.ib.reqContractDetails(validate_contract)
            
            if details:
                valid_strikes = sorted(list(set(d.contract.strike for d in details)))
                logger.info(f"Broadcast {len(valid_strikes)} valid strikes for {expiry} (was {len(strikes)} in cache)")
                strikes = valid_strikes
            else:
                logger.warning(f"No contract details found for {symbol} {expiry}; falling back to cached strikes (risky)")
        except Exception as e:
            logger.warning(f"Failed to validate strikes via reqContractDetails: {e}; falling back to cached strikes")

        # get last price to find ATM
        quote = self.market_data(symbol)
        last = quote.last or 0.0
        if not strikes:
            return []
        atm = min(strikes, key=lambda s: abs(s - last))
        
        # Find ATM index and return ATM +/- 5 strikes for flexibility
        atm_idx = strikes.index(atm)
        start_idx = max(0, atm_idx - 5)
        end_idx = min(len(strikes), atm_idx + 6)
        strike_range = strikes[start_idx:end_idx]
        
        logger.info(f"Returning {len(strike_range)} strikes around ATM {atm} (range: {strike_range[0]}-{strike_range[-1]})")

        contracts: List[OptionContract] = []
        # create contracts for ATM +/- 5 strikes, both calls and puts
        for strike in strike_range:
            for right in ("C", "P"):
                contracts.append(
                    OptionContract(
                        symbol=symbol,
                        right=right,
                        strike=float(strike),
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

        self.ib.placeOrder(contract, order)

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
        duration: str = "3600 S",
        bar_size: str = "1 min",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        timeout: int = 60,
    ):
        """Fetch historical OHLCV bars as a pandas DataFrame indexed by time.

        Args:
            symbol: Underlying stock symbol.
            duration: IBKR duration string in seconds or days (e.g., '3600 S' for 1 hour, '1 D' for 1 day).
            bar_size: IBKR bar size (e.g., '1 min', '5 mins', '1 hour').
            what_to_show: Data type, default 'TRADES'.
            use_rth: Restrict to Regular Trading Hours.
            timeout: Max seconds to wait for historical data (default 60s for market hours reliability).
        Returns:
            pd.DataFrame with columns [open, high, low, close, volume] indexed by timestamp.
        """
        if not self.is_connected():
            self.connect()

        # Verify Gateway is actually responsive (not just connected)
        if not self.is_gateway_healthy():
            logger.bind(symbol=symbol, event="gateway_unhealthy").warning(
                "Gateway health check failed before historical request, attempting reconnection"
            )
            try:
                self.disconnect()
                time.sleep(2)
                self.connect()
                if not self.is_gateway_healthy():
                    logger.bind(symbol=symbol, event="gateway_reconnect_failed").error(
                        "Gateway still unhealthy after reconnection"
                    )
                    import pandas as pd
                    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
            except Exception as reconn_err:
                logger.bind(symbol=symbol, error=type(reconn_err).__name__).error(
                    "Gateway reconnection failed: {}", type(reconn_err).__name__
                )
                import pandas as pd
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        try:
            # import pandas lazily to avoid heavy import at module load
            import pandas as pd  # type: ignore

            contract = Stock(symbol, "SMART", "USD")

            # Qualify contract before requesting data (prevents rejections for unknown contracts)
            try:
                qualified = self.ib.qualifyContracts(contract)
                if not qualified or not contract.conId:
                    logger.bind(symbol=symbol, event="contract_qualification_failed").warning(
                        "Failed to qualify contract for {}", symbol
                    )
                    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
                logger.bind(symbol=symbol, conId=contract.conId, event="contract_qualified").debug(
                    "Contract qualified: conId={}", contract.conId
                )
            except Exception as qual_err:
                logger.bind(symbol=symbol, error=type(qual_err).__name__, event="contract_qualification_error").warning(
                    "Contract qualification error: {}", type(qual_err).__name__
                )
            
            # Allow ib_insync to settle
            self.ib.sleep(0.5)
            
            # Set request timeout
            old_timeout = self.ib.RequestTimeout
            self.ib.RequestTimeout = timeout
            
            logger.info(
                f"[HIST] Requesting: symbol={symbol}, duration={duration}, "
                f"use_rth={use_rth}, timeout={timeout}s, RequestTimeout={self.ib.RequestTimeout}"
            )
            request_start = time.time()
            bars = []
            
            # --- SIMPLIFIED REQUEST LOGIC ---
            try:
                # Direct blocking call to ib_insync (thread-safe within its architecture)
                # This matches the pattern proven working in diagnostic_test.py
                bars = self.ib.reqHistoricalData(
                    contract,
                    endDateTime="",
                    durationStr=duration,
                    barSizeSetting=bar_size,
                    whatToShow=what_to_show,
                    useRTH=use_rth,
                    formatDate=1,
                    keepUpToDate=False,
                    chartOptions=[]
                )
                
                request_elapsed = time.time() - request_start
                logger.info(f"[HIST] Completed: symbol={symbol}, elapsed={request_elapsed:.2f}s, bars={len(bars) if bars else 0}")
                
            except Exception as e:
                logger.bind(
                    symbol=symbol,
                    error=type(e).__name__,
                    event="historical_request_error"
                ).warning(f"Primary historical data request failed: {e}")
                bars = []

            # --- ROBUST RETRY LOGIC ---
            if not bars:
                logger.bind(symbol=symbol, event="historical_retry").warning(
                    f"Primary request returned 0 bars for {symbol}. Attempting retry in 1s..."
                )
                self.ib.sleep(1.0)
                
                try:
                    # Retry with same parameters
                    bars = self.ib.reqHistoricalData(
                        contract,
                        endDateTime="",
                        durationStr=duration,
                        barSizeSetting=bar_size,
                        whatToShow=what_to_show,
                        useRTH=use_rth,
                        formatDate=1,
                        keepUpToDate=False,
                        chartOptions=[]
                    )
                    retry_elapsed = time.time() - request_start
                    logger.info(f"[HIST] Retry Completed: symbol={symbol}, elapsed={retry_elapsed:.2f}s, bars={len(bars) if bars else 0}")
                except Exception as retry_err:
                    logger.bind(
                        symbol=symbol,
                        error=type(retry_err).__name__,
                        event="historical_retry_error"
                    ).error(f"Retry historical data request failed: {retry_err}")
                    bars = []

            # Restore timeout
            self.ib.RequestTimeout = old_timeout
            
            # --- DATAFRAME CONVERSION ---
            # DEBUG: Log what was returned
            logger.info(f"[DEBUG] historical_prices({symbol}): raw bars count = {len(bars) if bars else 0}")
            if bars and len(bars) > 0:
                logger.info(f"[DEBUG] First bar: date={bars[0].date}, close={bars[0].close}")
                logger.info(f"[DEBUG] Last bar: date={bars[-1].date}, close={bars[-1].close}")
            
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
                logger.warning(f"[DEBUG] No rows after conversion, returning empty DataFrame")
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])  # type: ignore[name-defined]
            
            df = pd.DataFrame(rows)
            
            if "time" in df.columns:
                df = df.set_index("time")
            
            logger.info(f"[DEBUG] Returning DataFrame with {len(df)} rows for {symbol}")
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
                # Cancel all active market data subscriptions to prevent Gateway buffer accumulation
                # This is critical for sustained operation - uncancelled subscriptions can cause
                # Gateway to fill internal buffers after sustained requests
                try:
                    for ticker in list(self.ib.tickers()):
                        try:
                            self.ib.cancelMktData(ticker.contract)
                            logger.debug(
                                "cancelled subscription: {}",
                                getattr(getattr(ticker, "contract", None), "symbol", str(getattr(ticker, "contract", ""))),
                            )
                        except Exception as tick_err:
                            logger.debug("error cancelling subscription: {}", type(tick_err).__name__)
                except Exception as list_err:
                    logger.debug("error listing tickers: {}", type(list_err).__name__)
                
                # Now safely disconnect
                self.ib.disconnect()
        except Exception as e:
            logger.debug("error during disconnect: {}", type(e).__name__)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.disconnect()
