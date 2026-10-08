"""AI Short Generator 1.0 - Subtitle Styler Card Component"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QWidget
)
from PySide6.QtCore import Signal
from app.config import DEFAULT_FONT_NAME, DEFAULT_TEXT_COLOR, DEFAULT_HIGHLIGHT_COLOR


class SubtitleStylerCard(QFrame):
    """Card di configurazione e preset per i Sottotitoli & Sincronizzazione."""

    settings_drawer_requested = Signal()
    preset_changed = Signal(dict)

    PRESETS = {
        "Viral Pop (Sabbia Calda)": {
            "font_name": "Montserrat Black",
            "font_size": 68,
            "primary_color_hex": "#DCE0EA",
            "highlight_color_hex": "#DCE0EA",
            "outline_color_hex": "#181A20",
            "animation_style": "WORD_POP"
        },
        "Slate Crime Thriller": {
            "font_name": "Anton",
            "font_size": 72,
            "primary_color_hex": "#FFFFFF",
            "highlight_color_hex": "#FFFFFF",
            "outline_color_hex": "#181A20",
            "animation_style": "KARAOKE_LINEAR"
        },
        "Clean Minimalist": {
            "font_name": "The Bold Font",
            "font_size": 66,
            "primary_color_hex": "#F0F2F5",
            "highlight_color_hex": "#F0F2F5",
            "outline_color_hex": "#181A20",
            "animation_style": "WORD_POP"
        }
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CardSurface")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header_lbl = QLabel("4. SOTTOTITOLI & SINCRONIZZAZIONE")
        header_lbl.setObjectName("SectionHeader")
        layout.addWidget(header_lbl)

        # Riga Preset
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Preset Stile:"))
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(list(self.PRESETS.keys()))
        self.combo_preset.currentTextChanged.connect(self._on_preset_change)
        row1.addWidget(self.combo_preset, stretch=1)
        layout.addLayout(row1)

        # Box informazioni tecniche
        info_box = QFrame()
        info_box.setObjectName("InnerCard")
        info_layout = QVBoxLayout(info_box)
        info_layout.setContentsMargins(8, 6, 8, 6)
        info_layout.setSpacing(4)

        b1 = QLabel("Auto-Wrap: [ Bounding Box <= 880px, 2 righe max ]")
        b1.setObjectName("HelperText")
        b2 = QLabel("Timing: +0.5s pre / +1.5s outro (CTA a -1.0s)")
        b2.setObjectName("HelperText")
        info_layout.addWidget(b1)
        info_layout.addWidget(b2)
        layout.addWidget(info_box)

        # Pulsante Drawer
        btn_row = QHBoxLayout()
        self.btn_settings = QPushButton("⚙️ Tipografia & Personalizzazione Avanzata")
        self.btn_settings.clicked.connect(self.settings_drawer_requested.emit)
        btn_row.addWidget(self.btn_settings)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_preset_change(self, preset_name: str):
        cfg = self.PRESETS.get(preset_name, self.PRESETS["Viral Pop (Sabbia Calda)"])
        self.preset_changed.emit(cfg)

    def get_config(self) -> Dict[str, Any]:
        preset_name = self.combo_preset.currentText()
        return self.PRESETS.get(preset_name, self.PRESETS["Viral Pop (Sabbia Calda)"])

