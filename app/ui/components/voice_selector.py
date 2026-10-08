"""AI Short Generator 1.0 - Voice Selector Card Component"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QWidget
)
from PySide6.QtCore import Signal
from app.config import DEFAULT_SPEAKER, DEFAULT_INSTRUCT


class VoiceSelectorCard(QFrame):
    """Card di selezione rapida per la Suite Voce Qwen3-TTS (en-US)."""

    audition_requested = Signal()
    studio_requested = Signal()
    voice_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CardSurface")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header_lbl = QLabel("2. SUITE VOCE QWEN3-TTS (en-US)")
        header_lbl.setObjectName("SectionHeader")
        layout.addWidget(header_lbl)

        # Riga controlli speaker e lingua
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Speaker:"))
        self.combo_speaker = QComboBox()
        self.combo_speaker.addItems([
            "Ryan (Natural Warm Male - en-US)",
            "Vivian (Warm Female - en-US)",
            "Aiden (Dynamic Young Narrator - en-US)",
            "Emma (Expressive Narrator - en-US)"
        ])
        self.combo_speaker.currentIndexChanged.connect(self._on_change)
        row1.addWidget(self.combo_speaker, stretch=1)

        row1.addWidget(QLabel("Lingua:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["🇺🇸 English (US)"])
        row1.addWidget(self.combo_lang)
        layout.addLayout(row1)

        # Riga Stile e Azioni
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Stile:"))
        self.combo_style = QComboBox()
        self.combo_style.addItems([
            "Viral Hook (High Energy)",
            "Dark Mystery & Crime",
            "Tech & Science Facts",
            "Inspiring Motivational"
        ])
        self.combo_style.currentIndexChanged.connect(self._on_change)
        row2.addWidget(self.combo_style, stretch=1)

        self.btn_audition = QPushButton("▶ Ascolta Live ~97ms")
        self.btn_audition.clicked.connect(self.audition_requested.emit)

        self.btn_studio = QPushButton("⚙️ Studio Voce Completo")
        self.btn_studio.clicked.connect(self.studio_requested.emit)

        row2.addWidget(self.btn_audition)
        row2.addWidget(self.btn_studio)
        layout.addLayout(row2)

    def _on_change(self):
        self.voice_changed.emit(self.get_config())

    def get_config(self) -> Dict[str, Any]:
        spk_text = self.combo_speaker.currentText()
        speaker = spk_text.split(" ")[0]
        style = self.combo_style.currentText()
        return {
            "speaker": speaker,
            "speaker_full": spk_text,
            "language": "English",
            "instruct": style,
            "type": "Custom Voice"
        }

    def set_config(self, cfg: dict):
        self.blockSignals(True)
        try:
            spk = cfg.get("speaker", "Ryan")
            found_spk = False
            for i in range(self.combo_speaker.count()):
                if spk in self.combo_speaker.itemText(i):
                    self.combo_speaker.setCurrentIndex(i)
                    found_spk = True
                    break
            if not found_spk and spk:
                self.combo_speaker.addItem(f"{spk} (Custom)")
                self.combo_speaker.setCurrentIndex(self.combo_speaker.count() - 1)

            inst = cfg.get("instruct", "")
            if inst:
                for i in range(self.combo_style.count()):
                    item_words = [w.lower() for w in self.combo_style.itemText(i).split()[:2]]
                    if any(w in inst.lower() for w in item_words):
                        self.combo_style.setCurrentIndex(i)
                        break
        finally:
            self.blockSignals(False)

