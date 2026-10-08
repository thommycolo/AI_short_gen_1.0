"""AI Short Generator 1.0 - Video Background Pool Card Component"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QWidget
)
from PySide6.QtCore import Signal
from app.config import CATEGORIES


class VideoSourceCard(QFrame):
    """Card per la gestione del Background Video Pool e categorizzazione continua."""

    import_local_requested = Signal()
    download_yt_requested = Signal()
    pool_library_requested = Signal()
    settings_drawer_requested = Signal()
    category_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CardSurface")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header con pulsanti
        top_row = QHBoxLayout()
        header_lbl = QLabel("3. BACKGROUND VIDEO POOL (Continuo / Locale & YT)")
        header_lbl.setObjectName("SectionHeader")

        self.btn_local = QPushButton("📁 Importa Locale")
        self.btn_local.clicked.connect(self.import_local_requested.emit)

        self.btn_yt = QPushButton("⬇️ Scarica YT")
        self.btn_yt.clicked.connect(self.download_yt_requested.emit)

        self.btn_pool = QPushButton("📂 Pool")
        self.btn_pool.clicked.connect(self.pool_library_requested.emit)

        top_row.addWidget(header_lbl)
        top_row.addStretch()
        top_row.addWidget(self.btn_local)
        top_row.addWidget(self.btn_yt)
        top_row.addWidget(self.btn_pool)
        layout.addLayout(top_row)

        # Riga Categoria & Assegnazione
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Categoria:"))
        self.combo_category = QComboBox()
        self.combo_category.addItems(CATEGORIES)
        self.combo_category.currentTextChanged.connect(self.category_changed.emit)
        row2.addWidget(self.combo_category, stretch=1)

        row2.addWidget(QLabel("Assegnazione:"))
        self.combo_alloc = QComboBox()
        self.combo_alloc.addItems([
            "🤖 Auto (Thematic Category Solver)",
            "👤 Selezione Manuale Specifica"
        ])
        row2.addWidget(self.combo_alloc, stretch=1)
        layout.addLayout(row2)

        # Box informazioni video pool
        info_box = QFrame()
        info_box.setObjectName("InnerCard")
        info_layout = QVBoxLayout(info_box)
        info_layout.setContentsMargins(8, 6, 8, 6)
        info_layout.setSpacing(4)

        self.lbl_active_video = QLabel('Video: "Minecraft_Parkour_Speedrun" (ID: #001)')
        self.lbl_active_video.setStyleSheet("font-weight: 500; color: #DCE0EA;")

        self.lbl_avail_dur = QLabel("Durata: 09m 00s disponibili (Frontiera: 00:00)")
        self.lbl_avail_dur.setObjectName("HelperText")

        # Badge tecnici
        badge_row = QHBoxLayout()
        b1 = QLabel("Continuità: [ Multiversale per Categoria 🎮 ]")
        b1.setObjectName("HelperText")
        b2 = QLabel("Snapping: [ Bounded Right (±0.2s) ]")
        b2.setObjectName("HelperText")
        b3 = QLabel("Ingestion: [ Zero-Recode ]")
        b3.setObjectName("BadgeAvailable")

        badge_row.addWidget(b1)
        badge_row.addWidget(b2)
        badge_row.addStretch()
        badge_row.addWidget(b3)

        info_layout.addWidget(self.lbl_active_video)
        info_layout.addWidget(self.lbl_avail_dur)
        info_layout.addLayout(badge_row)
        layout.addWidget(info_box)

        # Pulsante impostazioni drawer
        btn_row = QHBoxLayout()
        self.btn_settings = QPushButton("⚙️ Impostazioni Video & Ritaglio On-Demand")
        self.btn_settings.clicked.connect(self.settings_drawer_requested.emit)
        btn_row.addWidget(self.btn_settings)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def get_selected_category(self) -> str:
        return self.combo_category.currentText()

    def update_pool_status(self, video_title: str, total_avail_str: str):
        self.lbl_active_video.setText(f'Video: "{video_title}"')
        self.lbl_avail_dur.setText(f"Durata: {total_avail_str}")

    def update_video_info(self, title: str, duration_str: str, is_valid: bool = True):
        self.update_pool_status(title, duration_str)
