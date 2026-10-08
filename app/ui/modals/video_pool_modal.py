from pathlib import Path
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QButtonGroup, QScrollArea, QFrame, QWidget, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from app.config import FONTS_DIR
from app.core.continuous_video_manager import ContinuousVideoPoolManager


class VideoPoolModal(QDialog):
    """Libreria Video Background & Pool a Flusso Continuo con Continuità per Categoria."""

    source_selected = Signal(int)

    def __init__(
        self,
        video_mgr: ContinuousVideoPoolManager,
        active_category: str = "Minecraft",
        required_duration_sec: float = 40.0,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.video_mgr = video_mgr
        self.active_category = active_category
        self.required_duration_sec = required_duration_sec
        self.selected_source_id: Optional[int] = None
        self.setWindowTitle("Libreria Video Background & Pool Continuo")
        self.resize(840, 600)
        self.setObjectName("ModalWindow")
        self._init_ui()
        self.refresh_sources()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # Header
        top_bar = QHBoxLayout()
        header_lbl = QLabel("LIBRERIA VIDEO BACKGROUND & POOL CONTINUO")
        header_lbl.setObjectName("SectionHeader")
        top_bar.addWidget(header_lbl)
        top_bar.addStretch()

        btn_close = QPushButton("✕ Chiudi")
        btn_close.clicked.connect(self.close)
        top_bar.addWidget(btn_close)
        layout.addLayout(top_bar)

        # Modalità di Assegnazione
        mode_box = QFrame()
        mode_box.setObjectName("InnerCard")
        check_icon_url = (Path(FONTS_DIR).parent / "icons" / "check.png").resolve().as_posix()
        mode_box.setStyleSheet(f"""
            QRadioButton {{
                spacing: 10px;
                color: #DCE0EA;
                font-size: 12px;
                font-weight: 600;
            }}
            QRadioButton::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #4C5466;
                background-color: #1A1C22;
            }}
            QRadioButton::indicator:hover {{
                border-color: #6B82A6;
                background-color: #232731;
            }}
            QRadioButton::indicator:checked {{
                background-color: #2F543F;
                border: 2px solid #528A68;
                image: url("{check_icon_url}");
            }}
        """)
        mb_layout = QVBoxLayout(mode_box)
        mb_layout.setContentsMargins(8, 6, 8, 6)

        self.btn_group = QButtonGroup(self)
        self.rb_auto = QRadioButton("🤖 SELEZIONE AUTOMATICA OTTIMALE (Default - Continuità per Categoria Tematica)")
        self.rb_auto.setChecked(True)
        self.rb_manual = QRadioButton("👤 PREFERENZA MANUALE SPECIFICA (Override dell'utente)")
        self.btn_group.addButton(self.rb_auto)
        self.btn_group.addButton(self.rb_manual)

        mb_layout.addWidget(QLabel("MODALITÀ DI ASSEGNAZIONE VIDEO ATTIVA:"))
        mb_layout.addWidget(self.rb_auto)
        mb_layout.addWidget(self.rb_manual)
        layout.addWidget(mode_box)

        # Stato Storia Attiva
        self.lbl_story_status = QLabel(
            f"STATO STORIA ATTIVA: Richiede ~{self.required_duration_sec:.1f}s continui | Categoria: {self.active_category}"
        )
        self.lbl_story_status.setStyleSheet("font-weight: 500; color: #BFA175;")
        layout.addWidget(self.lbl_story_status)

        # Scroll Area per la lista video
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.vbox_sources = QVBoxLayout(self.container)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, stretch=1)

        # Footer
        footer = QHBoxLayout()
        self.btn_reset_auto = QPushButton("🤖 Ripristina Selezione Automatica")
        self.btn_reset_auto.clicked.connect(self._reset_to_auto)

        self.btn_apply = QPushButton("Chiudi & Applica Modifiche")
        self.btn_apply.setObjectName("PrimaryButton")
        self.btn_apply.clicked.connect(self.accept)

        footer.addWidget(self.btn_reset_auto)
        footer.addStretch()
        footer.addWidget(self.btn_apply)
        layout.addLayout(footer)

    def refresh_sources(self):
        while self.vbox_sources.count():
            item = self.vbox_sources.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        sources = self.video_mgr.get_all_sources()
        if not sources:
            lbl_empty = QLabel("Nessun video presente nel Pool. Importa o scarica nuovi video.")
            lbl_empty.setObjectName("HelperText")
            self.vbox_sources.addWidget(lbl_empty)
            self.vbox_sources.addStretch()
            return

        for src in sources:
            card = self._create_source_card(src)
            self.vbox_sources.addWidget(card)

        self.vbox_sources.addStretch()

    def _create_source_card(self, src: Dict[str, Any]) -> QFrame:
        card = QFrame()
        card.setObjectName("InnerCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(4)

        # Riga 1: Titolo e Categoria
        r1 = QHBoxLayout()
        title_lbl = QLabel(f'🎬 "{src["video_title"]}" (ID: #{src["id"]})')
        title_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #DCE0EA;")

        cat_badge = QLabel(f"Cat: {src['category']}")
        cat_badge.setObjectName("BadgeAvailable")

        r1.addWidget(title_lbl)
        r1.addWidget(cat_badge)
        r1.addStretch()

        btn_select = QPushButton("SELEZIONA QUESTO")
        btn_select.clicked.connect(lambda _, sid=src["id"]: self._on_select_source(sid))
        r1.addWidget(btn_select)
        cl.addLayout(r1)

        # Riga 2: Metriche temporali
        tot_m = int(src["total_duration_sec"] // 60)
        tot_s = int(src["total_duration_sec"] % 60)
        avail_m = int(src["available_duration_sec"] // 60)
        avail_s = int(src["available_duration_sec"] % 60)
        front_m = int(src["frontier_playhead_sec"] // 60)
        front_s = int(src["frontier_playhead_sec"] % 60)

        meta_lbl = QLabel(
            f"Durata Totale: {tot_m:02d}m {tot_s:02d}s  |  "
            f"Disponibili: {avail_m:02d}m {avail_s:02d}s continui (Playhead a {front_m:02d}m {front_s:02d}s)"
        )
        meta_lbl.setObjectName("HelperText")
        cl.addWidget(meta_lbl)

        # Riga 3: Compatibilità
        is_same_cat = (src["category"] == self.active_category or self.active_category == "General" or src["category"] == "General")
        has_time = src["available_duration_sec"] >= self.required_duration_sec

        if is_same_cat and has_time:
            compat_lbl = QLabel("Compatibilità: [ 🟢 IDONEO: Copre integralmente i requisiti richiesti ]")
            compat_lbl.setStyleSheet("color: #729B84; font-weight: 500; font-size: 11px;")
        elif not is_same_cat:
            compat_lbl = QLabel(f"Compatibilità: [ 🟡 CATEGORIA DIFFERENTE: Riservato per storie '{src['category']}' ]")
            compat_lbl.setStyleSheet("color: #C4A36B; font-size: 11px;")
        else:
            compat_lbl = QLabel("Compatibilità: [ 🔴 TEMPO INSUFFICIENTE: Durata residua inferiore al fabbisogno ]")
            compat_lbl.setStyleSheet("color: #AA7373; font-size: 11px;")

        cl.addWidget(compat_lbl)
        return card

    def _on_select_source(self, source_id: int):
        self.selected_source_id = source_id
        self.rb_manual.setChecked(True)
        self.source_selected.emit(source_id)
        QMessageBox.information(self, "Video Assegnato", f"Video #{source_id} impostato come preferenza manuale.")

    def _reset_to_auto(self):
        self.selected_source_id = None
        self.rb_auto.setChecked(True)
        QMessageBox.information(self, "Selezione Automatica", "Ripristinata la selezione automatica per categoria.")

