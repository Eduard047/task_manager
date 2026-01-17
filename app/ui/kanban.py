from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidgetItem, QVBoxLayout

from app.domain.enums import TaskStatus
from app.domain.filters import TaskFilters
from app.services.task_service import TaskService

from .widgets import KanbanListWidget, TaskItemWidget


class KanbanDialog(QDialog):
    def __init__(self, service: TaskService, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Kanban")
        self.resize(980, 520)

        layout = QHBoxLayout(self)
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
            for task in tasks:
                item = QListWidgetItem()
                list_widget.addItem(item)
                item.setData(Qt.UserRole, task.id)
                widget = TaskItemWidget(task)
                item.setSizeHint(widget.sizeHint())
                list_widget.setItemWidget(item, widget)

    def on_drop_status(self, task_id: int, status_key: str) -> None:
        self.service.update_task(task_id, {"status": status_key})
        self.refresh()

    def on_reorder(self, task_ids: list[int]) -> None:
        self.service.reorder_tasks(task_ids)
        self.refresh()
