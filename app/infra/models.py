from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text

from .db import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="inbox", index=True)
    priority = Column(Integer, nullable=False, default=2)
    due_date = Column(Date, nullable=True)
    tags = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    recurrence_rule = Column(String(20), nullable=True)
    recurrence_interval = Column(Integer, nullable=False, default=1)
    recurrence_end_date = Column(Date, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)


class SubtaskModel(Base):
    __tablename__ = "subtasks"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    is_done = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    sort_order = Column(Integer, nullable=False, default=0)
