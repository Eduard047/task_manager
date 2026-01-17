from __future__ import annotations

from enum import IntEnum, StrEnum


class TaskStatus(StrEnum):
    INBOX = "inbox"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"


class RecurrenceRule(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class PriorityLevel(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
