from typing import Protocol, List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Quote:
    symbol: str
    last: float
    bid: float
    ask: float
    time: float  # epoch


@dataclass
class OptionContract:
    symbol: str       # IB local symbol
    right: str        # "C" or "P"
    strike: float
    expiry: str       # YYYYMMDD
    multiplier: int


@dataclass
class OrderTicket:
    contract: Any
    action: str       # BUY/SELL
    quantity: int
    order_type: str   # MKT/LMT
    limit_price: Optional[float] = None
    tif: str = "DAY"
    take_profit_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    transmit: bool = True


class Broker(Protocol):
    def connect(self) -> None: ...
    def is_connected(self) -> bool: ...
    def market_data(self, symbol: str) -> Quote: ...
    def option_chain(self, symbol: str, expiry_hint: str = "weekly") -> List[OptionContract]: ...
    def historical_prices(self, symbol: str, duration: str = "60 M", bar_size: str = "1 min", what_to_show: str = "TRADES", use_rth: bool = True): ...
    def place_order(self, ticket: OrderTicket) -> str: ...
    def cancel_order(self, order_id: str) -> None: ...
    def positions(self) -> List[Dict[str, Any]]: ...
    def pnl(self) -> Dict[str, float]: ...
    def account(self) -> Dict[str, Any]: ...
