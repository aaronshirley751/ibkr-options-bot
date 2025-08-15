from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BrokerSettings(BaseModel):
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=4002, ge=1, le=65535)
    client_id: int = Field(default=1, ge=0)
    read_only: bool = Field(default=False)


class RiskSettings(BaseModel):
    max_risk_pct_per_trade: float = Field(default=0.01, ge=0.0, le=1.0)
    max_daily_loss_pct: float = Field(default=0.15, ge=0.0, le=1.0)
    take_profit_pct: float = Field(default=0.30, ge=0.0, le=5.0)
    stop_loss_pct: float = Field(default=0.20, ge=0.0, le=1.0)
    whale_alloc_pct: float = Field(default=0.15, ge=0.0, le=1.0)


class ScheduleSettings(BaseModel):
    interval_seconds: int = Field(default=180, ge=10, le=3600)


class OptionsSettings(BaseModel):
    expiry: str = Field(default="weekly")
    moneyness: str = Field(default="atm")
    max_spread_pct: float = Field(default=2.0, ge=0.0, le=100.0)
    min_volume: int = Field(default=100, ge=0)

    @field_validator("moneyness")
    @classmethod
    def _validate_moneyness(cls, v: str) -> str:
        allowed = {"atm", "itmp1", "otmp1"}
        if v not in allowed:
            raise ValueError(f"moneyness must be one of {sorted(allowed)}")
        return v


class MonitoringSettings(BaseModel):
    alerts_enabled: bool = Field(default=True)
    heartbeat_url: Optional[str] = Field(default=None)
    slack_webhook_url: Optional[str] = Field(default=None)
    telegram_bot_token: Optional[str] = Field(default=None)
    telegram_chat_id: Optional[str] = Field(default=None)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="__", extra="ignore")

    # top-level
    symbols: List[str] = ["SPY", "QQQ"]
    mode: str = "growth"  # growth | hybrid

    # nested
    broker: BrokerSettings = BrokerSettings()
    risk: RiskSettings = RiskSettings()
    schedule: ScheduleSettings = ScheduleSettings()
    options: OptionsSettings = OptionsSettings()
    monitoring: MonitoringSettings = MonitoringSettings()

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, v: str) -> str:
        allowed = {"growth", "hybrid"}
        if v not in allowed:
            raise ValueError(f"mode must be one of {sorted(allowed)}")
        return v

    @classmethod
    def load(cls, yaml_path: str | Path = "configs/settings.yaml") -> "Settings":
        # Load YAML first, then overlay environment variables via BaseSettings
        base: dict = {}
        p = Path(yaml_path)
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                base = yaml.safe_load(f) or {}
        # Instantiate with YAML as initial data; env overrides will apply automatically
        return cls(**base)


def get_settings(yaml_path: str | Path = "configs/settings.yaml") -> Settings:
    return Settings.load(yaml_path)
