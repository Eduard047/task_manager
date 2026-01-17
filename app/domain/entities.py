from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from .enums import TaskStatus


@dataclass(frozen=True)
class TaskEntity:
    id: int | None
    title: str
    description: str
    status: TaskStatus
    priority: int
    due_date: Optional[date]
    tags: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    recurrence_rule: str | None
    recurrence_interval: int
    recurrence_end_date: Optional[date]
    archived_at: Optional[datetime]
    sort_order: int
