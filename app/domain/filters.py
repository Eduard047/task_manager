from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class TaskFilters:
    filter_key: str = "all"
    search: str | None = None
    due_on: Optional[date] = None
