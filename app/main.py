from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from app.infra.db import init_db
from app.infra.logging import setup_logging
from app.ui.main_window import MainWindow


def load_styles(app: QApplication) -> None:
    qss_path = Path(__file__).resolve().parent / "ui" / "styles.qss"
    if not qss_path.exists():
        return
    app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> None:
    setup_logging()
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "DB error", str(exc))
        return

    app = QApplication(sys.argv)
    app.setFont(QFont("Bahnschrift", 10))
    load_styles(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
