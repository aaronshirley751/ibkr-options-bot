"""Unit tests for data/options.py - options chain handling and selection."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from src.bot.data.options import (
    nearest_atm_strike,
    nearest_friday,
    pick_weekly_option,
    _strike_from_moneyness,
)


class TestNearestFriday:
    """Test Friday date calculation."""

    def test_nearest_friday_when_monday(self):
        """Returns same week's Friday from Monday."""
        monday = datetime(2025, 12, 8, tzinfo=timezone.utc)  # Monday
        result = nearest_friday(monday)
        assert result.weekday() == 4  # Friday
        assert result.day == 12  # Same week

    def test_nearest_friday_when_friday(self):
        """Returns same Friday if input is Friday."""
        friday = datetime(2025, 12, 12, tzinfo=timezone.utc)  # Friday
        result = nearest_friday(friday)
        assert result.weekday() == 4
        assert result.day == 12

    def test_nearest_friday_when_sunday(self):
        """Returns next week's Friday from Sunday."""
        sunday = datetime(2025, 12, 14, tzinfo=timezone.utc)  # Sunday
        result = nearest_friday(sunday)
        assert result.weekday() == 4
        assert result.day == 19  # Next Friday

    def test_nearest_friday_when_saturday(self):
        """Returns next week's Friday from Saturday."""
        saturday = datetime(2025, 12, 13, tzinfo=timezone.utc)  # Saturday
        result = nearest_friday(saturday)
        assert result.weekday() == 4
        assert result.day == 19

    def test_nearest_friday_across_month_boundary(self):
        """Handles Friday calculation across month boundary."""
        thursday = datetime(2025, 12, 31, tzinfo=timezone.utc)  # Dec 31, Thursday
        result = nearest_friday(thursday)
        assert result.weekday() == 4
        assert result.month == 1  # January
        assert result.day == 3  # Next Friday in January


class TestNearestATMStrike:
    """Test ATM strike selection."""

    def test_nearest_atm_strike_exact_match(self):
        """Returns strike exactly matching last price."""
        strikes = [450, 455, 460]
        result = nearest_atm_strike(455.0, strikes)
        assert result == 455

    def test_nearest_atm_strike_between_two(self):
        """Returns closest strike to last price."""
        strikes = [450, 460]
        result = nearest_atm_strike(452.0, strikes)
        assert result == 450

    def test_nearest_atm_strike_closer_to_higher(self):
        """Returns higher strike when closer."""
        strikes = [450, 460]
        result = nearest_atm_strike(458.0, strikes)
        assert result == 460

    def test_nearest_atm_strike_empty_list(self):
        """Returns None for empty strikes list."""
        result = nearest_atm_strike(100.0, [])
        assert result is None

    def test_nearest_atm_strike_single_strike(self):
        """Returns single strike."""
        result = nearest_atm_strike(100.0, [95.0])
        assert result == 95.0

    def test_nearest_atm_strike_far_above(self):
        """Handles price far above all strikes."""
        strikes = [100, 105, 110]
        result = nearest_atm_strike(200.0, strikes)
        assert result == 110  # Closest, even if far

    def test_nearest_atm_strike_far_below(self):
        """Handles price far below all strikes."""
        strikes = [100, 105, 110]
        result = nearest_atm_strike(10.0, strikes)
        assert result == 100  # Closest, even if far


class TestStrikeFromMoneyness:
    """Test strike selection by moneyness (ATM/ITM/OTM)."""

    def test_strike_from_moneyness_atm(self):
        """ATM returns nearest strike to last price."""
        strikes = [450, 455, 460]
        result = _strike_from_moneyness(453.0, strikes, "atm")
        assert result == 455  # Nearest to 453

    def test_strike_from_moneyness_itmp1(self):
        """ITMP1 returns strike just above last price (for calls)."""
        strikes = [450, 455, 460, 465]
        result = _strike_from_moneyness(453.0, strikes, "itmp1")
        assert result == 455  # First strike above 453

    def test_strike_from_moneyness_otmp1(self):
        """OTMP1 returns strike just below last price (for calls)."""
        strikes = [450, 455, 460, 465]
        result = _strike_from_moneyness(453.0, strikes, "otmp1")
        assert result == 450  # First strike below 453

    def test_strike_from_moneyness_invalid_type(self):
        """Returns None for invalid moneyness type."""
        strikes = [450, 455, 460]
        result = _strike_from_moneyness(453.0, strikes, "invalid")
        assert result is None

    def test_strike_from_moneyness_itmp1_at_boundary(self):
        """ITMP1 when price equals a strike."""
        strikes = [450, 455, 460]
        result = _strike_from_moneyness(455.0, strikes, "itmp1")
        assert result == 460  # Next strike above 455

    def test_strike_from_moneyness_otmp1_at_boundary(self):
        """OTMP1 when price equals a strike."""
        strikes = [450, 455, 460]
        result = _strike_from_moneyness(455.0, strikes, "otmp1")
        assert result == 450  # Previous strike below 455

    def test_strike_from_moneyness_atm_empty(self):
        """Returns None for empty strikes."""
        result = _strike_from_moneyness(100.0, [], "atm")
        assert result is None


class TestPickWeeklyOption:
    """Test weekly option selection logic."""

    def create_stub_broker(self, chain=None, quote=None):
        """Helper to create a mock broker with option chain and quotes."""
        broker = Mock()
        broker.option_chain = Mock(return_value=chain or [])
        broker.market_data = Mock(return_value=quote or Mock(last=100.0, bid=2.45, ask=2.55, volume=5000))
        return broker

    def create_option_contract(self, strike, right="C", expiry="20251219", symbol="SPY"):
        """Helper to create an option contract."""
        contract = Mock()
        contract.strike = strike
        contract.right = right
        contract.expiry = expiry
        contract.symbol = f"{symbol}{right}{strike}"
        return contract

    def test_pick_weekly_option_call_atm(self):
        """Picks ATM call with adequate liquidity."""
        contracts = [
            self.create_option_contract(450, "C"),
            self.create_option_contract(455, "C"),
            self.create_option_contract(460, "C"),
        ]
        broker = self.create_stub_broker(chain=contracts)

        result = pick_weekly_option(
            broker,
            underlying="SPY",
            right="C",
            last_price=453.0,
            moneyness="atm",
            min_volume=1000,
            max_spread_pct=2.0,
        )

        assert result is not None
        assert result.strike == 455  # Closest to 453

    def test_pick_weekly_option_put_atm(self):
        """Picks ATM put with adequate liquidity."""
        contracts = [
            self.create_option_contract(450, "P"),
            self.create_option_contract(455, "P"),
            self.create_option_contract(460, "P"),
        ]
        broker = self.create_stub_broker(chain=contracts)

        result = pick_weekly_option(
            broker,
            underlying="SPY",
            right="P",
            last_price=453.0,
            moneyness="atm",
            min_volume=1000,
            max_spread_pct=2.0,
        )

        assert result is not None
        assert result.strike == 455
        assert result.right == "P"

    def test_pick_weekly_option_empty_chain(self):
        """Returns None when no options available."""
        broker = self.create_stub_broker(chain=[])

        result = pick_weekly_option(
            broker,
            underlying="SPY",
            right="C",
            last_price=450.0,
            moneyness="atm",
            min_volume=100,
            max_spread_pct=2.0,
        )

        assert result is None

    def test_pick_weekly_option_all_illiquid(self):
        """Returns None when all options fail liquidity check."""
        # Create contracts but broker returns illiquid quotes
        contracts = [
            self.create_option_contract(450, "C"),
            self.create_option_contract(455, "C"),
        ]
        
        illiquid_quote = Mock(last=2.50, bid=2.0, ask=5.0, volume=10)  # Wide spread, low volume
        broker = self.create_stub_broker(chain=contracts, quote=illiquid_quote)

        result = pick_weekly_option(
            broker,
            underlying="SPY",
            right="C",
            last_price=453.0,
            moneyness="atm",
            min_volume=100,
            max_spread_pct=1.0,  # Strict spread requirement
        )

        assert result is None

    def test_pick_weekly_option_selects_liquid_option(self):
        """Picks option meeting liquidity requirements."""
        contracts = [
            self.create_option_contract(450, "C"),
            self.create_option_contract(455, "C"),
            self.create_option_contract(460, "C"),
        ]
        
        liquid_quote = Mock(last=2.50, bid=2.48, ask=2.52, volume=50000)
        broker = self.create_stub_broker(chain=contracts, quote=liquid_quote)

        result = pick_weekly_option(
            broker,
            underlying="SPY",
            right="C",
            last_price=453.0,
            moneyness="atm",
            min_volume=1000,
            max_spread_pct=2.0,
        )

        assert result is not None
        assert result.strike == 455

    def test_pick_weekly_option_itmp1(self):
        """Picks ITM P1 (slightly ITM) call."""
        contracts = [
            self.create_option_contract(450, "C"),
            self.create_option_contract(455, "C"),
            self.create_option_contract(460, "C"),
        ]
        broker = self.create_stub_broker(chain=contracts)

        result = pick_weekly_option(
            broker,
            underlying="SPY",
            right="C",
            last_price=453.0,
            moneyness="itmp1",
            min_volume=1000,
            max_spread_pct=2.0,
        )

        # ITMP1 should be first strike above price = 455
        assert result is not None
        assert result.strike >= 453.0

    def test_pick_weekly_option_otmp1(self):
        """Picks OTM P1 (slightly OTM) call."""
        contracts = [
            self.create_option_contract(450, "C"),
            self.create_option_contract(455, "C"),
            self.create_option_contract(460, "C"),
        ]
        broker = self.create_stub_broker(chain=contracts)

        result = pick_weekly_option(
            broker,
            underlying="SPY",
            right="C",
            last_price=453.0,
            moneyness="otmp1",
            min_volume=1000,
            max_spread_pct=2.0,
        )

        # OTMP1 should be first strike below price = 450
        assert result is not None
        assert result.strike <= 453.0

    def test_pick_weekly_option_ties_by_spread(self):
        """Breaks ties by tightest spread."""
        # Both strikes have same distance from price
        contracts = [
            self.create_option_contract(450, "C"),
            self.create_option_contract(460, "C"),  # Both 5 away from 455
        ]
        
        def market_data_side_effect(contract_or_symbol):
            if contract_or_symbol.strike == 450:
                return Mock(last=2.45, bid=2.44, ask=2.46, volume=10000)  # Tight spread
            else:
                return Mock(last=2.55, bid=2.50, ask=2.60, volume=10000)  # Wide spread
        
        broker = Mock()
        broker.option_chain = Mock(return_value=contracts)
        broker.market_data = Mock(side_effect=market_data_side_effect)

        result = pick_weekly_option(
            broker,
            underlying="SPY",
            right="C",
            last_price=455.0,
            moneyness="atm",
            min_volume=1000,
            max_spread_pct=3.0,
        )

        # Should pick 450 with tighter spread
        assert result is not None
        assert result.strike == 450
