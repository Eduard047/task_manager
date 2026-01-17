from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.domain.entities import TaskEntity

STATUS_LABELS = {
    "inbox": "Вхідні",
    "in_progress": "У роботі",
    "done": "Виконано",
    "archived": "Архів",
}

PRIORITY_OPTIONS = [
    ("Низький", 1),
    ("Середній", 2),
    ("Високий", 3),
    ("Критичний", 4),
]

PRIORITY_COLORS = {
    1: "#7CC4A1",
    2: "#E0B25B",
    3: "#E57B63",
    4: "#E24A4A",
}

DROP_STATUSES = {"inbox", "in_progress", "done", "archived"}


def _task_id_from_mime(mime: QMimeData) -> int | None:
    if not mime.hasText():
        return None
    text = mime.text()
    if not text.startswith("task:"):
        return None
    try:
        return int(text.split(":", 1)[1])
    except ValueError:
        return None


class TaskItemWidget(QWidget):
    def __init__(self, task: TaskEntity):
        super().__init__()
        self.task = task

        self.setObjectName("TaskCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        title = QLabel(task.title)
        title.setProperty("class", "task-title")
        title.setWordWrap(True)
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        meta_parts = []
        if task.due_date:
            meta_parts.append(f"Дедлайн: {task.due_date.strftime('%d.%m.%Y')}")
        if task.tags:
            meta_parts.append(f"Теги: {task.tags}")
        status_label = STATUS_LABELS.get(
            task.status.value if hasattr(task.status, "value") else str(task.status),
            "",
        )
        if status_label:
            meta_parts.append(f"Статус: {status_label}")

        meta = QLabel(" | ".join(meta_parts) if meta_parts else "Без деталей")
        meta.setProperty("class", "task-meta")
        meta.setWordWrap(True)
        meta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        priority_label = next(
            (label for label, value in PRIORITY_OPTIONS if value == task.priority),
            "Невідомо",
        )
        priority = QLabel(priority_label)
        priority.setProperty("class", "task-priority")
        priority.setStyleSheet(
            f"background-color: {PRIORITY_COLORS.get(task.priority, '#9CA3AF')};"
        )
        priority.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(priority)

        layout.addLayout(header)
        layout.addWidget(meta)


class TaskListWidget(QListWidget):
    def __init__(self, on_reorder=None, parent=None):
        super().__init__(parent)
        self._on_reorder = on_reorder
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def startDrag(self, supportedActions: Qt.DropActions) -> None:  # type: ignore[name-defined]
        item = self.currentItem()
        if not item:
            return
        task_id = item.data(Qt.UserRole)
        if not task_id:
            return
        mime = QMimeData()
        mime.setText(f"task:{task_id}")
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        super().dropEvent(event)
        if self._on_reorder:
            ids = [self.item(i).data(Qt.UserRole) for i in range(self.count())]
            ids = [task_id for task_id in ids if task_id]
            self._on_reorder(ids)

    def set_reorder_enabled(self, enabled: bool) -> None:
        self.setDragEnabled(True)
        self.setAcceptDrops(enabled)
        self.setDropIndicatorShown(enabled)
        mode = QAbstractItemView.InternalMove if enabled else QAbstractItemView.DragOnly
        self.setDragDropMode(mode)


class FilterListWidget(QListWidget):
    def __init__(self, on_drop_status, parent=None):
        super().__init__(parent)
        self._on_drop_status = on_drop_status
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if _task_id_from_mime(event.mimeData()) is not None:
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if _task_id_from_mime(event.mimeData()) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        task_id = _task_id_from_mime(event.mimeData())
        if task_id is None:
            return
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item = self.itemAt(pos)
        if not item:
            return
        status_key = item.data(Qt.UserRole)
        if status_key in DROP_STATUSES:
            self._on_drop_status(task_id, status_key)
            event.acceptProposedAction()


class KanbanListWidget(QListWidget):
    def __init__(self, status_key: str, on_drop_status, on_reorder, parent=None):
        super().__init__(parent)
        self.status_key = status_key
        self._on_drop_status = on_drop_status
        self._on_reorder = on_reorder
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def startDrag(self, supportedActions: Qt.DropActions) -> None:  # type: ignore[name-defined]
        item = self.currentItem()
        if not item:
            return
        task_id = item.data(Qt.UserRole)
        if not task_id:
            return
        mime = QMimeData()
        mime.setText(f"task:{task_id}")
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if _task_id_from_mime(event.mimeData()) is not None:
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if _task_id_from_mime(event.mimeData()) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        task_id = _task_id_from_mime(event.mimeData())
        if task_id is not None and event.source() is not self:
            self._on_drop_status(task_id, self.status_key)
            event.acceptProposedAction()
            return

        super().dropEvent(event)
        self._on_reorder(self._current_ids())

    def _current_ids(self) -> list[int]:
        ids = [self.item(i).data(Qt.UserRole) for i in range(self.count())]
        return [task_id for task_id in ids if task_id]
