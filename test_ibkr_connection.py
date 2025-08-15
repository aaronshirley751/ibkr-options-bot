"""Connectivity checks for IBKR Gateway using ib_insync.

Run this on your Raspberry Pi (or host) to validate IB Gateway/TWS is reachable and
returns basic market data for stocks, forex, and options. Optionally attempts
Level 2 depth if supported. Also requests short historical bars.

Example:
	python test_ibkr_connection.py --host 127.0.0.1 --port 4002 --client-id 101 --symbol SPY
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import asdict, dataclass
from typing import Optional, Any


@dataclass
class Snapshot:
	"""Simple snapshot of best bid/ask and last for a contract."""

	symbol: str
	last: float
	bid: float
	ask: float


def _snapshot(ib: Any, contract: Any, timeout: float = 3.0) -> Optional[Snapshot]:
	"""Request a snapshot for a contract within a timeout window."""

	ticker = ib.reqMktData(contract, snapshot=False, regulatorySnapshot=False)
	start = time.time()
	while time.time() - start < timeout:
		last = float(ticker.last or ticker.close or 0.0)
		bid = float(ticker.bid or 0.0)
		ask = float(ticker.ask or 0.0)
		if (bid and ask) or last:
			sym = getattr(contract, "symbol", "") or getattr(contract, "localSymbol", "")
			return Snapshot(symbol=sym, last=last, bid=bid, ask=ask)
		ib.sleep(0.2)
	return None


def main() -> int:
	"""Entry point for connectivity checks against IB Gateway/TWS."""

	ap = argparse.ArgumentParser(description="IBKR connectivity test")
	ap.add_argument("--host", default="127.0.0.1")
	ap.add_argument("--port", type=int, default=4002)
	ap.add_argument("--client-id", type=int, default=101)
	ap.add_argument("--symbol", default="SPY", help="Stock symbol to test")
	ap.add_argument("--timeout", type=float, default=3.0)
	args = ap.parse_args()

	# Import ib_insync lazily to avoid hard dependency at import time
	try:
		from ib_insync import IB, Stock, Option, Forex  # type: ignore
	except Exception:
		print("ib_insync not installed. Install with: pip install ib-insync", file=sys.stderr)
		return 1

	ib = IB()
	ib.connect(args.host, args.port, clientId=args.client_id, timeout=10)
	try:
		# Stocks
		stock = Stock(args.symbol, "SMART", "USD")
		snap = _snapshot(ib, stock, timeout=args.timeout)
		print({"event": "stock_snapshot", **(asdict(snap) if snap else {"symbol": args.symbol, "ok": False})})

		# Forex
		fx = Forex("EURUSD")
		fx_snap = _snapshot(ib, fx, timeout=args.timeout)
		print({"event": "forex_snapshot", **(asdict(fx_snap) if fx_snap else {"symbol": "EURUSD", "ok": False})})

		# Options (ATM call)
		# Get strikes from sec def and choose nearest to last
		secdefs = ib.reqSecDefOptParams(args.symbol, "SMART", "STK")
		if secdefs:
			sd = secdefs[0]
			strikes = [float(s) for s in sd.strikes if s is not None]
			last = snap.last if snap else 0.0
			strike = min(strikes, key=lambda s: abs(s - last)) if strikes else 0.0
			expiry = sorted(sd.expirations)[0] if sd.expirations else ""
			opt = Option(args.symbol, expiry, strike, "C", "SMART")
			opt_snap = _snapshot(ib, opt, timeout=args.timeout)
			print({
				"event": "option_snapshot",
				**(asdict(opt_snap) if opt_snap else {"symbol": args.symbol, "ok": False, "strike": strike, "expiry": expiry}),
			})
		else:
			print({"event": "option_snapshot", "ok": False, "reason": "no_secdef"})

		# Historical bars (1m x 30m)
		bars = ib.reqHistoricalData(
			stock,
			endDateTime="",
			durationStr="30 M",
			barSizeSetting="1 min",
			whatToShow="TRADES",
			useRTH=True,
			formatDate=1,
		)
		print({"event": "historical_1m", "bars": len(bars)})

		# Level 2 depth (if subscribed)
		try:
			ticker = ib.reqMktDepth(stock)
			ib.sleep(1.0)
			levels = len(getattr(ticker, "domBids", [])) + len(getattr(ticker, "domAsks", []))
			print({"event": "depth", "levels": levels})
			ib.cancelMktDepth(stock)
		except Exception:
			print({"event": "depth", "ok": False, "reason": "not_available"})
	finally:
		try:
			ib.disconnect()
		except Exception:
			pass
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
