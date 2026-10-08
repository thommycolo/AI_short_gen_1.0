"""AI Short Generator 1.0 - Audio Settings Drawer (BGM, Ducking & True Peak Limiter)"""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSlider, QCheckBox, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QColor

from app.core.bgm_manager import BgmManager, BgmTrackInfo
from app.config import (
    BGM_TARGET_LUFS, BGM_DUCKING_DB, BGM_INTRO_OUTRO_DB,
    TRUE_PEAK_LIMITER_DB, PADDING_INTRO_SEC, PADDING_OUTRO_SEC
)
from app.utils.logger import log


class BgmDownloadWorker(QThread):
    finished_track = Signal(object) # BgmTrackInfo or None
    error_occurred = Signal(str)

    def __init__(self, bgm_manager: BgmManager, url: str):
        super().__init__()
        self.bgm_manager = bgm_manager
        self.url = url

    def run(self):
        try:
            track = self.bgm_manager.download_and_normalize_youtube_audio(self.url)
            if track:
                self.finished_track.emit(track)
            else:
                self.error_occurred.emit("Impossibile estrarre o normalizzare la traccia da questo URL.")
        except Exception as e:
            self.error_occurred.emit(str(e))


class AudioSettingsDrawer(QDialog):
    """
    Drawer 4: Audio Mixing, BGM & YouTube Ingestion.
    Auto-Save on Close: ON.
    """

    settings_saved = Signal(dict)
    apply_to_all_requested = Signal(dict)

    def __init__(self, bgm_manager: Optional[BgmManager] = None, current_settings: Optional[dict] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bgm_manager = bgm_manager or BgmManager()
        self.current_settings = current_settings or {}
        self.selected_track_id: Optional[int] = self.current_settings.get("bgm_track_id")
        self.download_worker: Optional[BgmDownloadWorker] = None

        self.setWindowTitle("MIXING AUDIO, BGM & YOUTUBE INGESTION")
        self.resize(760, 680)
        self.setObjectName("DrawerWindow")

        self._init_ui()
        self._load_tracks_into_table()
        self._apply_initial_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(10)

        # Header con Auto-Save status badge
        header_bar = QHBoxLayout()
        lbl_title = QLabel("MIXING AUDIO, BGM & YOUTUBE INGESTION")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #DCE0EA;")
        header_bar.addWidget(lbl_title)
        header_bar.addStretch()

        lbl_autosave = QLabel("Auto-Save on Close: ON 🟢")
        lbl_autosave.setStyleSheet("font-size: 11px; font-weight: 600; color: #729B84; background-color: #21242C; padding: 4px 8px; border-radius: 4px; border: 1px solid #343946;")
        header_bar.addWidget(lbl_autosave)
        main_layout.addLayout(header_bar)

        # Scroll Area per il corpo centrale
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # SEZIONE 1: SCARICA & CONVERTI BGM DA LINK YOUTUBE
        sec1 = QFrame()
        sec1.setObjectName("CardSurface")
        sec1_layout = QVBoxLayout(sec1)
        sec1_layout.setContentsMargins(12, 10, 12, 10)
        sec1_layout.setSpacing(8)

        lbl_sec1 = QLabel("SEZIONE 1: SCARICA & CONVERTI BGM DA LINK YOUTUBE (Elaborazione Automatica)")
        lbl_sec1.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        sec1_layout.addWidget(lbl_sec1)

        lbl_yt_hint = QLabel("Incolla uno o più link di YouTube (uno per riga) per le musiche di sottofondo:")
        lbl_yt_hint.setStyleSheet("color: #949CAE; font-size: 11px;")
        sec1_layout.addWidget(lbl_yt_hint)

        self.txt_yt_urls = QTextEdit()
        self.txt_yt_urls.setPlaceholderText("https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...")
        self.txt_yt_urls.setFixedHeight(60)
        sec1_layout.addWidget(self.txt_yt_urls)

        btn_row1 = QHBoxLayout()
        self.btn_download_yt = QPushButton("⬇️ Scarica & Converti Audio da YouTube (Estrazione Stream + -24 LUFS)")
        self.btn_download_yt.setObjectName("AccentButton")
        self.btn_download_yt.clicked.connect(self._start_download_youtube)
        btn_row1.addWidget(self.btn_download_yt)
        sec1_layout.addLayout(btn_row1)

        self.lbl_yt_status = QLabel("Pronto per l'estrazione audio.")
        self.lbl_yt_status.setStyleSheet("color: #949CAE; font-size: 11px;")
        sec1_layout.addWidget(self.lbl_yt_status)
        layout.addWidget(sec1)

        # SEZIONE 2: LIBRERIA BGM LOCALE
        sec2 = QFrame()
        sec2.setObjectName("CardSurface")
        sec2_layout = QVBoxLayout(sec2)
        sec2_layout.setContentsMargins(12, 10, 12, 10)
        sec2_layout.setSpacing(8)

        lbl_sec2 = QLabel("SEZIONE 2: LIBRERIA BGM LOCALE (TRACCE YOUTUBE & SAFE CC0)")
        lbl_sec2.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        sec2_layout.addWidget(lbl_sec2)

        self.tbl_tracks = QTableWidget(0, 4)
        self.tbl_tracks.setHorizontalHeaderLabels(["Titolo Brano", "Durata", "Target LUFS", "Azione"])
        self.tbl_tracks.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_tracks.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_tracks.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_tracks.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_tracks.setFixedHeight(150)
        sec2_layout.addWidget(self.tbl_tracks)

        self.chk_shuffle_bgm = QCheckBox("Ruota casualmente le tracce musicali della libreria tra le diverse storie in Coda Batch")
        sec2_layout.addWidget(self.chk_shuffle_bgm)
        layout.addWidget(sec2)

        # SEZIONE 3: AUTO-DUCKING DINAMICO
        sec3 = QFrame()
        sec3.setObjectName("CardSurface")
        sec3_layout = QVBoxLayout(sec3)
        sec3_layout.setContentsMargins(12, 10, 12, 10)
        sec3_layout.setSpacing(8)

        lbl_sec3 = QLabel("SEZIONE 3: AUTO-DUCKING DINAMICO SENZA POP/CLIC")
        lbl_sec3.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        sec3_layout.addWidget(lbl_sec3)

        self.chk_ducking_active = QCheckBox("Attiva Auto-Ducking Morbido (Curve continue senza gradini impulsivi)")
        self.chk_ducking_active.setChecked(True)
        sec3_layout.addWidget(self.chk_ducking_active)

        # Slider Voice Active
        row_voice = QHBoxLayout()
        self.lbl_voice_duck = QLabel("Volume Musica durante il Parlato:")
        self.lbl_voice_duck.setFixedWidth(240)
        self.sld_voice_duck = QSlider(Qt.Horizontal)
        self.sld_voice_duck.setRange(-36, -10)
        self.sld_voice_duck.setValue(int(BGM_DUCKING_DB))
        self.lbl_val_voice_duck = QLabel(f"{BGM_DUCKING_DB:.1f} dB")
        self.lbl_val_voice_duck.setFixedWidth(60)
        self.sld_voice_duck.valueChanged.connect(lambda v: self.lbl_val_voice_duck.setText(f"{float(v):.1f} dB"))
        row_voice.addWidget(self.lbl_voice_duck)
        row_voice.addWidget(self.sld_voice_duck)
        row_voice.addWidget(self.lbl_val_voice_duck)
        sec3_layout.addLayout(row_voice)

        # Slider Intro/Outro
        row_io = QHBoxLayout()
        self.lbl_io_duck = QLabel("Volume Musica durante Intro (0.5s) ed Outro (1.5s):")
        self.lbl_io_duck.setFixedWidth(240)
        self.sld_io_duck = QSlider(Qt.Horizontal)
        self.sld_io_duck.setRange(-24, -6)
        self.sld_io_duck.setValue(int(BGM_INTRO_OUTRO_DB))
        self.lbl_val_io_duck = QLabel(f"{BGM_INTRO_OUTRO_DB:.1f} dB")
        self.lbl_val_io_duck.setFixedWidth(60)
        self.sld_io_duck.valueChanged.connect(lambda v: self.lbl_val_io_duck.setText(f"{float(v):.1f} dB"))
        row_io.addWidget(self.lbl_io_duck)
        row_io.addWidget(self.sld_io_duck)
        row_io.addWidget(self.lbl_val_io_duck)
        sec3_layout.addLayout(row_io)

        layout.addWidget(sec3)

        # SEZIONE 4: ADATTAMENTO DURATA & MASTERING BROADCAST
        sec4 = QFrame()
        sec4.setObjectName("CardSurface")
        sec4_layout = QVBoxLayout(sec4)
        sec4_layout.setContentsMargins(12, 10, 12, 10)
        sec4_layout.setSpacing(8)

        lbl_sec4 = QLabel("SEZIONE 4: ADATTAMENTO DURATA & MASTERING BROADCAST (TRUE PEAK LIMITER)")
        lbl_sec4.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        sec4_layout.addWidget(lbl_sec4)

        row_loop = QHBoxLayout()
        lbl_loop = QLabel("Gestione Durata Traccia BGM:")
        lbl_loop.setFixedWidth(240)
        self.cmb_loop = QComboBox()
        self.cmb_loop.addItems([
            "Seamless Loop con Crossfade se più corta del video",
            "Trim Automatico con Fade-out a fine video"
        ])
        row_loop.addWidget(lbl_loop)
        row_loop.addWidget(self.cmb_loop)
        sec4_layout.addLayout(row_loop)

        row_mix = QHBoxLayout()
        lbl_mix = QLabel("Mixaggio Flussi Audio:")
        lbl_mix.setFixedWidth(240)
        self.cmb_mix = QComboBox()
        self.cmb_mix.addItems([
            "amix con normalize=0 (Eliminato volume=2, zero clipping)",
            "amix standard con pesi proporzionali"
        ])
        row_mix.addWidget(lbl_mix)
        row_mix.addWidget(self.cmb_mix)
        sec4_layout.addLayout(row_mix)

        row_limit = QHBoxLayout()
        lbl_limit = QLabel("Limiter Anti-Clipping Finale:")
        lbl_limit.setFixedWidth(240)
        self.cmb_limit = QComboBox()
        self.cmb_limit.addItems([
            f"True Peak Limiter a {TRUE_PEAK_LIMITER_DB:.1f} dB (alimiter=limit=-1.0dB:attack=5)",
            "Limiter Soft a -0.5 dB",
            "Nessun Limiter (Non raccomandato)"
        ])
        row_limit.addWidget(lbl_limit)
        row_limit.addWidget(self.cmb_limit)
        sec4_layout.addLayout(row_limit)

        layout.addWidget(sec4)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Footer con pulsanti di azione
        footer = QHBoxLayout()
        self.btn_reset = QPushButton("Ripristina Valori")
        self.btn_reset.clicked.connect(self._reset_defaults)
        footer.addWidget(self.btn_reset)

        self.btn_apply_all = QPushButton("🔗 Applica BGM a Tutte in Coda")
        self.btn_apply_all.clicked.connect(self._on_apply_to_all)
        footer.addWidget(self.btn_apply_all)

        footer.addStretch()

        self.btn_save_close = QPushButton("Salva & Chiudi (Auto-Saved)")
        self.btn_save_close.setObjectName("AccentButton")
        self.btn_save_close.clicked.connect(self.accept)
        footer.addWidget(self.btn_save_close)

        main_layout.addLayout(footer)

    def _load_tracks_into_table(self):
        tracks = self.bgm_manager.list_available_tracks()
        self.tbl_tracks.setRowCount(len(tracks))
        for row, t in enumerate(tracks):
            self.tbl_tracks.setItem(row, 0, QTableWidgetItem(t.title))
            mins = int(t.duration_sec // 60)
            secs = int(t.duration_sec % 60)
            self.tbl_tracks.setItem(row, 1, QTableWidgetItem(f"{mins}m {secs:02d}s"))
            self.tbl_tracks.setItem(row, 2, QTableWidgetItem(f"{BGM_TARGET_LUFS:.1f} LUFS"))

            btn_sel = QPushButton()
            if self.selected_track_id == t.id:
                btn_sel.setText("ASSEGNATA 🟢")
                btn_sel.setStyleSheet("color: #729B84; font-weight: bold;")
            else:
                btn_sel.setText("Scegli per Questa Storia")
                btn_sel.clicked.connect(lambda checked=False, tid=t.id: self._select_track(tid))
            self.tbl_tracks.setCellWidget(row, 3, btn_sel)

    def _select_track(self, track_id: int):
        self.selected_track_id = track_id
        self._load_tracks_into_table()
        log.info(f"BGM track #{track_id} selected.")

    def _start_download_youtube(self):
        text = self.txt_yt_urls.toPlainText().strip()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            QMessageBox.warning(self, "Attenzione", "Inserisci almeno un link di YouTube.")
            return

        target_url = lines[0]
        self.lbl_yt_status.setText(f"⏳ Download ed estrazione audio in corso: {target_url}...")
        self.btn_download_yt.setEnabled(False)

        self.download_worker = BgmDownloadWorker(self.bgm_manager, target_url)
        self.download_worker.finished_track.connect(self._on_download_complete)
        self.download_worker.error_occurred.connect(self._on_download_error)
        self.download_worker.start()

    def _on_download_complete(self, track: BgmTrackInfo):
        self.btn_download_yt.setEnabled(True)
        self.lbl_yt_status.setText(f"🟢 \"{track.title}\" scaricato, silenzi rimossi e normalizzato a -24.0 LUFS.")
        self.selected_track_id = track.id
        self._load_tracks_into_table()

    def _on_download_error(self, err_msg: str):
        self.btn_download_yt.setEnabled(True)
        self.lbl_yt_status.setText(f"🔴 Errore download: {err_msg}")

    def _reset_defaults(self):
        self.chk_ducking_active.setChecked(True)
        self.sld_voice_duck.setValue(int(BGM_DUCKING_DB))
        self.sld_io_duck.setValue(int(BGM_INTRO_OUTRO_DB))
        self.chk_shuffle_bgm.setChecked(False)
        self.cmb_loop.setCurrentIndex(0)
        self.cmb_mix.setCurrentIndex(0)
        self.cmb_limit.setCurrentIndex(0)

    def _apply_initial_settings(self):
        if "voice_duck_db" in self.current_settings:
            self.sld_voice_duck.setValue(int(self.current_settings["voice_duck_db"]))
        if "intro_outro_duck_db" in self.current_settings:
            self.sld_io_duck.setValue(int(self.current_settings["intro_outro_duck_db"]))
        if "ducking_active" in self.current_settings:
            self.chk_ducking_active.setChecked(bool(self.current_settings["ducking_active"]))
        if "shuffle_bgm" in self.current_settings:
            self.chk_shuffle_bgm.setChecked(bool(self.current_settings["shuffle_bgm"]))

    def get_settings(self) -> dict:
        return {
            "bgm_track_id": self.selected_track_id,
            "ducking_active": self.chk_ducking_active.isChecked(),
            "voice_duck_db": float(self.sld_voice_duck.value()),
            "intro_outro_duck_db": float(self.sld_io_duck.value()),
            "shuffle_bgm": self.chk_shuffle_bgm.isChecked(),
            "loop_mode": self.cmb_loop.currentText(),
            "mix_mode": self.cmb_mix.currentText(),
            "limiter_mode": self.cmb_limit.currentText()
        }

    def _on_apply_to_all(self):
        settings = self.get_settings()
        self.apply_to_all_requested.emit(settings)
        QMessageBox.information(self, "Applicato a Tutte", "Le impostazioni BGM e Mastering sono state propagate a tutte le storie in coda.")

    def closeEvent(self, event):
        # Auto-Save on Close
        settings = self.get_settings()
        self.settings_saved.emit(settings)
        super().closeEvent(event)

    def accept(self):
        settings = self.get_settings()
        self.settings_saved.emit(settings)
        super().accept()

