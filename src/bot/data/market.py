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


def _to_df(bars_iter):
    """Convert iterable of bar dicts to pandas DataFrame if available.

    Returns an empty list when pandas is unavailable to allow graceful skips.
    """
    try:
        import importlib

        pd = importlib.import_module("pandas")  # type: ignore
        df = pd.DataFrame(bars_iter)
        if df.empty:
            return df
        cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        if not cols:
            return importlib.import_module("pandas").DataFrame()  # type: ignore
        subset = df.loc[:, cols if len(cols) > 1 else [cols[0]]]
        subset_df = importlib.import_module("pandas").DataFrame(subset)  # type: ignore
        return subset_df.copy()
    except Exception:  # pylint: disable=broad-except
        try:
            import importlib

            return importlib.import_module("pandas").DataFrame()  # type: ignore
        except Exception:  # pylint: disable=broad-except
            return []
