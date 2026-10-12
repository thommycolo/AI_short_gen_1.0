import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QButtonGroup, QScrollArea, QFrame, QWidget, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from app.config import FONTS_DIR
from app.core.continuous_video_manager import ContinuousVideoPoolManager
from app.ui.modals.video_playback_modal import VideoPlaybackModal


class VideoPoolModal(QDialog):
    """Libreria Video Background & Pool a Flusso Continuo con Continuità per Categoria."""

    source_selected = Signal(int)
    category_selected = Signal(str)

    def __init__(
        self,
        video_mgr: ContinuousVideoPoolManager,
        active_category: str = "Minecraft",
        required_duration_sec: float = 40.0,
        selected_source_id: Optional[int] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.video_mgr = video_mgr
        self.active_category = active_category
        self.required_duration_sec = required_duration_sec
        self.selected_source_id: Optional[int] = selected_source_id
        self.selected_category: Optional[str] = None
        self.selected_video_data: Optional[Dict[str, Any]] = None
        if selected_source_id:
            src = self.video_mgr.get_source_by_id(selected_source_id)
            if src:
                self.selected_video_data = dict(src)
                self.selected_category = src.get("category", active_category)
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
        self.rb_manual = QRadioButton("👤 PREFERENZA MANUALE SPECIFICA (Override dell'utente)")
        if self.selected_source_id:
            self.rb_manual.setChecked(True)
        else:
            self.rb_auto.setChecked(True)
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

        # Riga Filtro Categoria Pool
        filter_box = QHBoxLayout()
        filter_lbl = QLabel("🔍 Filtra Categoria:")
        filter_lbl.setStyleSheet("font-weight: 600; color: #DCE0EA; font-size: 12px;")
        filter_box.addWidget(filter_lbl)

        self.combo_filter_category = QComboBox()
        self.combo_filter_category.setStyleSheet("padding: 3px 8px; font-weight: 500;")
        self._populate_category_filter()
        self.combo_filter_category.currentIndexChanged.connect(self._on_filter_changed)
        filter_box.addWidget(self.combo_filter_category, stretch=1)
        layout.addLayout(filter_box)

        # Scroll Area per la lista video (senza scroll orizzontale)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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

    def _populate_category_filter(self):
        self.combo_filter_category.blockSignals(True)
        self.combo_filter_category.clear()
        self.combo_filter_category.addItem("📂 Tutte le categorie", "")
        available_cats = self.video_mgr.get_available_categories()
        for c in available_cats:
            self.combo_filter_category.addItem(f"📁 {c}", c)

        if self.active_category:
            idx = self.combo_filter_category.findData(self.active_category)
            if idx >= 0:
                self.combo_filter_category.setCurrentIndex(idx)
        self.combo_filter_category.blockSignals(False)

    def _on_filter_changed(self, index: int):
        self.refresh_sources()

    def refresh_sources(self):
        while self.vbox_sources.count():
            item = self.vbox_sources.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        selected_cat = ""
        if hasattr(self, "combo_filter_category"):
            selected_cat = self.combo_filter_category.currentData() or ""

        if selected_cat:
            sources = self.video_mgr.get_sources(category=selected_cat, available_only=False)
        else:
            sources = self.video_mgr.get_all_sources()

        if not sources:
            cat_str = f" per la categoria '{selected_cat}'" if selected_cat else ""
            lbl_empty = QLabel(f"Nessun video presente nel Pool{cat_str}. Scarica nuovi video da link YouTube.")
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
        is_selected = (self.selected_source_id is not None and src["id"] == self.selected_source_id)
        if is_selected:
            card.setStyleSheet("QFrame#InnerCard { border: 2px solid #528A68; background-color: #17241D; border-radius: 6px; }")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(4)

        # Troncamento del titolo per prevenire scroll orizzontale (nessun ID in vista)
        raw_title = str(src.get("video_title", "Video Master"))
        max_title_len = 38
        if len(raw_title) > max_title_len:
            clean_title = raw_title[:max_title_len - 3].rstrip() + "..."
        else:
            clean_title = raw_title

        # Riga 1: Titolo, Categoria e Pulsanti Azione (Riproduci, Seleziona, Elimina)
        r1 = QHBoxLayout()
        title_lbl = QLabel(f'🎬 "{clean_title}"')
        title_lbl.setToolTip(raw_title)
        title_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #DCE0EA;")

        cat_badge = QLabel(f"Cat: {src['category']}")
        cat_badge.setObjectName("BadgeAvailable")

        r1.addWidget(title_lbl)
        r1.addWidget(cat_badge)

        if is_selected:
            icon_badge = QLabel("✅ SELEZIONATO")
            icon_badge.setStyleSheet(
                "background-color: #2F543F; color: #A3E4D7; font-weight: 700; "
                "border: 1px solid #528A68; border-radius: 4px; padding: 2px 7px; font-size: 11px;"
            )
            r1.addWidget(icon_badge)

        r1.addStretch()

        btn_play = QPushButton("▶ Riproduci")
        btn_play.setStyleSheet("font-size: 11px; padding: 3px 8px; font-weight: 600;")
        btn_play.clicked.connect(lambda _, s=src: self._on_play_video(s))
        r1.addWidget(btn_play)

        btn_select = QPushButton("✅ ATTIVO" if is_selected else "SELEZIONA QUESTO")
        if is_selected:
            btn_select.setStyleSheet(
                "font-size: 11px; padding: 3px 8px; font-weight: 700; "
                "background-color: #2F543F; color: #E8F5E9; border: 1px solid #528A68;"
            )
        else:
            btn_select.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        btn_select.clicked.connect(lambda _, s=src: self._on_select_source(s))
        r1.addWidget(btn_select)

        btn_del = QPushButton("🗑️ Elimina")
        btn_del.setStyleSheet("font-size: 11px; padding: 3px 8px; color: #D98880; border-color: #5C3232;")
        btn_del.clicked.connect(lambda _, s=src: self._on_delete_video(s))
        r1.addWidget(btn_del)

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

        # Riga 3: Compatibilità per categoria
        is_same_cat = (src["category"] == self.active_category)
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

    def _on_play_video(self, src: Dict[str, Any]):
        path = src.get("file_path", "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "File non trovato", f"Il file video non è presente su disco:\n{path}")
            return
        playback_dialog = VideoPlaybackModal(
            video_path=path,
            video_title=src.get("video_title", "Video Master"),
            parent=self
        )
        playback_dialog.exec()

    def _on_delete_video(self, src: Dict[str, Any]):
        sid = src.get("id")
        title = src.get("video_title", "Video")
        reply = QMessageBox.question(
            self,
            "Conferma Eliminazione",
            f"Sei sicuro di voler eliminare definitivamente dal pool e dal disco il video:\n\n\"{title}\" (ID: #{sid})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.video_mgr.delete_source(sid, delete_file=True)
            if self.selected_source_id == sid:
                self.selected_source_id = None
                self.rb_auto.setChecked(True)
            self.refresh_sources()
            QMessageBox.information(self, "Video Eliminato", f"Il video #{sid} è stato rimosso dal pool con successo.")

    def _on_select_source(self, src_or_id: Any):
        if isinstance(src_or_id, int):
            sid = src_or_id
            src = self.video_mgr.get_source_by_id(sid) or {
                "id": sid, "category": self.active_category, "video_title": f"Video #{sid}",
                "available_duration_sec": 60.0, "frontier_playhead_sec": 0.0
            }
        else:
            src = src_or_id
            sid = src["id"]

        cat = src.get("category", "General")
        title = src.get("video_title", "Video")

        self.selected_source_id = sid
        self.selected_category = cat
        self.selected_video_data = dict(src)
        self.rb_manual.setChecked(True)

        old_cat = self.active_category
        self.active_category = cat

        self.source_selected.emit(sid)
        self.category_selected.emit(cat)

        self.lbl_story_status.setText(
            f"STATO STORIA ATTIVA: Richiede ~{self.required_duration_sec:.1f}s continui | Categoria: {self.active_category}"
        )

        self.refresh_sources()

    def _reset_to_auto(self):
        self.selected_source_id = None
        self.rb_auto.setChecked(True)
        self.refresh_sources()

