from pathlib import Path
from typing import Optional
from pydantic import BaseSettings
import yaml

class Settings(BaseSettings):
    ibkr_host: str = "127.0.0.1"
    ibkr_port_paper: int = 4002
    ibkr_port_live: int = 4001
    ibkr_client_id: int = 1
    ibkr_account: Optional[str] = None
    paper_mode: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = Path.cwd() / ".env"
        env_file_encoding = "utf-8"


def load_settings_from_yaml(path: str) -> Settings:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Settings(**data.get("bot", {}))

settings = Settings()
