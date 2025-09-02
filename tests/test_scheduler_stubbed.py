from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from src.bot.scheduler import run_cycle


@dataclass
class StubQuote:
    symbol: str
    last: float
    bid: float
    ask: float
    volume: int


@dataclass
class StubOption:
    symbol: str
    right: str
    strike: float
    expiry: str
    multiplier: int = 100


class StubBroker:
    def __init__(self):
        self._equity = 100000.0
        self._orders: List[Dict[str, Any]] = []

    def market_data(self, symbol_or_contract):
        # Return stable quotes
        if isinstance(symbol_or_contract, str):
            return StubQuote(
                symbol_or_contract, last=100.0, bid=99.9, ask=100.1, volume=1_000_000
            )
        # options
        return StubQuote(
            getattr(symbol_or_contract, "symbol", "OPT"),
            last=2.5,
            bid=2.45,
            ask=2.55,
            volume=5000,
        )

    def option_chain(self, symbol: str, expiry_hint: str = "weekly"):
        # Generate a tiny chain around 100
        strikes = [99, 100, 101]
        return [
            StubOption(symbol=f"{symbol}C{k}", right="C", strike=k, expiry="20250117")
            for k in strikes
        ] + [
            StubOption(symbol=f"{symbol}P{k}", right="P", strike=k, expiry="20250117")
            for k in strikes
        ]

    def historical_prices(
        self, symbol: str, duration: str = "60 M", bar_size: str = "1 min", **_
    ):
        # Return a simple 1-min OHLCV increasing trend
        idx = pd.date_range(end=datetime.utcnow(), periods=60, freq="1min")
        close = pd.Series([100 + i * 0.01 for i in range(60)], index=idx)
        high = close + 0.05
        low = close - 0.05
        vol = pd.Series([1000] * 60, index=idx)
        return pd.DataFrame(
            {"open": close, "high": high, "low": low, "close": close, "volume": vol}
        )

    def place_order(self, ticket):
        self._orders.append({"action": ticket.action, "qty": ticket.quantity})
        return f"OID{len(self._orders)}"

    def pnl(self) -> Dict[str, float]:
        return {"net": self._equity}


def test_run_cycle_with_stubbed_broker_no_errors(tmp_path, monkeypatch):
    broker = StubBroker()
    settings = {
        "symbols": ["SPY"],
        "mode": "growth",
        "risk": {
            "max_risk_pct_per_trade": 0.01,
            "stop_loss_pct": 0.2,
            "take_profit_pct": 0.3,
        },
        "options": {"moneyness": "atm", "min_volume": 100, "max_spread_pct": 5.0},
        "schedule": {"interval_seconds": 1, "max_concurrent_symbols": 1},
        "monitoring": {"alerts_enabled": False},
    }
    # Run one cycle; expect no exceptions
    run_cycle(broker, settings)
