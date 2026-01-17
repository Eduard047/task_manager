from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from app.domain.entities import TaskEntity
from app.domain.enums import RecurrenceRule, TaskStatus
from app.domain.filters import TaskFilters
from app.services.task_service import TaskService


class FakeRepo:
    def __init__(self) -> None:
        self.tasks: list[TaskEntity] = []
        self._id = 1

    def list_tasks(self, filters: TaskFilters) -> list[TaskEntity]:
        return self.tasks

    def get_task(self, task_id: int) -> TaskEntity | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def create_task(self, data: dict) -> TaskEntity:
        task = TaskEntity(
            id=self._id,
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "inbox")),
            priority=data.get("priority", 2),
            due_date=data.get("due_date"),
            tags=data.get("tags", ""),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            completed_at=None,
            recurrence_rule=data.get("recurrence_rule"),
            recurrence_interval=data.get("recurrence_interval", 1),
            recurrence_end_date=data.get("recurrence_end_date"),
            archived_at=None,
            sort_order=1,
        )
        self.tasks.append(task)
        self._id += 1
        return task

    def update_task(self, task_id: int, data: dict) -> TaskEntity | None:
        task = self.get_task(task_id)
        if not task:
            return None
        updated = replace(
            task,
            status=TaskStatus(data.get("status", task.status.value)),
            completed_at=data.get("completed_at", task.completed_at),
            archived_at=data.get("archived_at", task.archived_at),
        )
        self.tasks = [updated if t.id == task_id else t for t in self.tasks]
        return updated

    def delete_task(self, task_id: int) -> None:
        self.tasks = [t for t in self.tasks if t.id != task_id]

    def get_stats(self) -> dict[str, int]:
        return {
            "total": len(self.tasks),
            "in_progress": 0,
            "done": 0,
            "overdue": 0,
            "due_today": 0,
        }

    def list_due_reminders(self) -> list[TaskEntity]:
        return []


def test_recurring_task_creates_next_instance() -> None:
    repo = FakeRepo()
    service = TaskService(repo)

    task = repo.create_task({
        "title": "Daily",
        "status": "inbox",
        "priority": 2,
        "due_date": date(2026, 1, 1),
        "recurrence_rule": RecurrenceRule.DAILY.value,
        "recurrence_interval": 1,
    })

    service.mark_done(task.id)

    assert len(repo.tasks) == 2
    next_task = repo.tasks[1]
    assert next_task.due_date == date(2026, 1, 2)
