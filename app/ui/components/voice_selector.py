"""AI Short Generator 1.0 - Voice Selector Card Component"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QWidget
)
from PySide6.QtCore import Signal
from app.config import DEFAULT_SPEAKER, DEFAULT_INSTRUCT, QWEN_DEFAULT_VOICES


class VoiceSelectorCard(QFrame):
    """Card di selezione rapida per la Suite Voce Qwen3-TTS (en-US & Multilingual)."""

    audition_requested = Signal()
    studio_requested = Signal()
    voice_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CardSurface")
        self._current_config: Dict[str, Any] = {
            "speaker": "Ryan",
            "instruct": "Viral Hook (High Energy)",
            "speed": 1.00,
            "pitch": 0.0,
            "temperature": 0.70,
            "temp": 0.70
        }
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
        for v in QWEN_DEFAULT_VOICES:
            self.combo_speaker.addItem(v["display"], v["name"])
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

        self.btn_audition = QPushButton("▶ Ascolta Demo")
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
        speaker = self.combo_speaker.currentData() or spk_text.split(" ")[0].strip("(),:")
        style = self.combo_style.currentText()
        cfg = dict(self._current_config)
        cfg.update({
            "speaker": speaker,
            "speaker_full": spk_text,
            "language": "English",
            "instruct": style,
            "type": "Custom Voice"
        })
        if "pitch" not in cfg:
            cfg["pitch"] = 0.0
        if "temperature" not in cfg:
            cfg["temperature"] = cfg.get("temp", 0.70)
        if "temp" not in cfg:
            cfg["temp"] = cfg.get("temperature", 0.70)
        if "speed" not in cfg:
            cfg["speed"] = 1.00
        return cfg

    def set_config(self, cfg: dict):
        self.blockSignals(True)
        try:
            self._current_config.update(cfg)
            spk = cfg.get("speaker") or cfg.get("speaker_or_profile", "Ryan")
            spk_clean = str(spk).strip().lower().replace(" ", "_")
            found_spk = False
            for i in range(self.combo_speaker.count()):
                data_name = str(self.combo_speaker.itemData(i) or "").lower().replace(" ", "_")
                first_word = self.combo_speaker.itemText(i).split()[0].strip("(),:").lower().replace(" ", "_")
                if spk_clean in (data_name, first_word) or spk_clean == data_name or spk_clean == first_word:
                    self.combo_speaker.setCurrentIndex(i)
                    found_spk = True
                    break
            if not found_spk and spk:
                self.combo_speaker.addItem(f"{spk} (Custom)", spk)
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


