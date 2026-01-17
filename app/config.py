from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

def _resolve_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = _resolve_project_root()


def load_env() -> None:
    env_name = os.getenv("APP_ENV", "development")
    candidates = [Path.cwd(), PROJECT_ROOT]
    for base in candidates:
        env_path = base / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            break

    for base in candidates:
        env_specific = base / f".env.{env_name}"
        if env_specific.exists():
            load_dotenv(env_specific, override=True)
            break


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str = "INFO"
    log_dir: str = "logs"
    pomodoro_work_min: int = 25
    pomodoro_break_min: int = 5
    ics_export_path: str | None = None


load_env()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Create a .env file with your connection string.")

SETTINGS = Settings(
    database_url=DATABASE_URL,
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir=os.getenv("LOG_DIR", "logs"),
    pomodoro_work_min=int(os.getenv("POMODORO_WORK_MIN", "25")),
    pomodoro_break_min=int(os.getenv("POMODORO_BREAK_MIN", "5")),
    ics_export_path=os.getenv("ICS_EXPORT_PATH", "").strip() or None,
)
