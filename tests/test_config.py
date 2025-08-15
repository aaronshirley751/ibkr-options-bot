from src.bot.settings import Settings


def test_settings_defaults():
    s = Settings()
    assert s.broker.host == "127.0.0.1"
