from __future__ import annotations

from PySide6.QtCore import QMimeData, QSize, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.domain.entities import SubtaskEntity, TaskEntity

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
    def __init__(self, task: TaskEntity, subtask_titles: list[str] | None = None):
        super().__init__()
        self.task = task

        self.setObjectName("TaskCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(64)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        title_text = task.title.strip() if task.title else "Без назви"
        title = QLabel(title_text)
        title.setProperty("class", "task-title")
        title.setWordWrap(True)
        title.setMinimumWidth(0)
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        meta_parts = []
        if task.due_date:
            meta_parts.append(f"Дедлайн: {task.due_date.strftime('%d.%m.%Y')}")
        if task.tags:
            meta_parts.append(f"Теги: {task.tags}")
        if subtask_titles:
            numbered = [
                f"{index}) {title}" for index, title in enumerate(subtask_titles, start=1)
            ]
            meta_parts.append(f"Підзадачі: {'; '.join(numbered)}")

        status_value = task.status.value if hasattr(task.status, "value") else str(task.status or "")
        status_label = STATUS_LABELS.get(status_value, status_value)
        if status_label:
            meta_parts.append(f"Статус: {status_label}")

        meta = QLabel(" | ".join(meta_parts) if meta_parts else "Без деталей")
        meta.setProperty("class", "task-meta")
        meta.setWordWrap(True)
        meta.setMinimumWidth(0)
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
        header.setSpacing(8)
        header.addWidget(title, 1)
        header.addWidget(priority, 0, Qt.AlignTop)

        layout.addLayout(header)
        layout.addWidget(meta)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


class TaskItemContainer(QWidget):
    def __init__(self, task_widget: TaskItemWidget, h_margin: int = 12, parent=None):
        super().__init__(parent)
        self.task_widget = task_widget
        layout = QHBoxLayout(self)
        layout.setContentsMargins(h_margin, 0, h_margin, 0)
        layout.setSpacing(0)
        layout.addWidget(task_widget)

    @property
    def task(self) -> TaskEntity:
        return self.task_widget.task

    def set_selected(self, selected: bool) -> None:
        self.task_widget.set_selected(selected)


class SubtaskItemWidget(QWidget):
    def __init__(self, subtask: SubtaskEntity, on_toggle, on_title_update, on_delete, parent=None):
        super().__init__(parent)
        self.subtask_id = subtask.id
        self._title_value = subtask.title
        self._on_toggle = on_toggle
        self._on_title_update = on_title_update
        self._on_delete = on_delete

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.done_check = QCheckBox()
        self.done_check.setChecked(subtask.is_done)
        self.done_check.toggled.connect(self._handle_toggle)

        self.title_input = QLineEdit(subtask.title)
        self.title_input.setPlaceholderText("Subtask title")
        self.title_input.editingFinished.connect(self._handle_title_commit)

        self.delete_button = QPushButton("Remove")
        self.delete_button.setProperty("variant", "ghost")
        self.delete_button.clicked.connect(self._handle_delete)

        layout.addWidget(self.done_check)
        layout.addWidget(self.title_input, 1)
        layout.addWidget(self.delete_button)

    def _handle_toggle(self, checked: bool) -> None:
        if self.subtask_id is None:
            return
        self._on_toggle(self.subtask_id, checked)

    def _handle_title_commit(self) -> None:
        if self.subtask_id is None:
            return
        title = self.title_input.text().strip()
        if not title:
            self.title_input.setText(self._title_value)
            return
        if title != self._title_value:
            self._title_value = title
            self._on_title_update(self.subtask_id, title)

    def _handle_delete(self) -> None:
        if self.subtask_id is None:
            return
        self._on_delete(self.subtask_id)


class TaskListWidget(QListWidget):
    def __init__(self, on_reorder=None, parent=None):
        super().__init__(parent)
        self._on_reorder = on_reorder
        self._h_margin = 12
        self._v_margin = 8
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._update_viewport_margins()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.sync_item_sizes()

    def _update_viewport_margins(self) -> None:
        scrollbar_width = self.verticalScrollBar().width() or self.verticalScrollBar().sizeHint().width()
        right_margin = self._h_margin + (scrollbar_width if self.verticalScrollBar().isVisible() else 0)
        self.setViewportMargins(self._h_margin, self._v_margin, right_margin, self._v_margin)

    def sync_item_sizes(self) -> None:
        self._update_viewport_margins()
        viewport_width = self.viewport().width()
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if widget:
                widget.setMinimumWidth(viewport_width)
                widget.setMaximumWidth(viewport_width)
                widget.adjustSize()
                hint = widget.sizeHint()
                item.setSizeHint(QSize(viewport_width, hint.height()))
                widget.resize(viewport_width, hint.height())

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
        self._h_margin = 12
        self._v_margin = 10
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._update_viewport_margins()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.sync_item_sizes()

    def _update_viewport_margins(self) -> None:
        scrollbar_width = self.verticalScrollBar().width() or self.verticalScrollBar().sizeHint().width()
        right_margin = self._h_margin + (scrollbar_width if self.verticalScrollBar().isVisible() else 0)
        self.setViewportMargins(self._h_margin, self._v_margin, right_margin, self._v_margin)

    def sync_item_sizes(self) -> None:
        self._update_viewport_margins()
        viewport_width = self.viewport().width()
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if widget:
                widget.setMinimumWidth(viewport_width)
                widget.setMaximumWidth(viewport_width)
                widget.adjustSize()
                hint = widget.sizeHint()
                item.setSizeHint(QSize(viewport_width, hint.height()))
                widget.resize(viewport_width, hint.height())

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
