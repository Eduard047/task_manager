from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.config import SETTINGS


class PomodoroDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pomodoro")
        self.setObjectName("PomodoroDialog")
        self.setFixedSize(360, 260)

        self.work_seconds = SETTINGS.pomodoro_work_min * 60
        self.break_seconds = SETTINGS.pomodoro_break_min * 60
        self.remaining = self.work_seconds
        self.on_break = False

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

        self.label = QLabel(self._format_time())
        self.label.setObjectName("PomodoroTime")

        self.phase_label = QLabel("Робота")
        self.phase_label.setObjectName("PomodoroPhase")

        self.meta_label = QLabel(
            f"{SETTINGS.pomodoro_work_min}/{SETTINGS.pomodoro_break_min} хв"
        )
        self.meta_label.setObjectName("PomodoroMeta")

        self.progress = QProgressBar()
        self.progress.setObjectName("PomodoroProgress")
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)

        self.start_button = QPushButton("Старт")
        self.start_button.clicked.connect(self.start)

        self.pause_button = QPushButton("Пауза")
        self.pause_button.setProperty("variant", "secondary")
        self.pause_button.clicked.connect(self.pause)

        self.reset_button = QPushButton("Скинути")
        self.reset_button.setProperty("variant", "ghost")
        self.reset_button.clicked.connect(self.reset)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.reset_button)

        card = QFrame()
        card.setObjectName("PomodoroCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.addWidget(self.phase_label)
        top_row.addStretch()
        top_row.addWidget(self.meta_label)

        card_layout.addLayout(top_row)
        card_layout.addWidget(self.label, alignment=Qt.AlignLeft)
        card_layout.addWidget(self.progress)
        card_layout.addLayout(buttons)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(card)

        self._update_phase()
        self._update_progress()

    def start(self) -> None:
        if not self.timer.isActive():
            self.timer.start()

    def pause(self) -> None:
        self.timer.stop()

    def reset(self) -> None:
        self.timer.stop()
        self.on_break = False
        self.remaining = self.work_seconds
        self._update_phase()
        self.label.setText(self._format_time())
        self._update_progress()

    def _tick(self) -> None:
        self.remaining -= 1
        if self.remaining <= 0:
            self.on_break = not self.on_break
            self.remaining = self.break_seconds if self.on_break else self.work_seconds
            self._update_phase()
        self.label.setText(self._format_time())
        self._update_progress()

    def _update_phase(self) -> None:
        phase = "break" if self.on_break else "work"
        self.phase_label.setText("Перерва" if self.on_break else "Робота")
        self.phase_label.setProperty("phase", phase)
        self.progress.setProperty("phase", phase)
        self.phase_label.style().unpolish(self.phase_label)
        self.phase_label.style().polish(self.phase_label)
        self.progress.style().unpolish(self.progress)
        self.progress.style().polish(self.progress)

    def _update_progress(self) -> None:
        total = self.break_seconds if self.on_break else self.work_seconds
        value = int((self.remaining / total) * 100) if total else 0
        self.progress.setValue(max(0, min(100, value)))

    def _format_time(self) -> str:
        minutes = self.remaining // 60
        seconds = self.remaining % 60
        return f"{minutes:02d}:{seconds:02d}"


class StatsDialog(QDialog):
    def __init__(self, weekly_stats: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Звіти")
        self.resize(420, 320)

        title = QLabel("Динаміка за тижнями")
        title.setStyleSheet("font-size: 14px; font-weight: 600;")

        table = QTableWidget(len(weekly_stats), 3)
        table.setObjectName("StatsTable")
        header_labels = ["Тиждень", "Створено", "Виконано"]
        for col, label in enumerate(header_labels):
            item = QTableWidgetItem(label)
            align = Qt.AlignLeft | Qt.AlignVCenter if col == 0 else Qt.AlignCenter
            item.setTextAlignment(align)
            table.setHorizontalHeaderItem(col, item)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setShowGrid(True)
        table.setAlternatingRowColors(True)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(90)
        table.verticalHeader().setDefaultSectionSize(36)

        for row, item in enumerate(weekly_stats):
            week_start = item.get("week_start")
            created = item.get("created", 0)
            completed = item.get("completed", 0)
            week_end = week_start + timedelta(days=6)
            date_item = QTableWidgetItem(
                f"{week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}"
            )
            date_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            created_item = QTableWidgetItem(str(created))
            created_item.setTextAlignment(Qt.AlignCenter)
            completed_item = QTableWidgetItem(str(completed))
            completed_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, date_item)
            table.setItem(row, 1, created_item)
            table.setItem(row, 2, completed_item)

        close_button = QPushButton("Закрити")
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(table)
        layout.addLayout(buttons)
