"""AI Short Generator 1.0 - Video Background Pool Card Component"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QWidget
)
from PySide6.QtCore import Signal
from app.config import CATEGORIES


class VideoSourceCard(QFrame):
    """Card per la gestione del Background Video Pool e categorizzazione continua."""

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
        header_lbl = QLabel("3. BACKGROUND VIDEO POOL")
        header_lbl.setObjectName("SectionHeader")

        self.btn_yt = QPushButton("⬇️ Scarica Video")
        self.btn_yt.setObjectName("PrimaryButton")
        self.btn_yt.clicked.connect(self.download_yt_requested.emit)

        self.btn_pool = QPushButton("📂 Libreria Pool")
        self.btn_pool.clicked.connect(self.pool_library_requested.emit)

        top_row.addWidget(header_lbl)
        top_row.addStretch()
        top_row.addWidget(self.btn_yt)
        top_row.addWidget(self.btn_pool)
        layout.addLayout(top_row)

        # Riga Categoria
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Categoria:"))
        self.combo_category = QComboBox()
        self.combo_category.addItems(CATEGORIES)
        self.combo_category.currentTextChanged.connect(self.category_changed.emit)
        self.combo_category.activated.connect(lambda _: self.category_changed.emit(self.combo_category.currentText()))
        row2.addWidget(self.combo_category, stretch=1)
        layout.addLayout(row2)

        # Box informazioni video pool
        info_box = QFrame()
        info_box.setObjectName("InnerCard")
        info_box.setMinimumHeight(86)
        info_layout = QVBoxLayout(info_box)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(4)

        self.lbl_active_video = QLabel("- Nessun Video disponibile -")
        self.lbl_active_video.setMinimumHeight(18)
        self.lbl_active_video.setStyleSheet("font-weight: 600; color: #D98880; font-size: 13px;")

        self.lbl_avail_dur = QLabel("Scarica un nuovo video tramite '⬇️ Scarica Video' per iniziare.")
        self.lbl_avail_dur.setObjectName("HelperText")
        self.lbl_avail_dur.setMinimumHeight(16)
        self.lbl_avail_dur.setWordWrap(True)

        # Badge tecnici
        badge_row = QHBoxLayout()
        b1 = QLabel("Continuità: [ Multiversale per Categoria 🎮 ]")
        b1.setObjectName("HelperText")
        b1.setMinimumHeight(18)
        b2 = QLabel("Snapping: [ Bounded Right (±0.2s) ]")
        b2.setObjectName("HelperText")
        b2.setMinimumHeight(18)
        self.badge_status = QLabel("Nessun Video ⚠️")
        self.badge_status.setObjectName("BadgeWarning")
        self.badge_status.setMinimumHeight(20)

        badge_row.addWidget(b1)
        badge_row.addWidget(b2)
        badge_row.addStretch()
        badge_row.addWidget(self.badge_status)

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

    def set_categories(self, categories: list, current: Optional[str] = None):
        curr = current or self.combo_category.currentText()
        self.combo_category.blockSignals(True)
        self.combo_category.clear()
        self.combo_category.addItems(categories)
        if curr in categories:
            self.combo_category.setCurrentText(curr)
        elif categories:
            self.combo_category.setCurrentIndex(0)
        self.combo_category.blockSignals(False)

    def show_no_video_warning(self, category: str = ""):
        """Mostra nella barra la scritta '- Nessun Video disponibile -' se non ci sono video disponibili."""
        cat_info = f" per la categoria '{category}'" if category else ""
        self.lbl_active_video.setText("- Nessun Video disponibile -")
        self.lbl_active_video.setToolTip(f"Nessun video valido trovato nel pool{cat_info}. Scarica un nuovo video tramite '⬇️ Scarica Video'.")
        self.lbl_active_video.setStyleSheet("font-weight: 600; color: #D98880; font-size: 13px;")

        self.lbl_avail_dur.setText(f"Nessun video presente nel pool{cat_info}. Scarica un video tramite '⬇️ Scarica Video'.")
        self.lbl_avail_dur.setStyleSheet("color: #C4A36B; font-size: 11px;")

        if hasattr(self, "badge_status"):
            self.badge_status.setText("Nessun Video ⚠️")
            self.badge_status.setObjectName("BadgeWarning")
            self.badge_status.style().unpolish(self.badge_status)
            self.badge_status.style().polish(self.badge_status)

    def update_video_info(self, title: str, duration_str: str, is_valid: bool = True, has_video: Optional[bool] = None):
        """Aggiorna le informazioni sul video selezionato o mostra l'avviso se non disponibile."""
        if has_video is False or not title or "Nessun video" in title:
            cat = self.get_selected_category()
            self.show_no_video_warning(category=cat)
            return

        clean_title = title.strip()
        max_len = 38
        if len(clean_title) > max_len:
            disp_title = clean_title[:max_len - 3].rstrip() + "..."
        else:
            disp_title = clean_title

        self.lbl_active_video.setText(f'Video: "{disp_title}"')
        self.lbl_active_video.setToolTip(clean_title)
        self.lbl_active_video.setStyleSheet("font-weight: 600; color: #DCE0EA; font-size: 13px;")

        dur_text = duration_str if duration_str.startswith("Durata:") else f"Durata: {duration_str}"
        self.lbl_avail_dur.setText(dur_text)
        self.lbl_avail_dur.setStyleSheet("color: #949CAE; font-size: 11px;")

        if hasattr(self, "badge_status"):
            self.badge_status.setText("Video Pronto 🟢")
            self.badge_status.setObjectName("BadgeAvailable")
            self.badge_status.style().unpolish(self.badge_status)
            self.badge_status.style().polish(self.badge_status)

    def update_pool_status(self, video_title: str, total_avail_str: str):
        self.update_video_info(title=video_title, duration_str=f"Durata: {total_avail_str}")
