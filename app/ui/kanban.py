from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidgetItem, QVBoxLayout

from app.domain.enums import TaskStatus
from app.domain.filters import TaskFilters
from app.services.task_service import TaskService

from .widgets import KanbanListWidget, TaskItemContainer, TaskItemWidget


class KanbanDialog(QDialog):
    def __init__(self, service: TaskService, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Kanban")
        self.resize(1200, 700)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.columns: dict[str, KanbanListWidget] = {}
        for status_key, title in [
            (TaskStatus.INBOX.value, "Вхідні"),
            (TaskStatus.IN_PROGRESS.value, "У роботі"),
            (TaskStatus.DONE.value, "Виконано"),
            (TaskStatus.ARCHIVED.value, "Архів"),
        ]:
            column = QVBoxLayout()
            label = QLabel(title)
            label.setProperty("class", "panel-title")
            list_widget = KanbanListWidget(status_key, self.on_drop_status, self.on_reorder)
            list_widget.setObjectName("KanbanList")
            column.addWidget(label)
            column.addWidget(list_widget)
            layout.addLayout(column, 1)
            self.columns[status_key] = list_widget

        self.refresh()

    def refresh(self) -> None:
        for status_key, list_widget in self.columns.items():
            list_widget.clear()
            tasks = self.service.list_tasks(TaskFilters(filter_key=status_key))
            task_ids = [task.id for task in tasks if task.id is not None]
            subtask_titles = self.service.get_subtask_titles(task_ids)
            for task in tasks:
                item = QListWidgetItem()
                list_widget.addItem(item)
                item.setData(Qt.UserRole, task.id)
                task_widget = TaskItemWidget(task, subtask_titles.get(task.id))
                widget = TaskItemContainer(task_widget)
                item.setSizeHint(widget.sizeHint())
                list_widget.setItemWidget(item, widget)
            list_widget.sync_item_sizes()

    def on_drop_status(self, task_id: int, status_key: str) -> None:
        self.service.update_task(task_id, {"status": status_key})
        self.refresh()

    def on_reorder(self, task_ids: list[int]) -> None:
        self.service.reorder_tasks(task_ids)
        self.refresh()
