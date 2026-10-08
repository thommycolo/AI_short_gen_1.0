"""AI Short Generator 1.0 - Clip Carousel & Batch Clip Manager Component"""

import os
import subprocess
from typing import Optional, List, Dict
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QWidget
)
from PySide6.QtCore import Signal, Qt


class ClipCarouselWidget(QFrame):
    """Componente per la visualizzazione e navigazione delle clip generate."""

    clip_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CardSurface")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        header_lbl = QLabel("GESTIONE BATCH CLIP GENERATE")
        header_lbl.setObjectName("SectionHeader")
        top_row.addWidget(header_lbl)
        top_row.addStretch()

        self.btn_open_folder = QPushButton("📂 Cartella Renders")
        self.btn_open_folder.clicked.connect(self._open_renders_folder)
        top_row.addWidget(self.btn_open_folder)
        layout.addLayout(top_row)

        self.list_widget = QListWidget()
        self.list_widget.setFixedHeight(95)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def add_clip(self, file_path: str, label: str):
        item = QListWidgetItem(f"🎬 {label}")
        item.setData(Qt.UserRole, file_path)
        self.list_widget.addItem(item)

    def clear_clips(self):
        self.list_widget.clear()

    def _on_item_clicked(self, item: QListWidgetItem):
        file_path = item.data(Qt.UserRole)
        if file_path:
            self.clip_selected.emit(file_path)

    def _open_renders_folder(self):
        renders_dir = Path("app_data/renders").resolve()
        renders_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            subprocess.run(["explorer", str(renders_dir)])
        else:
            subprocess.run(["xdg-open", str(renders_dir)])

