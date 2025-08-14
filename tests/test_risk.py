from src.bot.risk import position_size, guard_daily_loss


def test_position_size_basic():
    # equity 100k, risk 1%, stop 20%, premium 2.5 -> floor((100000*0.01)/(2.5*0.2)) = floor(1000/0.5)=floor(2000)=2000
    size = position_size(100000, 0.01, 0.2, 2.5)
    assert isinstance(size, int)
    assert size >= 1


def test_guard_daily_loss():
    # start 100k, now 90k, max_daily_loss_pct 0.09 -> loss 10% >= 9% -> True
    assert guard_daily_loss(100000, 90000, 0.09) is True
    # small loss does not trigger
    assert guard_daily_loss(100000, 99500, 0.1) is False
