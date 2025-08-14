from src.bot.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.ibkr_host == "127.0.0.1"
