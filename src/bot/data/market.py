from typing import Iterable, Dict
from ..broker.base import Broker


def historical_prices(broker: Broker, symbol: str) -> Iterable[Dict]:
    return broker.market_data(symbol)
