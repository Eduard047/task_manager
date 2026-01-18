from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QDir
from PySide6.QtGui import QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory

from app.config import PROJECT_ROOT
from app.infra.db import init_db
from app.infra.logging import setup_logging
from app.ui.main_window import MainWindow


def _apply_dark_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0F172A"))
    palette.setColor(QPalette.WindowText, QColor("#E6EDF3"))
    palette.setColor(QPalette.Base, QColor("#111827"))
    palette.setColor(QPalette.AlternateBase, QColor("#1B2230"))
    palette.setColor(QPalette.Text, QColor("#E6EDF3"))
    palette.setColor(QPalette.Button, QColor("#202A3B"))
    palette.setColor(QPalette.ButtonText, QColor("#E6EDF3"))
    palette.setColor(QPalette.ToolTipBase, QColor("#1B2230"))
    palette.setColor(QPalette.ToolTipText, QColor("#E6EDF3"))
    palette.setColor(QPalette.Highlight, QColor("#2563EB"))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)


def _find_qss_path() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent / "ui" / "styles.qss",
        PROJECT_ROOT / "app" / "ui" / "styles.qss",
        Path.cwd() / "app" / "ui" / "styles.qss",
    ]

    if getattr(sys, "frozen", False):
        exe_root = Path(sys.executable).resolve().parent
        candidates.extend([
            exe_root / "app" / "ui" / "styles.qss",
            exe_root / "ui" / "styles.qss",
        ])
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            meipass_root = Path(meipass)
            candidates.extend([
                meipass_root / "app" / "ui" / "styles.qss",
                meipass_root / "ui" / "styles.qss",
            ])

    for path in candidates:
        if path.exists():
            return path
    return None


def load_styles(app: QApplication) -> None:
    qss_path = _find_qss_path()
    if not qss_path:
        return
    assets_dir = qss_path.parent / "assets"
    if assets_dir.exists():
        QDir.addSearchPath("assets", str(assets_dir.resolve()))
        icon_path = assets_dir / "taskforge.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
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
    app.setStyle(QStyleFactory.create("Fusion"))
    _apply_dark_palette(app)
    app.setFont(QFont("Bahnschrift", 10))
    load_styles(app)

    window = MainWindow()
    if app.windowIcon():
        window.setWindowIcon(app.windowIcon())
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
