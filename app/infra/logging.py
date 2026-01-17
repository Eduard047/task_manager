from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import SETTINGS, PROJECT_ROOT


def setup_logging() -> None:
    log_dir = PROJECT_ROOT / SETTINGS.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "task_manager.log"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=SETTINGS.log_level.upper(),
        handlers=[file_handler, console_handler],
    )
