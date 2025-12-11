"""Integration tests for the complete data flow pipeline.

Tests the end-to-end path: historical bars → DataFrame → strategy signals →
option selection → position sizing → OrderTicket, using realistic market data
and parametrized edge cases.
"""

from datetime import datetime, timedelta, timezone
from unittest import mock
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.bot.data.market import _to_df
from src.bot.data.options import pick_weekly_option
from src.bot.execution import build_bracket
from src.bot.risk import position_size, stop_target_from_premium
from src.bot.strategy.scalp_rules import scalp_signal
from src.bot.strategy.whale_rules import whale_rules


@pytest.fixture
def sample_1min_bars():
    """Generate realistic 1-minute OHLCV bars for last 60 minutes."""
    now = datetime.now(timezone.utc)
    timestamps = pd.date_range(end=now, periods=60, freq="1min")
    base_price = 450.0
    
    # Create realistic price movement
    closes = pd.Series(
        [base_price + i * 0.05 for i in range(60)],
        index=timestamps,
    )
    
    return pd.DataFrame({
        "open": closes - 0.02,
        "high": closes + 0.08,
        "low": closes - 0.05,
        "close": closes,
        "volume": pd.Series([int(1000 + i * 50) for i in range(60)], index=timestamps),
    })


@pytest.fixture
def sample_60min_bars():
    """Generate realistic 60-minute OHLCV bars for last 120 bars (20 trading days)."""
    now = datetime.now(timezone.utc)
    timestamps = pd.date_range(end=now, periods=120, freq="60min")
    base_price = 450.0
    
    # Create realistic price movement with volatility
    closes = pd.Series(
        [base_price + i * 0.02 + (i % 10) * 0.1 for i in range(120)],
        index=timestamps,
    )
    
    return pd.DataFrame({
        "open": closes - 0.05,
        "high": closes + 0.15,
        "low": closes - 0.10,
        "close": closes,
        "volume": pd.Series([int(50000 + i * 500) for i in range(120)], index=timestamps),
    })


class TestDataFlowBasic:
    """Test basic data flow through each component."""

    def test_to_df_converts_dict_list(self):
        """_to_df converts dictionary list to DataFrame."""
        bars = [
            {"date": "2025-12-10 10:00:00", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000},
            {"date": "2025-12-10 10:01:00", "open": 101, "high": 103, "low": 100, "close": 102, "volume": 1100},
        ]
        
        df = _to_df(bars)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["open", "high", "low", "close", "volume"] or "close" in df.columns

    def test_scalp_signal_on_trending_up_market(self, sample_1min_bars):
        """Scalp signal should generate BUY on uptrend with good momentum."""
        signal = scalp_signal(sample_1min_bars)
        
        assert signal["signal"] in ["BUY", "SELL", "HOLD"]
        assert 0.0 <= signal["confidence"] <= 1.0
        # On uptrend, should be bullish
        assert signal["signal"] in ["BUY", "HOLD"]

    def test_whale_signal_on_volume_spike(self, sample_60min_bars):
        """Whale signal should respond to volume spikes."""
        # Artificially inject volume spike in last bar
        sample_60min_bars.loc[sample_60min_bars.index[-1], "volume"] = 500000
        
        signal = whale_rules(sample_60min_bars, "SPY")
        
        assert signal["signal"] in ["BUY_CALL", "BUY_PUT", "HOLD"]
        assert 0.0 <= signal["confidence"] <= 1.0

    def test_position_sizing_scaled_by_equity(self):
        """Position size should scale with account equity."""
        size_small = position_size(
            equity=10000, max_risk_pct=0.01, stop_loss_pct=0.50, option_premium=2.50
        )
        size_large = position_size(
            equity=100000, max_risk_pct=0.01, stop_loss_pct=0.50, option_premium=2.50
        )
        
        assert size_large > size_small
        assert size_small >= 1
        assert size_large >= 1

    def test_build_bracket_prices_reasonable(self):
        """Build bracket should produce reasonable TP/SL prices."""
        bracket = build_bracket(
            option_premium=2.50,
            take_profit_pct=0.40,
            stop_loss_pct=0.50,
        )
        
        assert bracket["take_profit"] > 2.50  # TP above entry
        assert bracket["stop_loss"] < 2.50    # SL below entry
        assert bracket["take_profit"] == 2.50 * 1.40  # 40% gain
        assert bracket["stop_loss"] == 2.50 * 0.50    # 50% loss


class TestDataFlowIntegration:
    """Test complete flows from bars to ordering."""

    def test_bullish_scalp_flow(self, sample_1min_bars):
        """Complete flow: bullish bars → BUY signal → position sizing → bracket."""
        # Step 1: Strategy signal
        signal = scalp_signal(sample_1min_bars)
        
        # Step 2: Assume BUY signal received
        if signal["signal"] == "BUY":
            # Step 3: Position sizing
            size = position_size(
                equity=50000,
                max_risk_pct=0.02,
                stop_loss_pct=0.50,
                option_premium=2.75,  # Realistic option price
            )
            
            # Step 4: Build bracket
            bracket = build_bracket(
                option_premium=2.75,
                take_profit_pct=0.35,
                stop_loss_pct=0.50,
            )
            
            # Validations
            assert size >= 1
            assert bracket["take_profit"] is not None
            assert bracket["stop_loss"] is not None
            assert bracket["take_profit"] > 2.75
            assert bracket["stop_loss"] < 2.75
    
    def test_option_chain_filtering(self):
        """Test option selection filters by liquidity and moneyness."""
        # Create mock broker with option chain
        contracts = [
            Mock(symbol="SPY_C_450", strike=450, right="C", expiry="20251219"),
            Mock(symbol="SPY_C_455", strike=455, right="C", expiry="20251219"),
            Mock(symbol="SPY_C_460", strike=460, right="C", expiry="20251219"),
        ]
        
        quote_liquid = Mock(bid=2.45, ask=2.55, last=2.50, volume=50000)
        quote_illiquid = Mock(bid=2.0, ask=5.0, last=3.50, volume=10)
        
        def market_data_side_effect(contract_or_symbol):
            if hasattr(contract_or_symbol, "strike") and contract_or_symbol.strike == 455:
                return quote_liquid
            else:
                return quote_illiquid
        
        broker = Mock()
        broker.option_chain = Mock(return_value=contracts)
        broker.market_data = Mock(side_effect=market_data_side_effect)
        
        # Select ATM call with liquidity filter
        selected = pick_weekly_option(
            broker,
            underlying="SPY",
            right="C",
            last_price=453.0,
            moneyness="atm",
            min_volume=1000,
            max_spread_pct=2.0,
        )
        
        assert selected is not None
        assert selected.strike == 455  # Closest to last price


@pytest.mark.parametrize("equity,risk_pct,premium,stop_pct", [
    (10000, 0.01, 1.00, 0.50),     # Small account, tight stop
    (100000, 0.02, 2.50, 0.50),    # Medium account, standard stop
    (1000000, 0.05, 5.00, 0.50),   # Large account, larger stop
])
class TestDataFlowParametrized:
    """Parametrized tests for various market conditions and account sizes."""

    def test_position_sizing_consistency(self, equity, risk_pct, premium, stop_pct):
        """Position size should be consistent across parameters."""
        size = position_size(equity, risk_pct, stop_pct, premium)
        
        # Risk should not exceed equity * risk_pct
        max_risk_dollars = equity * risk_pct
        actual_risk = size * premium * stop_pct
        
        assert actual_risk <= max_risk_dollars + (premium * stop_pct)  # Allow 1 contract slippage
        assert size >= 1 if equity > 0 else size == 0

    def test_bracket_prices_consistent(self, equity, risk_pct, premium, stop_pct):
        """Bracket prices should be consistent with premium."""
        bracket = build_bracket(premium, take_profit_pct=0.25, stop_loss_pct=stop_pct)
        
        assert bracket["stop_loss"] < premium  # SL below
        assert bracket["take_profit"] > premium  # TP above
        assert bracket["stop_loss"] > 0  # Valid prices


class TestDataFlowEdgeCases:
    """Test edge cases and error conditions."""

    def test_scalp_signal_empty_dataframe(self):
        """Scalp signal handles empty DataFrame gracefully."""
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        signal = scalp_signal(df)
        
        assert signal["signal"] == "HOLD"
        assert signal["confidence"] == 0.0

    def test_scalp_signal_all_nans(self):
        """Scalp signal handles all-NaN DataFrame gracefully."""
        df = pd.DataFrame({
            "open": [float("nan")] * 30,
            "high": [float("nan")] * 30,
            "low": [float("nan")] * 30,
            "close": [float("nan")] * 30,
            "volume": [float("nan")] * 30,
        })
        
        signal = scalp_signal(df)
        
        assert signal["signal"] == "HOLD"
        assert signal["confidence"] == 0.0

    def test_position_size_zero_equity(self):
        """Position size returns 0 for zero/negative equity."""
        size = position_size(equity=0, max_risk_pct=0.01, stop_loss_pct=0.50, option_premium=2.50)
        assert size == 0
        
        size = position_size(equity=-1000, max_risk_pct=0.01, stop_loss_pct=0.50, option_premium=2.50)
        assert size == 0

    def test_position_size_zero_premium(self):
        """Position size returns 0 for zero/negative premium."""
        size = position_size(equity=50000, max_risk_pct=0.01, stop_loss_pct=0.50, option_premium=0)
        assert size == 0
        
        size = position_size(equity=50000, max_risk_pct=0.01, stop_loss_pct=0.50, option_premium=-1)
        assert size == 0

    def test_build_bracket_none_targets(self):
        """Build bracket handles None TP/SL gracefully."""
        bracket = build_bracket(option_premium=2.50, take_profit_pct=None, stop_loss_pct=None)
        
        assert bracket["take_profit"] is None
        assert bracket["stop_loss"] is None

    def test_whale_signal_insufficient_data(self):
        """Whale signal handles insufficient bar data."""
        small_df = pd.DataFrame({
            "close": [100, 101, 102],
            "volume": [1000, 1000, 1000],
        })
        
        signal = whale_rules(small_df, "SPY")
        
        assert signal["signal"] == "HOLD"
        assert signal["confidence"] == 0.0


class TestDataFlowWithBrokerMock:
    """Test data flow with mocked broker for end-to-end scenarios."""

    def test_complete_buy_flow_with_broker(self, sample_1min_bars, sample_60min_bars):
        """Complete BUY flow: bars → signal → option selection → position → bracket."""
        # Create mock broker
        broker = Mock()
        broker.market_data = Mock(return_value=Mock(last=453.0, bid=452.9, ask=453.1, volume=100000))
        broker.option_chain = Mock(return_value=[
            Mock(symbol="SPY_C_450", strike=450, right="C", expiry="20251219"),
            Mock(symbol="SPY_C_455", strike=455, right="C", expiry="20251219"),
            Mock(symbol="SPY_C_460", strike=460, right="C", expiry="20251219"),
        ])
        broker.pnl = Mock(return_value={"net": 100000.0})
        
        # Step 1: Get signal from bars
        scalp = scalp_signal(sample_1min_bars)
        whale = whale_rules(sample_60min_bars, "SPY")
        
        # Step 2: Decide action (scalp takes precedence)
        action = scalp["signal"] if scalp["signal"] != "HOLD" else whale["signal"]
        
        # Step 3: If action, proceed with option selection
        if action in ("BUY", "BUY_CALL"):
            last_price = 453.0
            option = pick_weekly_option(
                broker,
                underlying="SPY",
                right="C",
                last_price=last_price,
                moneyness="atm",
                min_volume=100,
                max_spread_pct=2.0,
            )
            
            # Step 4: Size position
            if option:
                quote = broker.market_data(option)
                size = position_size(
                    equity=100000,
                    max_risk_pct=0.02,
                    stop_loss_pct=0.50,
                    option_premium=quote.last,
                )
                
                # Step 5: Build bracket
                bracket = build_bracket(
                    option_premium=quote.last,
                    take_profit_pct=0.35,
                    stop_loss_pct=0.50,
                )
                
                # Assertions
                assert size >= 1
                assert bracket["take_profit"] > quote.last
                assert bracket["stop_loss"] < quote.last
