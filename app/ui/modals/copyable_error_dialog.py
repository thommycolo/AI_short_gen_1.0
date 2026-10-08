"""AI Short Generator 1.0 - Copyable Error Dialog Component"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QApplication, QWidget, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon


class CopyableErrorDialog(QDialog):
    """
    Dialog modale per visualizzare messaggi di errore o avvisi
    con testo completamente selezionabile e pulsante rapido per copiare negli appunti.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Errore",
        message: str = "",
        details: Optional[str] = None,
        is_warning: bool = False
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(540, 360)
        self.setMinimumSize(420, 260)
        self.setObjectName("ModalWindow")

        self.full_error_text = message
        if details:
            self.full_error_text = f"{message}\n\nDettagli:\n{details}"

        self._init_ui(title, message, is_warning)

    def _init_ui(self, title: str, message: str, is_warning: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header con badge
        header_row = QHBoxLayout()
        icon_str = "⚠️" if is_warning else "❌"
        badge_color = "#C4A36B" if is_warning else "#E06C75"
        lbl_badge = QLabel(f"{icon_str} {title}")
        lbl_badge.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {badge_color};")
        header_row.addWidget(lbl_badge)
        header_row.addStretch()
        layout.addLayout(header_row)

        lbl_desc = QLabel("Il testo sottostante può essere selezionato e copiato liberamente:")
        lbl_desc.setStyleSheet("color: #949CAE; font-size: 11px;")
        layout.addWidget(lbl_desc)

        # Text area per l'errore (read-only, selezionabile con mouse o tastiera)
        self.txt_error = QTextEdit()
        self.txt_error.setReadOnly(True)
        self.txt_error.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.txt_error.setPlainText(self.full_error_text)
        self.txt_error.setStyleSheet("""
            QTextEdit {
                background-color: #16181D;
                color: #E2E6EF;
                border: 1px solid #343946;
                border-radius: 6px;
                padding: 10px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.txt_error, stretch=1)

        # Feedback label
        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setStyleSheet("color: #729B84; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.lbl_feedback)

        # Footer con pulsanti
        btn_row = QHBoxLayout()
        
        self.btn_copy = QPushButton("📋 Copia Errore")
        self.btn_copy.setMinimumHeight(32)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #262B36;
                color: #DCE0EA;
                border: 1px solid #3D4455;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #313745;
                border-color: #555E75;
            }
        """)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self.btn_copy)

        btn_row.addStretch()

        self.btn_close = QPushButton("Chiudi")
        self.btn_close.setMinimumHeight(32)
        self.btn_close.setObjectName("AccentButton")
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)

        layout.addLayout(btn_row)

    def _copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.full_error_text)
        self.btn_copy.setText("✅ Copiato negli Appunti!")
        self.lbl_feedback.setText("Testo errore copiato con successo negli appunti.")
        QTimer.singleShot(2500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self.btn_copy.setText("📋 Copia Errore")
        self.lbl_feedback.setText("")


def show_copyable_error(
    parent: Optional[QWidget] = None,
    title: str = "Errore",
    message: str = "",
    details: Optional[str] = None,
    is_warning: bool = False
) -> int:
    """Funzione helper per mostrare un popup di errore con testo copiabile."""
    dialog = CopyableErrorDialog(
        parent=parent,
        title=title,
        message=message,
        details=details,
        is_warning=is_warning
    )
    return dialog.exec()

