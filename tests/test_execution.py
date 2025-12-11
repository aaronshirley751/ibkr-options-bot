"""Unit tests for execution.py - order management and OCO emulation."""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.bot.broker.base import OptionContract, OrderTicket, Quote
from src.bot.execution import build_bracket, emulate_oco, is_liquid


class TestBuildBracket:
    """Test bracket order construction."""

    def test_build_bracket_no_tp_or_sl(self):
        """Returns None for both when no parameters provided."""
        result = build_bracket(premium=2.5, take_profit_pct=None, stop_loss_pct=None)
        assert result == {"take_profit": None, "stop_loss": None}

    def test_build_bracket_tp_only(self):
        """Calculates take profit with premium and percentage."""
        result = build_bracket(premium=2.0, take_profit_pct=0.5, stop_loss_pct=None)
        assert result["take_profit"] == pytest.approx(3.0)  # 2.0 * (1 + 0.5)
        assert result["stop_loss"] is None

    def test_build_bracket_sl_only(self):
        """Calculates stop loss with premium and percentage."""
        result = build_bracket(premium=2.0, take_profit_pct=None, stop_loss_pct=0.2)
        assert result["stop_loss"] == pytest.approx(1.6)  # 2.0 * (1 - 0.2)
        assert result["take_profit"] is None

    def test_build_bracket_both_tp_and_sl(self):
        """Calculates both take profit and stop loss."""
        result = build_bracket(premium=1.0, take_profit_pct=0.3, stop_loss_pct=0.1)
        assert result["take_profit"] == pytest.approx(1.3)  # 1.0 * (1 + 0.3)
        assert result["stop_loss"] == pytest.approx(0.9)  # 1.0 * (1 - 0.1)

    def test_build_bracket_high_premium(self):
        """Handles high premium values correctly."""
        result = build_bracket(premium=100.0, take_profit_pct=0.05, stop_loss_pct=0.02)
        assert result["take_profit"] == pytest.approx(105.0)
        assert result["stop_loss"] == pytest.approx(98.0)

    def test_build_bracket_zero_premium(self):
        """Handles zero premium gracefully."""
        result = build_bracket(premium=0.0, take_profit_pct=0.5, stop_loss_pct=0.2)
        assert result["take_profit"] == pytest.approx(0.0)
        assert result["stop_loss"] == pytest.approx(0.0)


class TestIsLiquid:
    """Test liquidity validation."""

    def test_is_liquid_meets_all_criteria(self):
        """Quote passing all liquidity checks."""
        quote = Mock()
        quote.bid = 2.45
        quote.ask = 2.55
        quote.volume = 10000
        quote.last = 2.50

        result = is_liquid(quote, max_spread_pct=2.0, min_volume=100)
        assert result is True

    def test_is_liquid_spread_too_wide(self):
        """Rejects quote with spread exceeding max_spread_pct."""
        quote = Mock()
        quote.bid = 2.0
        quote.ask = 3.0
        quote.volume = 10000
        quote.last = 2.50

        result = is_liquid(quote, max_spread_pct=2.0, min_volume=100)
        assert result is False

    def test_is_liquid_volume_too_low(self):
        """Rejects quote with volume below min_volume."""
        quote = Mock()
        quote.bid = 2.45
        quote.ask = 2.55
        quote.volume = 50
        quote.last = 2.50

        result = is_liquid(quote, max_spread_pct=2.0, min_volume=100)
        assert result is False

    def test_is_liquid_zero_bid_or_ask(self):
        """Rejects quote with zero bid or ask."""
        quote = Mock()
        quote.bid = 0.0
        quote.ask = 2.55
        quote.volume = 10000
        quote.last = 2.50

        result = is_liquid(quote, max_spread_pct=2.0, min_volume=100)
        assert result is False

    def test_is_liquid_negative_bid_ask(self):
        """Rejects quote with negative prices."""
        quote = Mock()
        quote.bid = -2.45
        quote.ask = 2.55
        quote.volume = 10000
        quote.last = 2.50

        result = is_liquid(quote, max_spread_pct=2.0, min_volume=100)
        assert result is False

    def test_is_liquid_missing_attributes(self):
        """Gracefully handles missing attributes."""
        quote = Mock()
        # Don't set bid/ask/volume/last attributes
        del quote.bid

        result = is_liquid(quote, max_spread_pct=2.0, min_volume=100)
        assert result is False

    def test_is_liquid_tight_spread(self):
        """Accepts quotes with very tight spreads."""
        quote = Mock()
        quote.bid = 2.495
        quote.ask = 2.505
        quote.volume = 100000
        quote.last = 2.50

        # Spread = (2.505 - 2.495) / 2.50 * 100 = 0.04%
        result = is_liquid(quote, max_spread_pct=1.0, min_volume=1000)
        assert result is True

    def test_is_liquid_high_volume(self):
        """Accepts quotes with very high volume."""
        quote = Mock()
        quote.bid = 2.45
        quote.ask = 2.55
        quote.volume = 1000000
        quote.last = 2.50

        result = is_liquid(quote, max_spread_pct=2.0, min_volume=100)
        assert result is True


class TestEmulateOCO:
    """Test OCO emulation thread behavior."""

    def test_emulate_oco_tp_triggers(self):
        """Emulation triggers take-profit order when price hits TP level."""
        broker = Mock()
        contract = Mock(symbol="SPY")
        
        # Simulate price rising to TP level
        quotes = [
            Mock(last=2.45),  # Below TP
            Mock(last=2.48),  # Below TP
            Mock(last=3.00),  # Hits TP (premium * 1.2 = 2.5 * 1.2 = 3.0)
        ]
        broker.market_data = Mock(side_effect=quotes)
        broker.place_order = Mock(return_value="CLOSE_ORDER_123")

        with patch('src.bot.execution.logger') as mock_logger:
            emulate_oco(
                broker,
                contract,
                parent_order_id="PARENT_123",
                take_profit=3.0,
                stop_loss=None,
                poll_seconds=0.01,
                side="BUY",
                quantity=1,
            )

        # Verify place_order was called for TP close
        assert broker.place_order.called
        call_args = broker.place_order.call_args[0][0]
        assert call_args.action == "SELL"
        assert call_args.order_type == "LMT"
        assert call_args.limit_price == 3.0

    def test_emulate_oco_sl_triggers(self):
        """Emulation triggers stop-loss order when price hits SL level."""
        broker = Mock()
        contract = Mock(symbol="SPY")
        
        # Simulate price falling to SL level
        quotes = [
            Mock(last=1.95),  # Above SL
            Mock(last=1.80),  # Hits SL (premium * 0.8 = 2.5 * 0.8 = 2.0, so below 2.0)
        ]
        broker.market_data = Mock(side_effect=quotes)
        broker.place_order = Mock(return_value="CLOSE_ORDER_456")

        with patch('src.bot.execution.logger'):
            emulate_oco(
                broker,
                contract,
                parent_order_id="PARENT_456",
                take_profit=None,
                stop_loss=2.0,
                poll_seconds=0.01,
                side="BUY",
                quantity=1,
            )

        # Verify place_order was called for SL close
        assert broker.place_order.called
        call_args = broker.place_order.call_args[0][0]
        assert call_args.action == "SELL"
        assert call_args.order_type == "MKT"

    def test_emulate_oco_neither_triggers(self):
        """Emulation continues polling if neither TP nor SL are hit."""
        broker = Mock()
        contract = Mock(symbol="SPY")
        
        # Price stays between TP and SL
        quotes = [
            Mock(last=2.48),
            Mock(last=2.49),
        ]
        broker.market_data = Mock(side_effect=quotes)

        with patch('src.bot.execution.logger'):
            # This will exhaust the quotes and eventually stop
            with pytest.raises(StopIteration):
                emulate_oco(
                    broker,
                    contract,
                    parent_order_id="PARENT_789",
                    take_profit=3.0,
                    stop_loss=2.0,
                    poll_seconds=0.01,
                    side="BUY",
                    quantity=1,
                )

    def test_emulate_oco_keyboard_interrupt(self):
        """Emulation handles KeyboardInterrupt gracefully."""
        broker = Mock()
        contract = Mock(symbol="SPY")
        
        def raise_interrupt(*args, **kwargs):
            raise KeyboardInterrupt("User interrupted")
        
        broker.market_data = Mock(side_effect=raise_interrupt)

        with patch('src.bot.execution.logger') as mock_logger:
            emulate_oco(
                broker,
                contract,
                parent_order_id="PARENT_KI",
                take_profit=3.0,
                stop_loss=2.0,
                poll_seconds=0.01,
                side="BUY",
                quantity=1,
            )

        # Should log interruption
        assert mock_logger.info.called

    def test_emulate_oco_sell_side(self):
        """Emulation reverses action for SELL side (closing action becomes BUY)."""
        broker = Mock()
        contract = Mock(symbol="SPY")
        
        quotes = [Mock(last=2.50), Mock(last=3.00)]  # Hits TP
        broker.market_data = Mock(side_effect=quotes)
        broker.place_order = Mock(return_value="BUY_CLOSE_123")

        with patch('src.bot.execution.logger'):
            emulate_oco(
                broker,
                contract,
                parent_order_id="SELL_PARENT",
                take_profit=3.0,
                stop_loss=None,
                poll_seconds=0.01,
                side="SELL",  # <-- Note: SELL side
                quantity=2,
            )

        # Closing action should be BUY (opposite of SELL)
        call_args = broker.place_order.call_args[0][0]
        assert call_args.action == "BUY"
        assert call_args.quantity == 2
