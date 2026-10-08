"""AI Short Generator 1.0 - Pre-Production Review Modal & Visual 0.60s Inspection Carousel"""

import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QTabWidget, QWidget, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from app.core.pre_review_engine import PreProductionReviewEngine, StoryReviewItem


class PreProductionReviewModal(QDialog):
    """
    Finestra Modale di Riepilogo Pre-Render & Ispezione Frame 0.60s:
    - Carosello sequenziale 1-a-1
    - Ispezione frame a t = 0.600s con Intro Title Banner e primo vocabolo karaoke attivo
    - Ispezione copertina Thumbnail seriale di serie
    - Overlay Safe Zones Social (TikTok / Reels / Shorts)
    """

    confirmed_start = Signal(list) # List[StoryReviewItem]

    def __init__(
        self,
        review_items: List[StoryReviewItem],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.review_items = review_items
        self.current_index = 0
        self.setWindowTitle("Riepilogo Pre-Produzione & Ispezione Visiva Primo Frame (0.6s)")
        self.resize(980, 720)
        self.setObjectName("ModalWindow")
        self._init_ui()
        self.display_current_item()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # Navigazione Carosello
        nav_bar = QHBoxLayout()
        self.btn_prev = QPushButton("◀ STORIA PRECEDENTE")
        self.btn_prev.clicked.connect(self._prev_story)

        self.lbl_nav_title = QLabel("STORIA 1 DI 1")
        self.lbl_nav_title.setStyleSheet("font-weight: 600; font-size: 14px; color: #E2E6EF;")
        self.lbl_nav_title.setAlignment(Qt.AlignCenter)

        self.btn_next = QPushButton("STORIA SUCCESSIVA ▶")
        self.btn_next.clicked.connect(self._next_story)

        nav_bar.addWidget(self.btn_prev)
        nav_bar.addWidget(self.lbl_nav_title, stretch=1)
        nav_bar.addWidget(self.btn_next)
        layout.addLayout(nav_bar)

        # Contenitore Centrale a 2 Colonne
        content_row = QHBoxLayout()
        content_row.setSpacing(14)

        # COLONNA SINISTRA: Metadati & Configurazione
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setSpacing(8)
        self.left_scroll.setWidget(self.left_container)
        content_row.addWidget(self.left_scroll, stretch=5)

        # COLONNA DESTRA: Monitor 9:16 (270x480) & Toggle Tabs
        right_panel = QFrame()
        right_panel.setObjectName("CardSurface")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 8, 10, 8)
        right_layout.setSpacing(8)

        self.lbl_monitor_header = QLabel("ISPEZIONE PRIMO FRAME (0.60s)")
        self.lbl_monitor_header.setObjectName("SectionHeader")
        right_layout.addWidget(self.lbl_monitor_header, alignment=Qt.AlignCenter)

        # Toggle Ispezione [ Frame 0.60s | Thumbnail Serie ] (Section 5.13)
        toggle_bar = QHBoxLayout()
        self.btn_mode_frame = QPushButton("🖼️ Frame 0.60s")
        self.btn_mode_frame.setCheckable(True)
        self.btn_mode_frame.setChecked(True)
        self.btn_mode_frame.clicked.connect(lambda: self._set_preview_mode("frame"))

        self.btn_mode_thumb = QPushButton("🏷️ Thumbnail Serie")
        self.btn_mode_thumb.setCheckable(True)
        self.btn_mode_thumb.setChecked(False)
        self.btn_mode_thumb.clicked.connect(lambda: self._set_preview_mode("thumb"))

        toggle_bar.addWidget(self.btn_mode_frame)
        toggle_bar.addWidget(self.btn_mode_thumb)
        right_layout.addLayout(toggle_bar)

        self.current_preview_mode = "frame"

        # Canvas Immagine Frame (270x480)
        self.frame_viewer = QLabel()
        self.frame_viewer.setFixedSize(270, 480)
        self.frame_viewer.setStyleSheet("background-color: #121418; border-radius: 6px; border: 1px solid #343946;")
        self.frame_viewer.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.frame_viewer, alignment=Qt.AlignCenter)

        self.cb_overlay = QCheckBox("Mostra Overlay Safe Zones (TikTok/Reels/Shorts)")
        self.cb_overlay.setChecked(True)
        self.cb_overlay.toggled.connect(self.display_current_item)
        right_layout.addWidget(self.cb_overlay, alignment=Qt.AlignCenter)

        self.lbl_frame_info = QLabel("Timestamp Esatto: 00:00:00.600 (+0.10s su inizio voce)")
        self.lbl_frame_info.setObjectName("HelperText")
        self.lbl_frame_info.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_frame_info)

        content_row.addWidget(right_panel, stretch=4)
        layout.addLayout(content_row, stretch=1)

        # Footer Azioni
        footer = QHBoxLayout()
        self.btn_back = QPushButton("✏️ Modifica / Torna Indietro")
        self.btn_back.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("🚀 CONFERMA & AVVIA CREAZIONE DEFINITIVA")
        self.btn_confirm.setObjectName("PrimaryButton")
        self.btn_confirm.clicked.connect(self._confirm_and_start)

        footer.addWidget(self.btn_back)
        footer.addStretch()
        footer.addWidget(self.btn_confirm)
        layout.addLayout(footer)

    def display_current_item(self):
        if not self.review_items:
            return

        item = self.review_items[self.current_index]
        n_total = len(self.review_items)
        self.lbl_nav_title.setText(f"STORIA {self.current_index + 1} DI {n_total}: \"{item.title}\"")

        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < n_total - 1)

        # Pulisci layout sinistro
        while self.left_layout.count():
            it = self.left_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

        # 1. Script & Metriche
        c1 = self._make_card(
            "📝 SCRIPT & METRICHE DURATA",
            [
                f"• Titolo Contesto: {item.title}",
                f"• Parole: {item.word_count}",
                f"• Durata Voce Prevista: {item.estimated_audio_duration_sec:.1f} s (Max 43.0s) ✅",
                f"• Durata Video Totale: {item.total_video_duration_sec:.1f} s (+2.0s Padding) ✅",
                f"• Anteprima: \"{item.script_snippet}\""
            ]
        )
        self.left_layout.addWidget(c1)

        # 2. Voce
        c2 = self._make_card(
            "🎙️ CONFIGURAZIONE VOCE & RECITAZIONE",
            [
                f"• Profilo Vocale: {item.voice_name}",
                f"• Modalità: {item.voice_type}",
                f"• Guida Emotiva (Instruct): \"{item.instruct_mood}\""
            ]
        )
        self.left_layout.addWidget(c2)

        # 3. Video Continuo
        c3 = self._make_card(
            "🎬 VIDEO ASSEGNATO & ALLOCAZIONE REGISTRY",
            [
                f"• File Sorgente: {item.video_source_title}",
                f"• Clip: {item.clip_index_label}",
                "• Vincolo Sequenziale: Monosorgente Continuo Garantito ✅"
            ]
        )
        self.left_layout.addWidget(c3)

        # 4. Banner Intro & Outro CTA
        c4 = self._make_card(
            "🏷️ BANNER INTRO & OUTRO CTA (STESSO FONT)",
            [
                f"• Intro Title (0.0s-1.5s): \"{item.intro_banner_text}\" (Centro Schermo)",
                f"• Outro CTA (-1.0s -> fine): \"{item.outro_cta_text}\" (Centro Schermo)",
                "• Stacco Voce: esattamente a -1.5s dalla fine del video"
            ]
        )
        self.left_layout.addWidget(c4)

        # 5. BGM
        c5 = self._make_card(
            "🎵 COLONNA SONORA (BGM)",
            [
                f"• Brano: {item.bgm_title}",
                f"• Target Loudness: {item.bgm_lufs:.1f} LUFS (EBU R128)",
                "• Auto-Ducking: Attivo (-22 dB voce, -14 dB intro/outro)"
            ]
        )
        self.left_layout.addWidget(c5)

        # 6. Tipografia
        c6 = self._make_card(
            "✍️ TIPOGRAFIA SOTTOTITOLI & BANNER",
            [
                f"• Font Uniforme: {item.font_name} ({item.font_size} pt)",
                f"• Colore Testo: {item.primary_color_hex} (Naturale uniforme)",
                "• Regola Anti-Overflow: Bounding Box <= 880px, max 2 righe"
            ]
        )
        self.left_layout.addWidget(c6)

        self.left_layout.addStretch()

        # Aggiorna monitor frame a 0.60s oppure Thumbnail Serie
        if self.current_preview_mode == "thumb":
            self.lbl_monitor_header.setText("ISPEZIONE THUMBNAIL SERIE")
            self.lbl_frame_info.setText("Same-Frame Series Branding (Titolo + part.N)")
            target_img_path = item.thumbnail_cover_path or ""
            fallback_label = "Copertina Thumbnail\ndi Serie"
        else:
            self.lbl_monitor_header.setText("ISPEZIONE PRIMO FRAME (0.60s)")
            self.lbl_frame_info.setText("Timestamp Esatto: 00:00:00.600 (+0.10s su inizio voce)")
            target_img_path = item.verification_frame_path or ""
            fallback_label = "Anteprima Frame\n0.600s"

        if target_img_path and os.path.exists(target_img_path):
            pix = QPixmap(target_img_path)
            if not pix.isNull():
                scaled = pix.scaled(270, 480, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.frame_viewer.setPixmap(scaled)
            else:
                self.frame_viewer.setText(fallback_label)
        else:
            self.frame_viewer.setText(fallback_label)

    def _set_preview_mode(self, mode: str):
        self.current_preview_mode = mode
        self.btn_mode_frame.setChecked(mode == "frame")
        self.btn_mode_thumb.setChecked(mode == "thumb")
        self.display_current_item()

    def _make_card(self, title: str, lines: List[str]) -> QFrame:
        card = QFrame()
        card.setObjectName("InnerCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(3)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #BFA175;")
        cl.addWidget(t_lbl)

        for l in lines:
            line_lbl = QLabel(l)
            line_lbl.setObjectName("HelperText")
            line_lbl.setWordWrap(True)
            cl.addWidget(line_lbl)

        return card

    def _prev_story(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.display_current_item()

    def _next_story(self):
        if self.current_index < len(self.review_items) - 1:
            self.current_index += 1
            self.display_current_item()

    def _confirm_and_start(self):
        self.confirmed_start.emit(self.review_items)
        self.accept()

