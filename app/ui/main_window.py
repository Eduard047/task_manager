from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QDate, QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMessageBox,
    QAbstractSpinBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import SETTINGS
from app.domain.entities import SubtaskEntity, TaskEntity
from app.domain.enums import RecurrenceRule, TaskStatus
from app.domain.filters import TaskFilters
from app.infra.repository import TaskRepository
from app.services.task_service import TaskService

from .dialogs import PomodoroDialog, StatsDialog
from .kanban import KanbanDialog
from .widgets import (
    FilterListWidget,
    PRIORITY_OPTIONS,
    STATUS_LABELS,
    SubtaskItemWidget,
    TaskItemContainer,
    TaskItemWidget,
    TaskListWidget,
)

FILTERS = [
    ("Усі", "all"),
    ("Вхідні", "inbox"),
    ("У роботі", "in_progress"),
    ("Прострочені", "overdue"),
    ("Найближчі 7 днів", "upcoming"),
    ("Виконано", "done"),
    ("Архів", "archived"),
]

STATUS_OPTIONS = [
    ("Вхідні", TaskStatus.INBOX.value),
    ("У роботі", TaskStatus.IN_PROGRESS.value),
    ("Виконано", TaskStatus.DONE.value),
    ("Архів", TaskStatus.ARCHIVED.value),
]

RECURRENCE_OPTIONS = [
    ("Без повтору", None),
    ("Щодня", RecurrenceRule.DAILY.value),
    ("Щотижня", RecurrenceRule.WEEKLY.value),
    ("Щомісяця", RecurrenceRule.MONTHLY.value),
]

CSV_HEADERS = [
    "title",
    "description",
    "status",
    "priority",
    "due_date",
    "tags",
    "recurrence_rule",
    "recurrence_interval",
    "recurrence_end_date",
]

REORDER_FILTERS = {"inbox", "in_progress", "done", "archived"}


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Forge")
        self.resize(1280, 760)

        self.service = TaskService(TaskRepository())

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        self.sidebar = self._build_sidebar()
        self.center = self._build_center()
        self.detail = self._build_detail_panel()

        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.center)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)
        splitter.setSizes([240, 620, 420])

        self.current_task_id: int | None = None
        self.current_filter = "all"
        self.due_on: date | None = None

        self.refresh_tasks()
        self._show_reminders()

        QShortcut(QKeySequence("Ctrl+N"), self, self.new_task)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_task)

    def _build_sidebar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Sidebar")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Фільтри")
        title.setProperty("class", "sidebar-title")
        layout.addWidget(title)

        self.filter_list = FilterListWidget(self.on_status_drop)
        self.filter_list.setObjectName("FilterList")
        self.filter_list.setSpacing(6)
        self.filter_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filter_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for label, key in FILTERS:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, key)
            self.filter_list.addItem(item)
        self.filter_list.setCurrentRow(0)
        self.filter_list.currentItemChanged.connect(self.on_filter_change)
        self._fit_filter_list_height()

        layout.addWidget(self.filter_list)

        calendar_title = QLabel("Календар")
        calendar_title.setProperty("class", "sidebar-title")
        layout.addWidget(calendar_title)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setNavigationBarVisible(True)
        self.calendar.setMinimumHeight(240)
        self.calendar.setMaximumHeight(280)
        self.calendar.selectionChanged.connect(self.on_calendar_selected)
        layout.addWidget(self.calendar)

        clear_date = QPushButton("Скинути дату")
        clear_date.setProperty("variant", "secondary")
        clear_date.clicked.connect(self.clear_calendar_filter)
        layout.addWidget(clear_date)

        layout.addStretch()
        return frame

    def _fit_filter_list_height(self) -> None:
        if self.filter_list.count() == 0:
            return
        row_height = self.filter_list.sizeHintForRow(0)
        if row_height <= 0:
            row_height = 32
        height = row_height * self.filter_list.count()
        height += self.filter_list.spacing() * (self.filter_list.count() - 1)
        height += self.filter_list.frameWidth() * 2
        self.filter_list.setFixedHeight(height)

    def _build_center(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("CenterPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header_title = QLabel("Мої задачі")
        header_title.setProperty("class", "panel-title")
        self.stats_label = QLabel("")
        self.stats_label.setProperty("class", "stats-badge")
        header.addWidget(header_title)
        header.addStretch()
        header.addWidget(self.stats_label)

        action_bar = QFrame()
        action_bar.setObjectName("ActionBar")
        action_layout = QVBoxLayout(action_bar)
        action_layout.setContentsMargins(12, 10, 12, 10)
        action_layout.setSpacing(8)

        primary_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Пошук за назвою, тегами або описом")
        self.search_input.setMinimumWidth(220)
        self.search_input.textChanged.connect(self.refresh_tasks)

        add_button = QPushButton("Нова задача")
        add_button.clicked.connect(self.new_task)

        kanban_button = QPushButton("Kanban")
        kanban_button.setProperty("variant", "secondary")
        kanban_button.clicked.connect(self.open_kanban)

        primary_row.addWidget(self.search_input, 1)
        primary_row.addWidget(add_button)
        primary_row.addWidget(kanban_button)

        secondary_row = QHBoxLayout()
        pomodoro_button = QPushButton("Pomodoro")
        pomodoro_button.setProperty("variant", "secondary")
        pomodoro_button.clicked.connect(self.open_pomodoro)

        export_csv_button = QPushButton("Експорт CSV")
        export_csv_button.setProperty("variant", "ghost")
        export_csv_button.clicked.connect(self.export_csv)

        import_csv_button = QPushButton("Імпорт CSV")
        import_csv_button.setProperty("variant", "ghost")
        import_csv_button.clicked.connect(self.import_csv)

        export_ics_button = QPushButton("Експорт ICS")
        export_ics_button.setProperty("variant", "ghost")
        export_ics_button.clicked.connect(self.export_ics)

        report_button = QPushButton("Звіти")
        report_button.setProperty("variant", "secondary")
        report_button.clicked.connect(self.open_reports)

        secondary_row.addWidget(pomodoro_button)
        secondary_row.addWidget(export_csv_button)
        secondary_row.addWidget(import_csv_button)
        secondary_row.addWidget(export_ics_button)
        secondary_row.addWidget(report_button)
        secondary_row.addStretch()

        action_layout.addLayout(primary_row)
        action_layout.addLayout(secondary_row)

        self.task_list = TaskListWidget(on_reorder=self.on_reorder_tasks)
        self.task_list.setObjectName("TaskList")
        self.task_list.setSpacing(10)
        self.task_list.currentItemChanged.connect(self.on_task_selected)

        layout.addLayout(header)
        layout.addWidget(action_bar)
        layout.addWidget(self.task_list)

        return frame

    def _build_detail_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("DetailPanel")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("DetailScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(8)

        title = QLabel("Деталі")
        title.setProperty("class", "panel-title")

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Назва задачі")

        self.description_input = QTextEdit()
        self.description_input.setObjectName("DescriptionInput")
        self.description_input.setPlaceholderText("Опис, чекліст, контекст")
        self.description_input.setMinimumHeight(120)
        self.description_input.setMaximumHeight(140)

        subtasks_label = QLabel("Підзадачі")
        subtasks_label.setProperty("class", "section-title")

        self.subtasks_summary = QLabel("0/0")
        self.subtasks_summary.setProperty("class", "stats")

        subtasks_header = QHBoxLayout()
        subtasks_header.addWidget(subtasks_label)
        subtasks_header.addStretch()
        subtasks_header.addWidget(self.subtasks_summary)

        self.subtask_input = QLineEdit()
        self.subtask_input.setPlaceholderText("Додати підзадачу")
        self.subtask_input.returnPressed.connect(self.add_subtask)

        self.subtask_add_button = QPushButton("Додати")
        self.subtask_add_button.setProperty("variant", "secondary")
        self.subtask_add_button.clicked.connect(self.add_subtask)

        subtask_row = QHBoxLayout()
        subtask_row.addWidget(self.subtask_input, 1)
        subtask_row.addWidget(self.subtask_add_button)

        self.subtasks_scroll = QScrollArea()
        self.subtasks_scroll.setWidgetResizable(True)
        self.subtasks_scroll.setFrameShape(QFrame.NoFrame)
        self.subtasks_scroll.setObjectName("SubtasksScroll")
        self.subtasks_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.subtasks_container = QWidget()
        self.subtasks_layout = QVBoxLayout(self.subtasks_container)
        self.subtasks_layout.setContentsMargins(0, 0, 0, 0)
        self.subtasks_layout.setSpacing(6)
        self.subtasks_layout.addStretch()
        self.subtasks_scroll.setWidget(self.subtasks_container)
        self.subtasks_scroll.setMinimumHeight(110)
        self.subtasks_scroll.setMaximumHeight(160)

        self.status_combo = QComboBox()
        for label, key in STATUS_OPTIONS:
            self.status_combo.addItem(label, key)

        self.priority_combo = QComboBox()
        for label, value in PRIORITY_OPTIONS:
            self.priority_combo.addItem(label, value)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Теги через кому")

        self.due_toggle = QPushButton("Дедлайн вимкнено")
        self.due_toggle.setCheckable(True)
        self.due_toggle.setProperty("variant", "secondary")
        self.due_toggle.setObjectName("DueToggle")
        self.due_toggle.toggled.connect(self.on_due_toggled)

        self.due_input = QDateEdit()
        self.due_input.setCalendarPopup(True)
        self.due_input.setDate(QDate.currentDate())
        self.due_input.setEnabled(False)

        recurrence_title = QLabel("Повторення")
        recurrence_title.setProperty("class", "section-title")

        self.recurrence_combo = QComboBox()
        for label, value in RECURRENCE_OPTIONS:
            self.recurrence_combo.addItem(label, value)

        self.recurrence_interval = QSpinBox()
        self.recurrence_interval.setRange(1, 30)
        self.recurrence_interval.setValue(1)
        self.recurrence_interval.setSuffix("x")
        self.recurrence_interval.setButtonSymbols(QAbstractSpinBox.UpDownArrows)

        self.recurrence_end_check = QCheckBox("Кінець повтору")
        self.recurrence_end_check.toggled.connect(self.on_recurrence_end_toggled)

        self.recurrence_end_date = QDateEdit()
        self.recurrence_end_date.setCalendarPopup(True)
        self.recurrence_end_date.setDate(QDate.currentDate())
        self.recurrence_end_date.setEnabled(False)

        self.save_button = QPushButton("Зберегти")
        self.save_button.clicked.connect(self.save_task)

        self.done_button = QPushButton("Позначити виконаною")
        self.done_button.setProperty("variant", "secondary")
        self.done_button.clicked.connect(self.mark_done)

        self.archive_button = QPushButton("В архів")
        self.archive_button.setProperty("variant", "ghost")
        self.archive_button.clicked.connect(self.archive_task)

        self.delete_button = QPushButton("Видалити")
        self.delete_button.setProperty("variant", "danger")
        self.delete_button.clicked.connect(self.delete_task)

        content_layout.addWidget(title)
        content_layout.addWidget(self.title_input)
        content_layout.addWidget(self.description_input)

        content_layout.addSpacing(6)
        content_layout.addLayout(subtasks_header)
        content_layout.addLayout(subtask_row)
        content_layout.addWidget(self.subtasks_scroll)
        content_layout.addSpacing(6)

        content_layout.addWidget(QLabel("Статус"))
        content_layout.addWidget(self.status_combo)

        content_layout.addWidget(QLabel("Пріоритет"))
        content_layout.addWidget(self.priority_combo)

        content_layout.addWidget(QLabel("Теги"))
        content_layout.addWidget(self.tags_input)

        content_layout.addWidget(self.due_toggle)
        content_layout.addWidget(self.due_input)

        content_layout.addWidget(recurrence_title)
        content_layout.addWidget(self.recurrence_combo)
        content_layout.addWidget(QLabel("Інтервал"))
        content_layout.addWidget(self.recurrence_interval)
        content_layout.addWidget(self.recurrence_end_check)
        content_layout.addWidget(self.recurrence_end_date)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.save_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.done_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.archive_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        actions.addWidget(self.save_button, 1)
        actions.addWidget(self.done_button, 1)
        actions.addWidget(self.archive_button, 1)
        content_layout.addLayout(actions)
        content_layout.addWidget(self.delete_button)
        content_layout.addStretch()

        scroll.setWidget(content)
        frame_layout.addWidget(scroll)

        return frame

    def refresh_tasks(self) -> None:
        search = self.search_input.text().strip() if self.search_input else ""
        filters = TaskFilters(
            filter_key=self.current_filter,
            search=search or None,
            due_on=self.due_on,
        )
        tasks = self.service.list_tasks(filters)
        task_ids = [task.id for task in tasks if task.id is not None]
        subtask_titles = self.service.get_subtask_titles(task_ids)
        self.task_list.clear()

        for task in tasks:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, task.id)
            task_widget = TaskItemWidget(task, subtask_titles.get(task.id))
            widget = TaskItemContainer(task_widget)
            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, widget)
            item.setSizeHint(widget.sizeHint())

        self.task_list.set_reorder_enabled(self.current_filter in REORDER_FILTERS)

        stats = self.service.get_stats()
        self.stats_label.setText(
            f"Всього: {stats['total']} • У роботі: {stats['in_progress']} • "
            f"Виконано: {stats['done']} • Прострочено: {stats['overdue']} • "
            f"Сьогодні: {stats['due_today']}"
        )

        if tasks:
            self.task_list.setCurrentRow(0)
        else:
            self.current_task_id = None
            self.clear_form()
        self.task_list.sync_item_sizes()

    def on_filter_change(self, current: QListWidgetItem) -> None:
        if not current:
            return
        self.current_filter = current.data(Qt.UserRole)
        self.refresh_tasks()

    def on_status_drop(self, task_id: int, status_key: str) -> None:
        self.service.update_task(task_id, {"status": status_key})
        self.refresh_tasks()
        self._auto_export_ics()

    def on_reorder_tasks(self, task_ids: list[int]) -> None:
        if self.current_filter not in REORDER_FILTERS:
            return
        self.service.reorder_tasks(task_ids)
        self.refresh_tasks()

    def on_calendar_selected(self) -> None:
        selected = self.calendar.selectedDate().toPython()
        self.due_on = selected
        self.refresh_tasks()

    def clear_calendar_filter(self) -> None:
        self.due_on = None
        self.refresh_tasks()

    def on_task_selected(
        self,
        current: QListWidgetItem,
        previous: QListWidgetItem | None = None,
    ) -> None:
        if previous:
            self._set_task_item_selected(previous, False)
        if not current:
            return
        self._set_task_item_selected(current, True)
        task_id = current.data(Qt.UserRole)
        task = self._get_task_from_list(task_id)
        if task:
            self.current_task_id = task.id
            self.populate_form(task)

    def _set_task_item_selected(self, item: QListWidgetItem, selected: bool) -> None:
        widget = self.task_list.itemWidget(item)
        if isinstance(widget, TaskItemWidget):
            widget.set_selected(selected)
        elif hasattr(widget, "set_selected"):
            widget.set_selected(selected)

    def _get_task_from_list(self, task_id: int) -> TaskEntity | None:
        for index in range(self.task_list.count()):
            item = self.task_list.item(index)
            if item.data(Qt.UserRole) == task_id:
                widget = self.task_list.itemWidget(item)
                if isinstance(widget, TaskItemWidget):
                    return widget.task
                if hasattr(widget, "task"):
                    return widget.task
        return None

    def populate_form(self, task: TaskEntity) -> None:
        self.title_input.setText(task.title)
        self.description_input.setPlainText(task.description)

        status_index = self.status_combo.findData(task.status.value)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)

        priority_index = self.priority_combo.findData(task.priority)
        if priority_index >= 0:
            self.priority_combo.setCurrentIndex(priority_index)

        self.tags_input.setText(task.tags)

        if task.due_date:
            self.due_toggle.setChecked(True)
            self.due_input.setEnabled(True)
            self.due_input.setDate(QDate(task.due_date.year, task.due_date.month, task.due_date.day))
        else:
            self.due_toggle.setChecked(False)
            self.due_input.setEnabled(False)

        recurrence_index = self.recurrence_combo.findData(task.recurrence_rule)
        if recurrence_index >= 0:
            self.recurrence_combo.setCurrentIndex(recurrence_index)

        self.recurrence_interval.setValue(task.recurrence_interval or 1)

        if task.recurrence_end_date:
            self.recurrence_end_check.setChecked(True)
            self.recurrence_end_date.setEnabled(True)
            self.recurrence_end_date.setDate(
                QDate(task.recurrence_end_date.year, task.recurrence_end_date.month, task.recurrence_end_date.day)
            )
        else:
            self.recurrence_end_check.setChecked(False)
            self.recurrence_end_date.setEnabled(False)

        self._sync_done_button(task)
        self._set_subtasks_enabled(True)
        if task.id is not None:
            self.refresh_subtasks(task.id)

    def refresh_subtasks(self, task_id: int) -> None:
        subtasks = self.service.list_subtasks(task_id)
        self._render_subtasks(subtasks)

    def add_subtask(self) -> None:
        title = self.subtask_input.text().strip()
        if not title:
            return
        if self.current_task_id is None:
            self.save_task()
        if self.current_task_id is None:
            QMessageBox.warning(self, "Потрібна задача", "Спочатку збережи задачу.")
            return
        try:
            self.service.create_subtask(self.current_task_id, title)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Помилка", f"Не вдалося додати підзадачу.\n{exc}")
            return
        self.subtask_input.clear()
        self.refresh_subtasks(self.current_task_id)

    def on_subtask_toggle(self, subtask_id: int, is_done: bool) -> None:
        self.service.update_subtask(subtask_id, {"is_done": is_done})
        if self.current_task_id is not None:
            self.refresh_subtasks(self.current_task_id)

    def on_subtask_title_update(self, subtask_id: int, title: str) -> None:
        self.service.update_subtask(subtask_id, {"title": title})
        if self.current_task_id is not None:
            self.refresh_subtasks(self.current_task_id)

    def on_subtask_delete(self, subtask_id: int) -> None:
        self.service.delete_subtask(subtask_id)
        if self.current_task_id is not None:
            self.refresh_subtasks(self.current_task_id)

    def _render_subtasks(self, subtasks: list[SubtaskEntity]) -> None:
        self._clear_subtasks()
        for subtask in subtasks:
            widget = SubtaskItemWidget(
                subtask,
                self.on_subtask_toggle,
                self.on_subtask_title_update,
                self.on_subtask_delete,
            )
            self.subtasks_layout.insertWidget(self.subtasks_layout.count() - 1, widget)
        self._update_subtask_summary(subtasks)
        self.subtasks_scroll.setVisible(bool(subtasks))

    def _clear_subtasks(self) -> None:
        while self.subtasks_layout.count() > 1:
            item = self.subtasks_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _update_subtask_summary(self, subtasks: list[SubtaskEntity]) -> None:
        total = len(subtasks)
        done = sum(1 for subtask in subtasks if subtask.is_done)
        if total:
            self.subtasks_summary.setText(f"{done}/{total}")
        else:
            self.subtasks_summary.setText("0/0")

    def _set_subtasks_enabled(self, enabled: bool) -> None:
        self.subtask_input.setEnabled(enabled)
        self.subtask_add_button.setEnabled(enabled)
        self.subtasks_scroll.setEnabled(enabled)

    def clear_form(self) -> None:
        self.title_input.clear()
        self.description_input.clear()
        self.status_combo.setCurrentIndex(0)
        self.priority_combo.setCurrentIndex(1)
        self.tags_input.clear()
        self.due_toggle.setChecked(False)
        self.due_input.setEnabled(False)
        self.due_input.setDate(QDate.currentDate())
        self.recurrence_combo.setCurrentIndex(0)
        self.recurrence_interval.setValue(1)
        self.recurrence_end_check.setChecked(False)
        self.recurrence_end_date.setEnabled(False)
        self.recurrence_end_date.setDate(QDate.currentDate())
        self._sync_done_button(None)
        self._render_subtasks([])
        self._set_subtasks_enabled(True)

    def _sync_done_button(self, task: TaskEntity | None) -> None:
        if task is None:
            self.done_button.setEnabled(False)
            self.done_button.setText("Позначити виконаною")
            self.done_button.setProperty("variant", "secondary")
        elif task.status == TaskStatus.DONE:
            self.done_button.setEnabled(True)
            self.done_button.setText("Повернути в роботу")
            self.done_button.setProperty("variant", "warning")
        else:
            self.done_button.setEnabled(True)
            self.done_button.setText("Позначити виконаною")
            self.done_button.setProperty("variant", "secondary")

        self.done_button.style().unpolish(self.done_button)
        self.done_button.style().polish(self.done_button)

    def new_task(self) -> None:
        self.current_task_id = None
        self.clear_form()
        self.title_input.setFocus()

    def on_due_toggled(self, checked: bool) -> None:
        self.due_input.setEnabled(checked)
        self.due_toggle.setText("Дедлайн активний" if checked else "Дедлайн вимкнено")

    def on_recurrence_end_toggled(self, checked: bool) -> None:
        self.recurrence_end_date.setEnabled(checked)

    def save_task(self) -> None:
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Потрібна назва", "Вкажи назву задачі.")
            return

        data = {
            "title": title,
            "description": self.description_input.toPlainText().strip(),
            "status": self.status_combo.currentData(),
            "priority": self.priority_combo.currentData(),
            "tags": self.tags_input.text().strip(),
            "due_date": self.due_input.date().toPython() if self.due_toggle.isChecked() else None,
            "recurrence_rule": self.recurrence_combo.currentData(),
            "recurrence_interval": self.recurrence_interval.value(),
            "recurrence_end_date": self.recurrence_end_date.date().toPython()
            if self.recurrence_end_check.isChecked()
            else None,
        }

        if self.current_task_id is None:
            task = self.service.create_task(data)
            self.current_task_id = task.id
        else:
            self.service.update_task(self.current_task_id, data)

        self.refresh_tasks()
        self._auto_export_ics()

    def mark_done(self) -> None:
        if self.current_task_id is None:
            return
        task = self._get_task_from_list(self.current_task_id)
        if task is None:
            task = self.service.get_task(self.current_task_id)
        if task and task.status == TaskStatus.DONE:
            self.service.update_task(self.current_task_id, {"status": TaskStatus.IN_PROGRESS.value})
        else:
            self.service.mark_done(self.current_task_id)
        self.refresh_tasks()
        self._auto_export_ics()

    def archive_task(self) -> None:
        if self.current_task_id is None:
            return
        self.service.archive_task(self.current_task_id)
        self.refresh_tasks()
        self._auto_export_ics()

    def delete_task(self) -> None:
        if self.current_task_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "Підтвердження",
            "Точно видалити задачу?",
        )
        if confirm != QMessageBox.Yes:
            return
        self.service.delete_task(self.current_task_id)
        self.refresh_tasks()
        self._auto_export_ics()

    def open_pomodoro(self) -> None:
        dialog = PomodoroDialog(self)
        dialog.exec()

    def open_kanban(self) -> None:
        dialog = KanbanDialog(self.service, self)
        dialog.exec()
        self.refresh_tasks()

    def open_reports(self) -> None:
        data = self.service.get_weekly_stats(weeks=8)
        dialog = StatsDialog(data, self)
        dialog.exec()

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Експорт CSV",
            str(Path.home() / "tasks.csv"),
            "CSV Files (*.csv)",
        )
        if not path:
            return
        tasks = self.service.list_tasks(TaskFilters(filter_key="all"))
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for task in tasks:
                writer.writerow(
                    {
                        "title": task.title,
                        "description": task.description,
                        "status": task.status.value,
                        "priority": task.priority,
                        "due_date": task.due_date.isoformat() if task.due_date else "",
                        "tags": task.tags,
                        "recurrence_rule": task.recurrence_rule or "",
                        "recurrence_interval": task.recurrence_interval,
                        "recurrence_end_date": task.recurrence_end_date.isoformat()
                        if task.recurrence_end_date
                        else "",
                    }
                )
        QMessageBox.information(self, "Готово", "CSV файл збережено.")

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Імпорт CSV",
            str(Path.home()),
            "CSV Files (*.csv)",
        )
        if not path:
            return
        created = 0
        with open(path, "r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                title = (row.get("title") or "").strip()
                if not title:
                    continue
                status = (row.get("status") or TaskStatus.INBOX.value).strip()
                if status not in STATUS_LABELS:
                    status = TaskStatus.INBOX.value
                due_date = _parse_date(row.get("due_date"))
                end_date = _parse_date(row.get("recurrence_end_date"))
                try:
                    priority = int(row.get("priority") or 2)
                except ValueError:
                    priority = 2
                try:
                    interval = int(row.get("recurrence_interval") or 1)
                except ValueError:
                    interval = 1

                self.service.create_task(
                    {
                        "title": title,
                        "description": (row.get("description") or "").strip(),
                        "status": status,
                        "priority": priority,
                        "due_date": due_date,
                        "tags": (row.get("tags") or "").strip(),
                        "recurrence_rule": (row.get("recurrence_rule") or None),
                        "recurrence_interval": interval,
                        "recurrence_end_date": end_date,
                    }
                )
                created += 1
        self.refresh_tasks()
        self._auto_export_ics()
        QMessageBox.information(self, "Готово", f"Імпортовано задач: {created}.")

    def export_ics(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Експорт ICS",
            str(Path.home() / "tasks.ics"),
            "ICS Files (*.ics)",
        )
        if not path:
            return
        self._write_ics(Path(path))
        QMessageBox.information(self, "Готово", "ICS файл збережено.")

    def _auto_export_ics(self) -> None:
        if not SETTINGS.ics_export_path:
            return
        self._write_ics(Path(SETTINGS.ics_export_path))

    def _write_ics(self, path: Path) -> None:
        tasks = self.service.list_tasks(TaskFilters(filter_key="all"))
        now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Task Forge//UA",
            "CALSCALE:GREGORIAN",
        ]
        for task in tasks:
            if not task.due_date:
                continue
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:task-{task.id}@taskforge",
                    f"DTSTAMP:{now}",
                    f"DTSTART;VALUE=DATE:{task.due_date.strftime('%Y%m%d')}",
                    f"SUMMARY:{_escape_ics(task.title)}",
                    f"DESCRIPTION:{_escape_ics(task.description)}",
                    "END:VEVENT",
                ]
            )
        lines.append("END:VCALENDAR")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _show_reminders(self) -> None:
        reminders = self.service.list_reminders()
        if not reminders:
            return
        lines = []
        for task in reminders[:5]:
            due_label = task.due_date.strftime("%d.%m.%Y") if task.due_date else "без дати"
            status_label = STATUS_LABELS.get(task.status.value, task.status.value)
            lines.append(f"- {task.title} (до {due_label}, {status_label})")
        message = "Нагадування про задачі з дедлайном:\n" + "\n".join(lines)
        QMessageBox.information(self, "Нагадування", message)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _escape_ics(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
