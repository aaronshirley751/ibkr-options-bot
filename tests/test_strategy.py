from src.bot.strategy.scalp_rules import scalp_signal


def test_scalp_signal_hold():
    sig = scalp_signal([1,2,3])
    assert sig["action"] == "HOLD"
