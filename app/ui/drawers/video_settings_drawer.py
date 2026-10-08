"""AI Short Generator 1.0 - Video Settings Drawer (9:16 Conform, Snapping, GC & NVENC)"""

import os
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QSlider, QCheckBox, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from app.config import (
    TARGET_WIDTH, TARGET_HEIGHT, TARGET_FPS,
    MIN_SHORT_DURATION_SEC, MAX_SHORT_DURATION_SEC,
    PADDING_INTRO_SEC, PADDING_OUTRO_SEC, TOTAL_PADDING_SEC,
    GC_DISCARD_BASELINE_SEC, GC_UPPER_TOLERANCE_SEC, GC_MAX_THRESHOLD_SEC,
    NVENC_PRESET, NVENC_CQ
)


class VideoSettingsDrawer(QDialog):
    """
    Drawer 2: Opzioni Video & Flusso Continuo (Soluzione B).
    Conform 9:16, Micro-snapping di scena, Garbage Collector 1m 30s (+20s / -inf),
    Padding 0.5s/1.5s e NVENC hardware encoder.
    """

    settings_saved = Signal(dict)

    def __init__(self, current_settings: Optional[dict] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_settings = current_settings or {}

        self.setWindowTitle("OPZIONI VIDEO & FLUSSO CONTINUO")
        self.resize(720, 650)
        self.setObjectName("DrawerWindow")

        self._init_ui()
        self._apply_initial_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(10)

        # Header con Auto-Save status badge
        header_bar = QHBoxLayout()
        lbl_title = QLabel("OPZIONI VIDEO & FLUSSO CONTINUO")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #DCE0EA;")
        header_bar.addWidget(lbl_title)
        header_bar.addStretch()

        lbl_autosave = QLabel("Auto-Save on Close: ON 🟢")
        lbl_autosave.setStyleSheet("font-size: 11px; font-weight: 600; color: #729B84; background-color: #21242C; padding: 4px 8px; border-radius: 4px; border: 1px solid #343946;")
        header_bar.addWidget(lbl_autosave)
        main_layout.addLayout(header_bar)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # SEZIONE 1: GESTIONE FLUSSO VIDEO CONTINUO & TAGLI ON-DEMAND
        sec1 = QFrame()
        sec1.setObjectName("CardSurface")
        sec1_layout = QVBoxLayout(sec1)
        sec1_layout.setContentsMargins(12, 10, 12, 10)
        sec1_layout.setSpacing(8)

        lbl_sec1 = QLabel("GESTIONE FLUSSO VIDEO CONTINUO & TAGLI ON-DEMAND (SOLUZIONE B)")
        lbl_sec1.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        sec1_layout.addWidget(lbl_sec1)

        row_c1 = QHBoxLayout()
        lbl_c1 = QLabel("Conform 9:16 su Ingestion:")
        lbl_c1.setFixedWidth(240)
        cmb_c1 = QComboBox()
        cmb_c1.addItems([f"{TARGET_WIDTH}x{TARGET_HEIGHT} @ {TARGET_FPS}fps (Automatico Zero-Recode)"])
        row_c1.addWidget(lbl_c1)
        row_c1.addWidget(cmb_c1)
        sec1_layout.addLayout(row_c1)

        row_c2 = QHBoxLayout()
        lbl_c2 = QLabel("Modalità di Taglio Video:")
        lbl_c2.setFixedWidth(240)
        self.cmb_cut_mode = QComboBox()
        self.cmb_cut_mode.addItems([
            "Just-In-Time su Durata Audio Reale (Silero VAD + 2.0s)",
            "Taglio Fisso Preventivo (Sconsigliato)"
        ])
        row_c2.addWidget(lbl_c2)
        row_c2.addWidget(self.cmb_cut_mode)
        sec1_layout.addLayout(row_c2)

        row_c3 = QHBoxLayout()
        lbl_c3 = QLabel("Scene Boundary Snapping:")
        lbl_c3.setFixedWidth(240)
        self.cmb_snap = QComboBox()
        self.cmb_snap.addItems([
            "Micro-snapping Bounded Right (±0.200s, max ±1.5s)",
            "Snapping Disattivato (Taglio netto al millisecondo)"
        ])
        row_c3.addWidget(lbl_c3)
        row_c3.addWidget(self.cmb_snap)
        sec1_layout.addLayout(row_c3)

        row_c4 = QHBoxLayout()
        lbl_c4 = QLabel("Soglia Minima Accettabile Reel:")
        lbl_c4.setFixedWidth(240)
        lbl_c4_val = QLabel(f"{MIN_SHORT_DURATION_SEC:.1f} secondi (Standard Reel)")
        lbl_c4_val.setStyleSheet("color: #729B84; font-weight: bold;")
        row_c4.addWidget(lbl_c4)
        row_c4.addWidget(lbl_c4_val)
        sec1_layout.addLayout(row_c4)

        row_c5 = QHBoxLayout()
        lbl_c5 = QLabel("Finestra Garbage Collector:")
        lbl_c5.setFixedWidth(240)
        lbl_c5_val = QLabel(f"1m 30s (+20s / -inf) -> eliminazione residui <= {GC_MAX_THRESHOLD_SEC:.0f}s")
        lbl_c5_val.setStyleSheet("color: #C4A36B;")
        row_c5.addWidget(lbl_c5)
        row_c5.addWidget(lbl_c5_val)
        sec1_layout.addLayout(row_c5)

        row_c6 = QHBoxLayout()
        lbl_c6 = QLabel("Riutilizzo Spazi da Rollback:")
        lbl_c6.setFixedWidth(240)
        lbl_c6_val = QLabel("Temporal Free-List (Best-Fit Allocation) 🟢 ATTIVO")
        lbl_c6_val.setStyleSheet("color: #729B84;")
        row_c6.addWidget(lbl_c6)
        row_c6.addWidget(lbl_c6_val)
        sec1_layout.addLayout(row_c6)

        layout.addWidget(sec1)

        # SEZIONE 2: FORMATO & INQUADRATURA VERTICALE (9:16)
        sec2 = QFrame()
        sec2.setObjectName("CardSurface")
        sec2_layout = QVBoxLayout(sec2)
        sec2_layout.setContentsMargins(12, 10, 12, 10)
        sec2_layout.setSpacing(8)

        lbl_sec2 = QLabel("FORMATO & INQUADRATURA VERTICALE (9:16)")
        lbl_sec2.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        sec2_layout.addWidget(lbl_sec2)

        row_adapt = QHBoxLayout()
        lbl_adapt = QLabel("Modalità Adattamento Ingestion:")
        lbl_adapt.setFixedWidth(240)
        self.cmb_adapt = QComboBox()
        self.cmb_adapt.addItems([
            "Ritaglio Intelligente al Centro (Smart Center Crop 9:16)",
            "Sfocatura Sfondo (Letterbox con Blur Laterale)",
            "Scala e Centra con Bande Nere (Aspect Ratio Puro)"
        ])
        row_adapt.addWidget(lbl_adapt)
        row_adapt.addWidget(self.cmb_adapt)
        sec2_layout.addLayout(row_adapt)

        row_res = QHBoxLayout()
        lbl_res = QLabel("Risoluzione Master Ingestion:")
        lbl_res.setFixedWidth(240)
        lbl_res_val = QLabel(f"{TARGET_WIDTH} x {TARGET_HEIGHT} (Full HD Verticale)")
        row_res.addWidget(lbl_res)
        row_res.addWidget(lbl_res_val)
        sec2_layout.addLayout(row_res)

        row_fps = QHBoxLayout()
        lbl_fps = QLabel("Frame Rate Target:")
        lbl_fps.setFixedWidth(240)
        self.cmb_fps = QComboBox()
        self.cmb_fps.addItems([f"{TARGET_FPS} FPS (Fluido)", "30 FPS"])
        row_fps.addWidget(lbl_fps)
        row_fps.addWidget(self.cmb_fps)
        sec2_layout.addLayout(row_fps)

        layout.addWidget(sec2)

        # SEZIONE 3: SINCRONIZZAZIONE & PADDING AUDIO-VIDEO (LEAD-IN 0.5s & OUTRO 1.5s)
        sec3 = QFrame()
        sec3.setObjectName("CardSurface")
        sec3_layout = QVBoxLayout(sec3)
        sec3_layout.setContentsMargins(12, 10, 12, 10)
        sec3_layout.setSpacing(8)

        lbl_sec3 = QLabel("SINCRONIZZAZIONE & PADDING AUDIO-VIDEO (LEAD-IN 0.5s & OUTRO 1.5s)")
        lbl_sec3.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        sec3_layout.addWidget(lbl_sec3)

        row_leadin = QHBoxLayout()
        lbl_leadin = QLabel("Lead-in Video (Anticipo Inizio):")
        lbl_leadin.setFixedWidth(240)
        self.sld_leadin = QSlider(Qt.Horizontal)
        self.sld_leadin.setRange(10, 100) # 0.10s - 1.00s in decimi di centesimo
        self.sld_leadin.setValue(int(PADDING_INTRO_SEC * 100))
        self.lbl_val_leadin = QLabel(f"{PADDING_INTRO_SEC:.2f} secondi")
        self.lbl_val_leadin.setFixedWidth(80)
        self.sld_leadin.valueChanged.connect(self._update_padding_display)
        row_leadin.addWidget(lbl_leadin)
        row_leadin.addWidget(self.sld_leadin)
        row_leadin.addWidget(self.lbl_val_leadin)
        sec3_layout.addLayout(row_leadin)

        row_leadout = QHBoxLayout()
        lbl_leadout = QLabel("Lead-out Video (Coda Post-Voce):")
        lbl_leadout.setFixedWidth(240)
        self.sld_leadout = QSlider(Qt.Horizontal)
        self.sld_leadout.setRange(50, 300) # 0.50s - 3.00s
        self.sld_leadout.setValue(int(PADDING_OUTRO_SEC * 100))
        self.lbl_val_leadout = QLabel(f"{PADDING_OUTRO_SEC:.2f} secondi")
        self.lbl_val_leadout.setFixedWidth(80)
        self.sld_leadout.valueChanged.connect(self._update_padding_display)
        row_leadout.addWidget(lbl_leadout)
        row_leadout.addWidget(self.sld_leadout)
        row_leadout.addWidget(self.lbl_val_leadout)
        sec3_layout.addLayout(row_leadout)

        self.lbl_formula = QLabel(
            "• Stacco Speech a -1.50s; Outro CTA Banner da -1.00s fino a fine video\n"
            f"• Durata Totale Short: T_video = (Durata Voce + {TOTAL_PADDING_SEC:.2f} s)"
        )
        self.lbl_formula.setStyleSheet("color: #BFA175; font-size: 11px;")
        sec3_layout.addWidget(self.lbl_formula)

        layout.addWidget(sec3)

        # SEZIONE 4: GESTIONE RISORSE HARDWARE
        sec4 = QFrame()
        sec4.setObjectName("CardSurface")
        sec4_layout = QVBoxLayout(sec4)
        sec4_layout.setContentsMargins(12, 10, 12, 10)
        sec4_layout.setSpacing(8)

        lbl_sec4 = QLabel("GESTIONE RISORSE HARDWARE & ENCODER")
        lbl_sec4.setStyleSheet("font-size: 12px; font-weight: 700; color: #6B82A6;")
        sec4_layout.addWidget(lbl_sec4)

        row_enc = QHBoxLayout()
        lbl_enc = QLabel("Encoder Video Utilizzato:")
        lbl_enc.setFixedWidth(240)
        self.cmb_enc = QComboBox()
        self.cmb_enc.addItems([
            "h264_nvenc (Accelerazione Hardware NVIDIA GPU)",
            "libx264 (Software CPU Fallback)"
        ])
        row_enc.addWidget(lbl_enc)
        row_enc.addWidget(self.cmb_enc)
        sec4_layout.addLayout(row_enc)

        row_nvp = QHBoxLayout()
        lbl_nvp = QLabel("Preset di Codifica NVENC:")
        lbl_nvp.setFixedWidth(240)
        self.cmb_nvp = QComboBox()
        self.cmb_nvp.addItems([
            f"Qualità Elevata (-cq {NVENC_CQ} / {NVENC_PRESET})",
            "Bilanciato (-cq 23 / p4)",
            "Veloce (-cq 28 / p2)"
        ])
        row_nvp.addWidget(lbl_nvp)
        row_nvp.addWidget(self.cmb_nvp)
        sec4_layout.addLayout(row_nvp)

        layout.addWidget(sec4)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Footer
        footer = QHBoxLayout()
        btn_reset = QPushButton("Ripristina Valori Predefiniti")
        btn_reset.clicked.connect(self._reset_defaults)
        footer.addWidget(btn_reset)
        footer.addStretch()

        btn_save = QPushButton("Salva & Chiudi (Auto-Save)")
        btn_save.setObjectName("AccentButton")
        btn_save.clicked.connect(self.accept)
        footer.addWidget(btn_save)
        main_layout.addLayout(footer)

    def _update_padding_display(self):
        leadin = self.sld_leadin.value() / 100.0
        leadout = self.sld_leadout.value() / 100.0
        tot = leadin + leadout
        self.lbl_val_leadin.setText(f"{leadin:.2f} s")
        self.lbl_val_leadout.setText(f"{leadout:.2f} s")
        self.lbl_formula.setText(
            f"• Stacco Speech a -{leadout:.2f}s; Outro CTA Banner da -1.00s fino a fine video\n"
            f"• Durata Totale Short: T_video = (Durata Voce + {tot:.2f} s)"
        )

    def _reset_defaults(self):
        self.cmb_cut_mode.setCurrentIndex(0)
        self.cmb_snap.setCurrentIndex(0)
        self.cmb_adapt.setCurrentIndex(0)
        self.cmb_fps.setCurrentIndex(0)
        self.sld_leadin.setValue(int(PADDING_INTRO_SEC * 100))
        self.sld_leadout.setValue(int(PADDING_OUTRO_SEC * 100))
        self.cmb_enc.setCurrentIndex(0)
        self.cmb_nvp.setCurrentIndex(0)
        self._update_padding_display()

    def _apply_initial_settings(self):
        if "lead_in_sec" in self.current_settings:
            self.sld_leadin.setValue(int(float(self.current_settings["lead_in_sec"]) * 100))
        if "lead_out_sec" in self.current_settings:
            self.sld_leadout.setValue(int(float(self.current_settings["lead_out_sec"]) * 100))
        if "adapt_mode" in self.current_settings:
            idx = self.cmb_adapt.findText(str(self.current_settings["adapt_mode"]))
            if idx >= 0:
                self.cmb_adapt.setCurrentIndex(idx)
        self._update_padding_display()

    def get_settings(self) -> dict:
        return {
            "cut_mode": self.cmb_cut_mode.currentText(),
            "snap_mode": self.cmb_snap.currentText(),
            "adapt_mode": self.cmb_adapt.currentText(),
            "target_fps": TARGET_FPS if self.cmb_fps.currentIndex() == 0 else 30,
            "lead_in_sec": self.sld_leadin.value() / 100.0,
            "lead_out_sec": self.sld_leadout.value() / 100.0,
            "encoder": "h264_nvenc" if self.cmb_enc.currentIndex() == 0 else "libx264",
            "nvenc_preset": NVENC_PRESET if self.cmb_nvp.currentIndex() == 0 else "p4",
            "nvenc_cq": NVENC_CQ if self.cmb_nvp.currentIndex() == 0 else 23
        }

    def closeEvent(self, event):
        settings = self.get_settings()
        self.settings_saved.emit(settings)
        super().closeEvent(event)

    def accept(self):
        settings = self.get_settings()
        self.settings_saved.emit(settings)
        super().accept()

