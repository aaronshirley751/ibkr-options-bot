from ..broker.base import Broker


def historical_prices(broker: Broker, symbol: str, minutes: int = 60):
    """Return recent OHLCV bars as a DataFrame when supported by the broker.

    Falls back to broker.market_data when historical API is not present.
    """
    duration = f"{minutes} M"
    if hasattr(broker, "historical_prices"):
        return broker.historical_prices(symbol, duration=duration, bar_size="1 min")
    # Fallback: single-tick shaped structure
    q = broker.market_data(symbol)
    try:
        import pandas as pd  # type: ignore
    except (
        Exception
    ):  # pylint: disable=broad-except  # pragma: no cover - optional dependency
        return [{"open": q.last, "high": q.last, "low": q.last, "close": q.last, "volume": 0}]  # type: ignore[return-value]
    return pd.DataFrame(
        [{"open": q.last, "high": q.last, "low": q.last, "close": q.last, "volume": 0}]
    )
