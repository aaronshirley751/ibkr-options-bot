from src.bot.settings import Settings, get_settings, BrokerSettings, RiskSettings


def test_settings_defaults():
    """Test Pydantic model defaults (without loading yaml or env)."""
    # Test individual model defaults directly to avoid env/yaml loading
    broker = BrokerSettings()
    assert broker.host == "127.0.0.1"
    assert broker.port == 4002
    assert broker.client_id == 1
    
    risk = RiskSettings()
    assert risk.reset_daily_guard_on_start is False  # New field default
    assert risk.max_risk_pct_per_trade == 0.01
    assert risk.max_daily_loss_pct == 0.15


def test_settings_load_from_yaml():
    """Test loading actual settings from yaml + env (may have custom values)."""
    s = get_settings()
    # Verify structure exists and types are correct
    assert isinstance(s.broker.host, str)
    assert isinstance(s.broker.port, int)
    assert isinstance(s.risk.reset_daily_guard_on_start, bool)
    assert s.dry_run is True  # Safety check: dry_run must be True in deployment config
