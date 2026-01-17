from __future__ import annotations

from datetime import date, datetime, timedelta

from app.domain.entities import TaskEntity
from app.domain.enums import RecurrenceRule, TaskStatus
from app.domain.filters import TaskFilters
from app.infra.repository import TaskRepository


class TaskService:
    def __init__(self, repo: TaskRepository) -> None:
        self._repo = repo

    def list_tasks(self, filters: TaskFilters) -> list[TaskEntity]:
        return self._repo.list_tasks(filters)

    def get_task(self, task_id: int) -> TaskEntity | None:
        return self._repo.get_task(task_id)

    def create_task(self, data: dict) -> TaskEntity:
        return self._repo.create_task(self._normalize_data(data))

    def update_task(self, task_id: int, data: dict) -> TaskEntity | None:
        normalized = self._normalize_data(data)
        status = normalized.get("status")
        if status == TaskStatus.DONE.value and "completed_at" not in normalized:
            normalized["completed_at"] = datetime.utcnow()
        if status and status != TaskStatus.DONE.value:
            normalized["completed_at"] = None
        if status == TaskStatus.ARCHIVED.value and "archived_at" not in normalized:
            normalized["archived_at"] = datetime.utcnow()
        if status and status != TaskStatus.ARCHIVED.value:
            normalized["archived_at"] = None
        return self._repo.update_task(task_id, normalized)

    def delete_task(self, task_id: int) -> None:
        self._repo.delete_task(task_id)

    def mark_done(self, task_id: int) -> TaskEntity | None:
        task = self.update_task(task_id, {"status": TaskStatus.DONE.value})
        if not task:
            return None
        self._handle_recurrence(task)
        return task

    def archive_task(self, task_id: int) -> TaskEntity | None:
        return self.update_task(task_id, {"status": TaskStatus.ARCHIVED.value})

    def get_stats(self) -> dict[str, int]:
        return self._repo.get_stats()

    def list_reminders(self) -> list[TaskEntity]:
        return self._repo.list_due_reminders()

    def get_weekly_stats(self, weeks: int = 8) -> list[dict]:
        return self._repo.get_weekly_stats(weeks)

    def reorder_tasks(self, task_ids: list[int]) -> None:
        self._repo.reorder_tasks(task_ids)

    def _normalize_data(self, data: dict) -> dict:
        normalized = dict(data)
        if "status" in normalized and isinstance(normalized["status"], TaskStatus):
            normalized["status"] = normalized["status"].value
        return normalized

    def _handle_recurrence(self, task: TaskEntity) -> None:
        if not task.recurrence_rule or not task.due_date:
            return

        rule = task.recurrence_rule
        interval = max(int(task.recurrence_interval or 1), 1)
        next_due = self._next_due_date(task.due_date, rule, interval)

        if task.recurrence_end_date and next_due > task.recurrence_end_date:
            return

        self._repo.create_task({
            "title": task.title,
            "description": task.description,
            "status": TaskStatus.INBOX.value,
            "priority": task.priority,
            "due_date": next_due,
            "tags": task.tags,
            "recurrence_rule": rule,
            "recurrence_interval": interval,
            "recurrence_end_date": task.recurrence_end_date,
        })

    @staticmethod
    def _next_due_date(current: date, rule: str, interval: int) -> date:
        if rule == RecurrenceRule.DAILY.value:
            return current + timedelta(days=interval)
        if rule == RecurrenceRule.WEEKLY.value:
            return current + timedelta(weeks=interval)
        if rule == RecurrenceRule.MONTHLY.value:
            return _add_months(current, interval)
        return current + timedelta(days=interval)


def _add_months(base: date, months: int) -> date:
    year = base.year + (base.month - 1 + months) // 12
    month = (base.month - 1 + months) % 12 + 1
    day = min(base.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day
