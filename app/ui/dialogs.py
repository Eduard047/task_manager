from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
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
        self.setFixedSize(280, 220)

        self.work_seconds = SETTINGS.pomodoro_work_min * 60
        self.break_seconds = SETTINGS.pomodoro_break_min * 60
        self.remaining = self.work_seconds
        self.on_break = False

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

        self.label = QLabel(self._format_time())
        self.label.setObjectName("PomodoroTime")
        self.label.setStyleSheet("font-size: 24px; font-weight: 600;")

        self.phase_label = QLabel("Робота")

        self.start_button = QPushButton("Старт")
        self.start_button.clicked.connect(self.start)

        self.pause_button = QPushButton("Пауза")
        self.pause_button.clicked.connect(self.pause)

        self.reset_button = QPushButton("Скинути")
        self.reset_button.clicked.connect(self.reset)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.reset_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.label)
        layout.addLayout(buttons)

    def start(self) -> None:
        if not self.timer.isActive():
            self.timer.start()

    def pause(self) -> None:
        self.timer.stop()

    def reset(self) -> None:
        self.timer.stop()
        self.on_break = False
        self.remaining = self.work_seconds
        self.phase_label.setText("Робота")
        self.label.setText(self._format_time())

    def _tick(self) -> None:
        self.remaining -= 1
        if self.remaining <= 0:
            self.on_break = not self.on_break
            self.remaining = self.break_seconds if self.on_break else self.work_seconds
            self.phase_label.setText("Перерва" if self.on_break else "Робота")
        self.label.setText(self._format_time())

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
        table.setHorizontalHeaderLabels(["Тиждень (початок)", "Створено", "Виконано"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)

        for row, item in enumerate(weekly_stats):
            week_start = item.get("week_start")
            created = item.get("created", 0)
            completed = item.get("completed", 0)
            table.setItem(row, 0, QTableWidgetItem(week_start.strftime("%d.%m.%Y")))
            table.setItem(row, 1, QTableWidgetItem(str(created)))
            table.setItem(row, 2, QTableWidgetItem(str(completed)))

        close_button = QPushButton("Закрити")
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(table)
        layout.addLayout(buttons)
