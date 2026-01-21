from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, or_, select

from app.domain.entities import SubtaskEntity, TaskEntity
from app.domain.filters import TaskFilters
from app.domain.enums import TaskStatus

from .db import SessionLocal
from .models import SubtaskModel, TaskModel

STATUS_DONE = TaskStatus.DONE.value
STATUS_ARCHIVED = TaskStatus.ARCHIVED.value


def _to_entity(model: TaskModel) -> TaskEntity:
    return TaskEntity(
        id=model.id,
        title=model.title,
        description=model.description,
        status=TaskStatus(model.status),
        priority=model.priority,
        due_date=model.due_date,
        tags=model.tags,
        created_at=model.created_at,
        updated_at=model.updated_at,
        completed_at=model.completed_at,
        recurrence_rule=model.recurrence_rule,
        recurrence_interval=model.recurrence_interval,
        recurrence_end_date=model.recurrence_end_date,
        archived_at=model.archived_at,
        sort_order=model.sort_order,
    )


def _to_subtask_entity(model: SubtaskModel) -> SubtaskEntity:
    return SubtaskEntity(
        id=model.id,
        task_id=model.task_id,
        title=model.title,
        is_done=model.is_done,
        created_at=model.created_at,
        updated_at=model.updated_at,
        sort_order=model.sort_order,
    )


def _apply_filters(stmt, filters: TaskFilters) -> object:
    today = date.today()

    if filters.filter_key == "inbox":
        stmt = stmt.where(TaskModel.status == TaskStatus.INBOX.value)
    elif filters.filter_key == "in_progress":
        stmt = stmt.where(TaskModel.status == TaskStatus.IN_PROGRESS.value)
    elif filters.filter_key == "done":
        stmt = stmt.where(TaskModel.status == STATUS_DONE)
    elif filters.filter_key == "archived":
        stmt = stmt.where(TaskModel.status == STATUS_ARCHIVED)
    elif filters.filter_key == "overdue":
        stmt = stmt.where(
            TaskModel.due_date.is_not(None),
            TaskModel.due_date < today,
            TaskModel.status.notin_([STATUS_DONE, STATUS_ARCHIVED]),
        )
    elif filters.filter_key == "upcoming":
        horizon = today + timedelta(days=7)
        stmt = stmt.where(
            TaskModel.due_date.is_not(None),
            TaskModel.due_date.between(today, horizon),
            TaskModel.status.notin_([STATUS_DONE, STATUS_ARCHIVED]),
        )

    if filters.due_on:
        stmt = stmt.where(TaskModel.due_date == filters.due_on)

    if filters.search:
        pattern = f"%{filters.search}%"
        stmt = stmt.where(
            or_(
                TaskModel.title.ilike(pattern),
                TaskModel.description.ilike(pattern),
                TaskModel.tags.ilike(pattern),
            )
        )

    return stmt


class TaskRepository:
    def list_tasks(self, filters: TaskFilters) -> list[TaskEntity]:
        with SessionLocal() as session:
            stmt = select(TaskModel)
            stmt = _apply_filters(stmt, filters)
            stmt = stmt.order_by(
                TaskModel.sort_order.asc(),
                TaskModel.due_date.is_(None),
                TaskModel.due_date.asc(),
                TaskModel.priority.desc(),
                TaskModel.created_at.desc(),
            )
            return [_to_entity(task) for task in session.scalars(stmt)]

    def get_task(self, task_id: int) -> Optional[TaskEntity]:
        with SessionLocal() as session:
            task = session.get(TaskModel, task_id)
            return _to_entity(task) if task else None

    def create_task(self, data: dict) -> TaskEntity:
        with SessionLocal() as session:
            if data.get("sort_order") is None:
                status = data.get("status", TaskStatus.INBOX.value)
                data["sort_order"] = self._next_sort_order(session, status)
            task = TaskModel(**data)
            session.add(task)
            session.commit()
            session.refresh(task)
            return _to_entity(task)

    def list_subtasks(self, task_id: int) -> list[SubtaskEntity]:
        with SessionLocal() as session:
            stmt = (
                select(SubtaskModel)
                .where(SubtaskModel.task_id == task_id)
                .order_by(
                    SubtaskModel.sort_order.asc(),
                    SubtaskModel.created_at.asc(),
                )
            )
            return [_to_subtask_entity(subtask) for subtask in session.scalars(stmt)]

    def get_subtask_titles(self, task_ids: list[int]) -> dict[int, list[str]]:
        if not task_ids:
            return {}
        with SessionLocal() as session:
            stmt = (
                select(SubtaskModel.task_id, SubtaskModel.title)
                .where(SubtaskModel.task_id.in_(task_ids))
                .order_by(
                    SubtaskModel.task_id.asc(),
                    SubtaskModel.sort_order.asc(),
                    SubtaskModel.created_at.asc(),
                )
            )
            titles: dict[int, list[str]] = {}
            for row in session.execute(stmt):
                title = (row.title or "").strip()
                if not title:
                    continue
                titles.setdefault(int(row.task_id), []).append(title)
            return titles

    def create_subtask(self, task_id: int, title: str) -> SubtaskEntity:
        with SessionLocal() as session:
            sort_order = self._next_subtask_sort_order(session, task_id)
            subtask = SubtaskModel(
                task_id=task_id,
                title=title,
                is_done=False,
                sort_order=sort_order,
            )
            session.add(subtask)
            session.commit()
            session.refresh(subtask)
            return _to_subtask_entity(subtask)

    def update_subtask(self, subtask_id: int, data: dict) -> Optional[SubtaskEntity]:
        with SessionLocal() as session:
            subtask = session.get(SubtaskModel, subtask_id)
            if not subtask:
                return None

            for key, value in data.items():
                setattr(subtask, key, value)
            session.commit()
            session.refresh(subtask)
            return _to_subtask_entity(subtask)

    def delete_subtask(self, subtask_id: int) -> None:
        with SessionLocal() as session:
            subtask = session.get(SubtaskModel, subtask_id)
            if not subtask:
                return
            session.delete(subtask)
            session.commit()

    def update_task(self, task_id: int, data: dict) -> Optional[TaskEntity]:
        with SessionLocal() as session:
            task = session.get(TaskModel, task_id)
            if not task:
                return None

            if "status" in data and data.get("sort_order") is None:
                new_status = data["status"]
                data["sort_order"] = self._next_sort_order(session, new_status)

            for key, value in data.items():
                setattr(task, key, value)
            session.commit()
            session.refresh(task)
            return _to_entity(task)

    def reorder_tasks(self, task_ids: list[int]) -> None:
        if not task_ids:
            return
        with SessionLocal() as session:
            tasks = (
                session.query(TaskModel)
                .filter(TaskModel.id.in_(task_ids))
                .all()
            )
            order_map = {task_id: index for index, task_id in enumerate(task_ids, start=1)}
            for task in tasks:
                task.sort_order = order_map.get(task.id, task.sort_order)
            session.commit()

    def delete_task(self, task_id: int) -> None:
        with SessionLocal() as session:
            task = session.get(TaskModel, task_id)
            if not task:
                return
            session.query(SubtaskModel).filter(SubtaskModel.task_id == task_id).delete(
                synchronize_session=False
            )
            session.delete(task)
            session.commit()

    def get_stats(self) -> dict[str, int]:
        with SessionLocal() as session:
            total = session.scalar(select(func.count()).select_from(TaskModel)) or 0
            in_progress = session.scalar(
                select(func.count())
                .select_from(TaskModel)
                .where(TaskModel.status == TaskStatus.IN_PROGRESS.value)
            ) or 0
            done = session.scalar(
                select(func.count()).select_from(TaskModel).where(TaskModel.status == STATUS_DONE)
            ) or 0
            today = date.today()
            overdue = session.scalar(
                select(func.count())
                .select_from(TaskModel)
                .where(
                    TaskModel.due_date.is_not(None),
                    TaskModel.due_date < today,
                    TaskModel.status.notin_([STATUS_DONE, STATUS_ARCHIVED]),
                )
            ) or 0
            due_today = session.scalar(
                select(func.count())
                .select_from(TaskModel)
                .where(TaskModel.due_date == today)
            ) or 0
            return {
                "total": total,
                "in_progress": in_progress,
                "done": done,
                "overdue": overdue,
                "due_today": due_today,
            }

    def list_due_reminders(self) -> list[TaskEntity]:
        today = date.today()
        with SessionLocal() as session:
            stmt = (
                select(TaskModel)
                .where(
                    TaskModel.due_date.is_not(None),
                    TaskModel.due_date <= today,
                    TaskModel.status.notin_([STATUS_DONE, STATUS_ARCHIVED]),
                )
                .order_by(TaskModel.due_date.asc())
            )
            return [_to_entity(task) for task in session.scalars(stmt)]

    def get_weekly_stats(self, weeks: int = 8) -> list[dict]:
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        start_week = current_week_start - timedelta(weeks=weeks - 1)
        start_dt = datetime.combine(start_week, datetime.min.time())

        with SessionLocal() as session:
            created_rows = session.execute(
                select(
                    func.date_trunc("week", TaskModel.created_at).label("week"),
                    func.count().label("count"),
                )
                .where(TaskModel.created_at >= start_dt)
                .group_by("week")
            ).all()

            completed_rows = session.execute(
                select(
                    func.date_trunc("week", TaskModel.completed_at).label("week"),
                    func.count().label("count"),
                )
                .where(TaskModel.completed_at.is_not(None), TaskModel.completed_at >= start_dt)
                .group_by("week")
            ).all()

        created_map = {
            row.week.date(): row.count for row in created_rows if row.week is not None
        }
        completed_map = {
            row.week.date(): row.count for row in completed_rows if row.week is not None
        }

        weekly = []
        for offset in range(weeks):
            week_start = start_week + timedelta(weeks=offset)
            weekly.append(
                {
                    "week_start": week_start,
                    "created": created_map.get(week_start, 0),
                    "completed": completed_map.get(week_start, 0),
                }
            )
        return weekly

    @staticmethod
    def _next_sort_order(session, status: str) -> int:
        max_order = session.scalar(
            select(func.max(TaskModel.sort_order)).where(TaskModel.status == status)
        )
        return (max_order or 0) + 1

    @staticmethod
    def _next_subtask_sort_order(session, task_id: int) -> int:
        max_order = session.scalar(
            select(func.max(SubtaskModel.sort_order)).where(SubtaskModel.task_id == task_id)
        )
        return (max_order or 0) + 1
