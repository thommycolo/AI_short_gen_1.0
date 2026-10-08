"""AI Short Generator 1.0 - Script Selector Compact Card Component"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PySide6.QtCore import Signal, Qt
from app.config import DEFAULT_WPS


class ScriptSelectorCard(QFrame):
    """Card compatta di gestione e selezione dello script attivo nella schermata principale."""

    new_script_requested = Signal()
    library_requested = Signal()
    clip_split_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CardSurface")
        self.active_script_data: Optional[Dict[str, Any]] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header con pulsanti rapidi
        top_row = QHBoxLayout()
        header_lbl = QLabel("1. SCRIPT ATTIVO & REPOSITORY")
        header_lbl.setObjectName("SectionHeader")

        self.btn_new = QPushButton("➕ Nuovo Script")
        self.btn_new.clicked.connect(self.new_script_requested.emit)

        self.btn_library = QPushButton("📂 Scegli dall'Archivio")
        self.btn_library.clicked.connect(self.library_requested.emit)

        self.btn_clip_split = QPushButton("✂️ Suddivisione Clip & Parametri")
        self.btn_clip_split.setStyleSheet("font-weight: 600; color: #E2E6EF;")
        self.btn_clip_split.setToolTip("Analizza la suddivisione del testo nelle varie clip e regola dinamicamente i parametri temporali")
        self.btn_clip_split.clicked.connect(self.clip_split_requested.emit)

        top_row.addWidget(header_lbl)
        top_row.addStretch()
        top_row.addWidget(self.btn_new)
        top_row.addWidget(self.btn_library)
        top_row.addWidget(self.btn_clip_split)
        layout.addLayout(top_row)

        # Box informazioni script attivo
        self.info_box = QFrame()
        self.info_box.setObjectName("InnerCard")
        info_layout = QVBoxLayout(self.info_box)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(4)

        # Riga Titolo
        title_row = QHBoxLayout()
        self.lbl_title = QLabel("Nessun testo selezionato (Archivio in attesa)")
        self.lbl_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #DCE0EA;")

        self.btn_clear = QPushButton("🗑 Rimuovi")
        self.btn_clear.setVisible(False)
        self.btn_clear.clicked.connect(self.clear_script)

        title_row.addWidget(self.lbl_title)
        title_row.addStretch()
        title_row.addWidget(self.btn_clear)
        info_layout.addLayout(title_row)

        # Riga Metriche & Stato
        metrics_row = QHBoxLayout()
        self.lbl_metrics = QLabel("Dati: 0 Words | Stima: ~0.0 s | 0 Clip Short")
        self.lbl_metrics.setObjectName("HelperText")

        self.btn_mini_split = QPushButton("✂️ Dettaglio Clip")
        self.btn_mini_split.setStyleSheet("font-size: 10px; padding: 2px 7px; color: #BFA175;")
        self.btn_mini_split.setVisible(False)
        self.btn_mini_split.clicked.connect(self.clip_split_requested.emit)

        self.lbl_status = QLabel("IN ATTESA")
        self.lbl_status.setObjectName("BadgeUsedLock")

        metrics_row.addWidget(self.lbl_metrics)
        metrics_row.addWidget(self.btn_mini_split)
        metrics_row.addStretch()
        metrics_row.addWidget(self.lbl_status)
        info_layout.addLayout(metrics_row)

        layout.addWidget(self.info_box)

    def set_script(self, script_data: Dict[str, Any]):
        self.active_script_data = script_data
        title = script_data.get("context_title", "Untitled")
        word_count = script_data.get("word_count", 0)
        est_sec = script_data.get("est_duration_sec", round(word_count / DEFAULT_WPS, 1))
        status = script_data.get("status", "DISPONIBILE")

        # Stima o conteggio reale clip
        if "num_clips" in script_data and script_data["num_clips"]:
            num_clips = int(script_data["num_clips"])
        elif script_data.get("custom_chunks"):
            num_clips = len(script_data["custom_chunks"])
        else:
            num_clips = max(1, int(round(est_sec / 40.0 + 0.49)))

        self.lbl_title.setText(f'Titolo: "{title}"')
        self.lbl_metrics.setText(f"Dati: {word_count} Words | Stima: ~{est_sec:.1f} s | {num_clips} Clip Short")

        if status == "DISPONIBILE":
            self.lbl_status.setText("🟢 DISPONIBILE")
            self.lbl_status.setObjectName("BadgeAvailable")
        elif status == "UTILIZZATO":
            self.lbl_status.setText("🔒 UTILIZZATO")
            self.lbl_status.setObjectName("BadgeUsedLock")
        else:
            self.lbl_status.setText(f"⚡ {status}")
            self.lbl_status.setObjectName("BadgeWarning")

        # Re-apply stylesheet to update badge
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

        self.btn_clear.setVisible(True)
        self.btn_mini_split.setVisible(True)

    def update_metrics(
        self,
        wps: float = DEFAULT_WPS,
        num_clips: Optional[int] = None,
        total_duration_sec: Optional[float] = None,
        word_count: Optional[int] = None,
        char_count: Optional[int] = None
    ):
        """Aggiorna le metriche mostrate in base alla nuova velocità WPS e suddivisione clip."""
        if not self.active_script_data:
            return
        if word_count is not None:
            self.active_script_data["word_count"] = word_count
        if char_count is not None:
            self.active_script_data["char_count"] = char_count
        if total_duration_sec is not None:
            self.active_script_data["est_duration_sec"] = total_duration_sec
        if num_clips is not None:
            self.active_script_data["num_clips"] = num_clips

        wc = self.active_script_data.get("word_count", 0)

        if total_duration_sec is not None:
            est_sec = float(total_duration_sec)
        elif "est_duration_sec" in self.active_script_data:
            est_sec = float(self.active_script_data["est_duration_sec"])
        else:
            est_sec = round(wc / max(0.5, wps), 1)

        if num_clips is not None:
            clips = int(num_clips)
        elif "num_clips" in self.active_script_data:
            clips = int(self.active_script_data["num_clips"])
        elif self.active_script_data.get("custom_chunks"):
            clips = len(self.active_script_data["custom_chunks"])
        else:
            clips = max(1, int(round(est_sec / 40.0 + 0.49)))

        self.lbl_metrics.setText(f"Dati: {wc} Words | Stima: ~{est_sec:.1f} s | {clips} Clip Short")

    def clear_script(self, notify: bool = True):
        if self.active_script_data is None and not self.btn_clear.isVisible():
            return
        self.active_script_data = None
        self.lbl_title.setText("Nessun testo selezionato (Archivio in attesa)")
        self.lbl_metrics.setText("Dati: 0 Words | Stima: ~0.0 s | 0 Clip Short")
        self.lbl_status.setText("IN ATTESA")
        self.lbl_status.setObjectName("BadgeUsedLock")
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)
        self.btn_clear.setVisible(False)
        self.btn_mini_split.setVisible(False)
        if notify:
            self.clear_requested.emit()

    def get_active_script(self) -> Optional[Dict[str, Any]]:
        return self.active_script_data

