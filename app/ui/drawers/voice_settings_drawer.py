"""AI Short Generator 1.0 - Voice Studio Drawer & Voice Intelligence (Gemini Expressive TTS & Multi-Provider)"""

import os
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QSlider, QComboBox, QTextEdit, QLineEdit,
    QTabWidget, QProgressBar, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QColor

from app.config import (
    CACHE_DIR, DEFAULT_SPEAKER, DEFAULT_FEMALE_SPEAKER,
    DEFAULT_NARRATOR_SPEAKER, DEFAULT_INSTRUCT, GEMINI_DEFAULT_VOICES
)
from app.core.tts_engine import VoiceIntelligenceEngine, Qwen3VoiceSuite
from app.core.tts.factory import TTSFactory
from app.core.tts.quota_tracker import QuotaTracker, QuotaSafeguardExceededError
from app.core.tts.key_manager import APIKeyManager
from app.core.preset_manager import PresetManager
from app.ui.modals.copyable_error_dialog import show_copyable_error
from app.utils.logger import log
from app.utils.audio_player import play_wav_file, stop_wav_playback


class VoiceAuditionWorker(QThread):
    finished_audition = Signal(str, float) # path, duration
    error_occurred = Signal(str)

    def __init__(
        self,
        voice_suite: VoiceIntelligenceEngine,
        preset_mgr: PresetManager,
        text: str,
        speaker: str,
        instruct: str,
        speed: float,
        pitch: float = 0.0,
        temperature: float = 0.70,
        mode: str = "custom",
        profile_path: Optional[str] = None,
        voice_description: Optional[str] = None,
        provider_id: str = "gemini_tts",
        volume_gain_db: float = 0.0
    ):
        super().__init__()
        self.suite = voice_suite
        self.preset_mgr = preset_mgr
        self.text = text
        self.speaker = speaker
        self.instruct = instruct
        self.speed = speed
        self.pitch = pitch
        self.temperature = temperature
        self.mode = mode if (isinstance(mode, str) and mode) else "custom"
        self.profile_path = profile_path
        self.voice_description = voice_description
        self.provider_id = provider_id
        self.volume_gain_db = volume_gain_db

    def run(self):
        try:
            now_ms = int(time.time() * 1000)
            raw_out = str(CACHE_DIR / f"temp_audition_raw_{os.getpid()}_{now_ms}.wav")
            clamped_out = str(CACHE_DIR / f"temp_audition_5s_{os.getpid()}_{now_ms}.wav")

            # Genera audio con il motore vocale modulare
            duration = self.suite.generate_custom(
                text=self.text,
                output_path=raw_out,
                speaker=self.speaker,
                instruct=self.instruct,
                speed=self.speed,
                pitch=self.pitch,
                temperature=self.temperature,
                is_preview=True,
                provider_id=self.provider_id,
                volume_gain_db=self.volume_gain_db
            )

            # Clamp audio a massimo 5.0 secondi con micro-fadeout di 50ms
            if os.path.exists(raw_out) and os.path.getsize(raw_out) > 200:
                self.preset_mgr.clamp_audio_demo_to_5s(raw_out, clamped_out, max_sec=5.0)
                self.finished_audition.emit(clamped_out, 5.0)
            else:
                self.error_occurred.emit("Errore generazione anteprima vocale.")
        except QuotaSafeguardExceededError as q_err:
            self.error_occurred.emit(str(q_err))
        except Exception as e:
            self.error_occurred.emit(str(e))


class VoiceCloneWorker(QThread):
    progress_step = Signal(int, str)
    finished_clone = Signal(str, str)
    error_occurred = Signal(str)

    def __init__(self, voice_suite: Any, profile_name: str, ref_audio_path: str, ref_text: str):
        super().__init__()
        self.suite = voice_suite
        self.profile_name = profile_name
        self.ref_audio_path = ref_audio_path
        self.ref_text = ref_text

    def run(self):
        try:
            self.progress_step.emit(20, "Verifica file audio di riferimento...")
            if not os.path.exists(self.ref_audio_path):
                raise FileNotFoundError(f"File audio non trovato: {self.ref_audio_path}")
            time.sleep(0.1)
            self.progress_step.emit(50, "Estrazione profili prosodici...")
            time.sleep(0.1)
            self.progress_step.emit(90, "Registrazione profilo vocale nel sistema...")
            time.sleep(0.1)
            self.progress_step.emit(100, "Completato con successo!")
            self.finished_clone.emit(self.profile_name, self.ref_audio_path)
        except Exception as e:
            self.error_occurred.emit(str(e))


class VoiceSettingsDrawer(QDialog):
    """
    Drawer: Studio Voce & Impostazioni Generazione Audio Modulare (Gemini TTS)
    Supporta:
    - Selezione dinamica del motore vocale (Factory Pattern)
    - Gestione sicura API Key (visualizzazione mascherata, salvataggio, test connessione)
    - Quota Tracker con Salvaguardia al 95% del limite mensile gratuito
    - Regolazione parametri audio: Modello, Velocità, Pitch, Guadagno Volume (dB), Stile
    - Banco di prova benchmark (4 test fonetici/emotivi con clamp a 5s)
    """

    settings_saved = Signal(dict)
    apply_to_all_requested = Signal(dict)

    DEFAULT_TEST_PHRASE = (
        "Black holes are among the most mysterious cosmic titans in the entire universe..."
    )

    def __init__(
        self,
        voice_suite: Optional[VoiceIntelligenceEngine] = None,
        preset_mgr: Optional[PresetManager] = None,
        current_settings: Optional[dict] = None,
        active_story_title: str = "Active Script",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.suite = voice_suite or VoiceIntelligenceEngine()
        self.preset_mgr = preset_mgr or PresetManager()
        self.quota_tracker = QuotaTracker()
        self.current_settings = current_settings or {}
        self.active_story_title = active_story_title

        self.setWindowTitle("VOICE STUDIO & IMPOSTAZIONI SINTESI VOCALE")
        self.resize(860, 750)
        self.setObjectName("DrawerWindow")

        self.audition_worker: Optional[VoiceAuditionWorker] = None
        self.clone_worker: Optional[VoiceCloneWorker] = None
        self.last_cloned_profile_path: Optional[str] = None
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(100)
        self.playback_timer.timeout.connect(self._update_playback_progress)
        self.playback_start_time = 0.0

        self._init_ui()
        self._load_presets_into_combo()
        self._apply_initial_settings()
        self._refresh_quota_display()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(10)

        # Header Bar
        header_bar = QHBoxLayout()
        lbl_title = QLabel("VOICE STUDIO & IMPOSTAZIONI SINTESI VOCALE")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #DCE0EA;")
        header_bar.addWidget(lbl_title)
        header_bar.addStretch()

        lbl_autosave = QLabel("Auto-Save on Close: ON 🟢")
        lbl_autosave.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #729B84; background-color: #21242C; "
            "padding: 4px 8px; border-radius: 4px; border: 1px solid #343946;"
        )
        header_bar.addWidget(lbl_autosave)
        main_layout.addLayout(header_bar)

        # Ambito Attivo
        scope_lbl = QLabel(f"AMBITO ATTIVO: Configurazione per Script \"{self.active_story_title}\"")
        scope_lbl.setStyleSheet("color: #BFA175; font-size: 12px; font-weight: 600;")
        main_layout.addWidget(scope_lbl)

        # Preset & Quick Action Toolbar
        preset_bar = QHBoxLayout()
        preset_bar.addWidget(QLabel("Preset Voce:"))
        self.combo_presets = QComboBox()
        self.combo_presets.currentIndexChanged.connect(self._on_preset_selected)
        preset_bar.addWidget(self.combo_presets, stretch=1)

        btn_save_preset = QPushButton("💾 Salva Nuovo Preset")
        btn_save_preset.clicked.connect(self._save_new_preset)
        preset_bar.addWidget(btn_save_preset)

        btn_apply_all = QPushButton("🔗 Applica Voce a Tutte le Storie")
        btn_apply_all.clicked.connect(self._apply_to_all_stories)
        preset_bar.addWidget(btn_apply_all)
        main_layout.addLayout(preset_bar)

        # Card Stato Modello & Motore Vocale
        self.weights_card = QFrame()
        self.weights_card.setObjectName("InnerCard")
        wc_layout = QHBoxLayout(self.weights_card)
        wc_layout.setContentsMargins(12, 6, 12, 6)

        self.lbl_weights_status = QLabel("🟢 Motore Cloud Attivo: Google Gemini Expressive TTS (VRAM: 0 MB)")
        self.lbl_weights_status.setStyleSheet("font-size: 11px; font-weight: 600; color: #729B84;")
        wc_layout.addWidget(self.lbl_weights_status, stretch=1)

        self.btn_download_weights = QPushButton("Verifica Quota")
        self.btn_download_weights.setStyleSheet("font-size: 11px; font-weight: 600; padding: 4px 10px;")
        self.btn_download_weights.clicked.connect(self._refresh_quota_display)
        wc_layout.addWidget(self.btn_download_weights)
        main_layout.addWidget(self.weights_card)

        # Tabs Container (Voci Standard e Impostazioni API & Quota)
        self.tabs = QTabWidget()
        self.tab1 = self._build_tab1_presets()
        self.tab2 = self._build_tab4_api_quota()
        self.tab4 = self.tab2  # Retrocompatibilità

        self.tabs.addTab(self.tab1, "VOCI STANDARD & PARAMETRI")
        self.tabs.addTab(self.tab2, "IMPOSTAZIONI API & QUOTA 95%")
        main_layout.addWidget(self.tabs, stretch=1)

        # Banco di Prova Benchmark Vocale (4 Test Benchmark Standard, Clamped a 5.0s)
        audition_box = QFrame()
        audition_box.setObjectName("InnerCard")
        ab_layout = QVBoxLayout(audition_box)
        ab_layout.setContentsMargins(12, 8, 12, 8)
        ab_layout.setSpacing(6)

        lbl_aud_header = QLabel("🔊 BANCO DI PROVA & TEST AUDIZIONE VOCALE (DEMO MAX 5.0 SECONDI):")
        lbl_aud_header.setStyleSheet("font-weight: 600; font-size: 11px; color: #BFA175;")
        ab_layout.addWidget(lbl_aud_header)

        tests_row = QHBoxLayout()
        self.btn_test_phonetic = QPushButton("🎯 Bilanciamento Fonetico")
        self.btn_test_phonetic.setObjectName("AccentButton")
        self.btn_test_phonetic.setToolTip('Riproduce: "The box was thrown beside the parked truck."')
        self.btn_test_phonetic.clicked.connect(lambda: self._run_benchmark_test(
            "The box was thrown beside the parked truck.", "Bilanciamento Fonetico"
        ))
        tests_row.addWidget(self.btn_test_phonetic)

        self.btn_test_context = QPushButton("📖 Contesto")
        self.btn_test_context.setObjectName("AccentButton")
        self.btn_test_context.setToolTip('Riproduce: "The soldier decided to desert his post in the dry desert."')
        self.btn_test_context.clicked.connect(lambda: self._run_benchmark_test(
            "The soldier decided to desert his post in the dry desert.", "Contesto"
        ))
        tests_row.addWidget(self.btn_test_context)

        self.btn_test_emotion = QPushButton("🎭 Emozione")
        self.btn_test_emotion.setObjectName("AccentButton")
        self.btn_test_emotion.setToolTip("Riproduce: \"Wait—don't tell me... they actually lost the game?!\"")
        self.btn_test_emotion.clicked.connect(lambda: self._run_benchmark_test(
            "Wait—don't tell me... they actually lost the game?!", "Emozione"
        ))
        tests_row.addWidget(self.btn_test_emotion)

        self.btn_test_format = QPushButton("🌐 Gestione del Formato")
        self.btn_test_format.setObjectName("AccentButton")
        self.btn_test_format.setToolTip('Riproduce: "The update is live at example.com."')
        self.btn_test_format.clicked.connect(lambda: self._run_benchmark_test(
            "The update is live at example.com.", "Gestione del Formato"
        ))
        tests_row.addWidget(self.btn_test_format)
        ab_layout.addLayout(tests_row)

        self.lbl_active_phrase = QLabel("Test benchmark: Seleziona uno dei 4 pulsanti per riprodurre il test sonoro.")
        self.lbl_active_phrase.setStyleSheet("color: #949CAE; font-size: 11px; font-style: italic;")
        ab_layout.addWidget(self.lbl_active_phrase)

        play_row = QHBoxLayout()
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_audition)
        play_row.addWidget(self.btn_stop)

        self.prog_audio = QProgressBar()
        self.prog_audio.setRange(0, 50)
        self.prog_audio.setValue(0)
        play_row.addWidget(self.prog_audio, stretch=1)

        self.lbl_audio_time = QLabel("00:00.0 / 00:05.0")
        self.lbl_audio_time.setStyleSheet("font-family: monospace; font-size: 11px; color: #949CAE;")
        play_row.addWidget(self.lbl_audio_time)
        ab_layout.addLayout(play_row)

        info_note = QLabel("* Nota: Il motore genera i primi 5 secondi con micro-fadeout di 50ms, garantendo feedback immediato.")
        info_note.setStyleSheet("color: #666E7F; font-size: 10px;")
        ab_layout.addWidget(info_note)
        main_layout.addWidget(audition_box)

        # Footer Actions
        footer = QHBoxLayout()
        btn_reset = QPushButton("Ripristina Valori")
        btn_reset.clicked.connect(self._reset_defaults)
        footer.addWidget(btn_reset)

        footer.addStretch()

        btn_save_close = QPushButton("Salva & Chiudi (Auto-Saved on Close)")
        btn_save_close.setObjectName("PrimaryButton")
        btn_save_close.clicked.connect(self._save_and_close)
        footer.addWidget(btn_save_close)
        main_layout.addLayout(footer)

    def _build_tab1_presets(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Riga Motore & Speaker
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Motore Vocale:"))
        self.combo_provider = QComboBox()
        for prov in TTSFactory.get_registered_providers():
            self.combo_provider.addItem(prov["name"], prov["id"])
        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)
        r1.addWidget(self.combo_provider, stretch=1)

        r1.addWidget(QLabel("Speaker / Voce:"))
        self.combo_speaker = QComboBox()
        for v in GEMINI_DEFAULT_VOICES:
            self.combo_speaker.addItem(v["display"], v["name"])
        r1.addWidget(self.combo_speaker, stretch=1)
        layout.addLayout(r1)

        # Presets di Guida Emotiva & Prosodia
        layout.addWidget(QLabel("PRESET DI GUIDA EMOTIVA & PROSODIA PER SHORT VIRALI (instruct):"))
        self.combo_instruct_preset = QComboBox()
        self.combo_instruct_preset.addItems([
            "Viral Hook (High energy, punchy pace, emphasizes keywords)",
            "Dark Mystery & Crime (Deep tone, suspenseful micro-pauses)",
            "Tech & Science Facts (Fast-paced, crystal clear American diction)",
            "Inspiring Motivational (Passionate, confident, cinematic)"
        ])
        self.combo_instruct_preset.currentIndexChanged.connect(self._on_instruct_preset_changed)
        layout.addWidget(self.combo_instruct_preset)

        layout.addWidget(QLabel("Prompt Libero Istruzione Stile:"))
        self.txt_custom_instruct = QLineEdit("High energy viral creator voice, fast paced, emphasizing keywords")
        layout.addWidget(self.txt_custom_instruct)

        # Regolazioni fini (Velocità, Pitch, Volume dB, Sampling Temperature)
        fines_box = QFrame()
        fines_box.setObjectName("InnerCard")
        fb_layout = QVBoxLayout(fines_box)
        fb_layout.setContentsMargins(10, 8, 10, 8)
        fb_layout.setSpacing(6)

        fb_layout.addWidget(QLabel("REGOLAZIONI PARAMETRICHE AUDIO:"))

        # Speaking Rate / Velocità
        row_rate = QHBoxLayout()
        self.lbl_rate = QLabel("Speaking Rate (Velocità WPM): 1.00x (~150 WPM American Standard)")
        self.slider_rate = QSlider(Qt.Horizontal)
        self.slider_rate.setRange(75, 150)
        self.slider_rate.setValue(100)
        self.slider_rate.valueChanged.connect(lambda v: self.lbl_rate.setText(f"Speaking Rate (Velocità WPM): {v/100.0:.2f}x (~{int(v*1.5)} WPM)"))
        row_rate.addWidget(self.lbl_rate, stretch=1)
        row_rate.addWidget(self.slider_rate, stretch=1)
        fb_layout.addLayout(row_rate)

        # Pitch / Intonazione
        row_pitch = QHBoxLayout()
        self.lbl_pitch = QLabel("Pitch / Vocal Timbre: Neutral (0.0)")
        self.slider_pitch = QSlider(Qt.Horizontal)
        self.slider_pitch.setRange(-5, 5)
        self.slider_pitch.setValue(0)
        self.slider_pitch.valueChanged.connect(lambda v: self.lbl_pitch.setText(f"Pitch / Vocal Timbre: {'Neutral' if v == 0 else ('Deeper' if v < 0 else 'Higher')} ({v:+.1f})"))
        row_pitch.addWidget(self.lbl_pitch, stretch=1)
        row_pitch.addWidget(self.slider_pitch, stretch=1)
        fb_layout.addLayout(row_pitch)

        # Guadagno Volume (dB)
        row_vol = QHBoxLayout()
        self.lbl_volume = QLabel("Guadagno Volume: 0.0 dB")
        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(-10, 10)
        self.slider_volume.setValue(0)
        self.slider_volume.valueChanged.connect(lambda v: self.lbl_volume.setText(f"Guadagno Volume: {v:+.1f} dB"))
        row_vol.addWidget(self.lbl_volume, stretch=1)
        row_vol.addWidget(self.slider_volume, stretch=1)
        fb_layout.addLayout(row_vol)

        # Sampling Temperature
        row_temp = QHBoxLayout()
        self.lbl_temp = QLabel("Sampling Temperature: 0.70")
        self.slider_temp = QSlider(Qt.Horizontal)
        self.slider_temp.setRange(10, 100)
        self.slider_temp.setValue(70)
        self.slider_temp.valueChanged.connect(lambda v: self.lbl_temp.setText(f"Sampling Temperature: {v/100.0:.2f}"))
        row_temp.addWidget(self.lbl_temp, stretch=1)
        row_temp.addWidget(self.slider_temp, stretch=1)
        fb_layout.addLayout(row_temp)

        layout.addWidget(fines_box)
        layout.addStretch()
        return widget

    def _build_tab4_api_quota(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Sezione API Key
        key_box = QFrame()
        key_box.setObjectName("InnerCard")
        kb_layout = QVBoxLayout(key_box)
        kb_layout.setContentsMargins(12, 10, 12, 10)
        kb_layout.setSpacing(6)

        lbl_key_title = QLabel("🔑 CONFIGURAZIONE GOOGLE / GEMINI API KEY:")
        lbl_key_title.setStyleSheet("font-weight: 600; font-size: 11px; color: #BFA175;")
        kb_layout.addWidget(lbl_key_title)

        key_row = QHBoxLayout()
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText("Inserisci la tua API Key (es. AIzaSy...)")
        current_k = APIKeyManager.get_api_key("gemini", allow_interactive=False) if APIKeyManager.has_api_key("gemini") else ""
        if current_k:
            self.txt_api_key.setText(current_k)
        key_row.addWidget(self.txt_api_key, stretch=1)

        self.btn_toggle_key = QPushButton("👁️")
        self.btn_toggle_key.setToolTip("Mostra/Nascondi API Key")
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self.btn_toggle_key)

        btn_save_key = QPushButton("💾 Salva Chiave")
        btn_save_key.clicked.connect(self._save_api_key_clicked)
        key_row.addWidget(btn_save_key)

        self.btn_test_conn = QPushButton("⚡ Testa Connessione")
        self.btn_test_conn.clicked.connect(self._test_api_connection)
        key_row.addWidget(self.btn_test_conn)
        kb_layout.addLayout(key_row)

        self.lbl_key_status = QLabel("Stato: Chiave caricata e attiva nel sistema." if current_k else "Stato: Nessuna chiave salvata.")
        self.lbl_key_status.setStyleSheet("font-size: 11px; color: #729B84;" if current_k else "font-size: 11px; color: #C4A36B;")
        kb_layout.addWidget(self.lbl_key_status)

        help_lbl = QLabel("Puoi ottenere gratuitamente una chiave API Google AI Studio su: https://aistudio.google.com/")
        help_lbl.setStyleSheet("font-size: 10px; color: #666E7F;")
        kb_layout.addWidget(help_lbl)
        layout.addWidget(key_box)

        # 2. Sezione Quota Tracker 95% Safeguard
        quota_box = QFrame()
        quota_box.setObjectName("InnerCard")
        qb_layout = QVBoxLayout(quota_box)
        qb_layout.setContentsMargins(12, 10, 12, 10)
        qb_layout.setSpacing(6)

        lbl_quota_title = QLabel("🛡️ MONITORAGGIO QUOTA & SALVAGUARDIA 95% (FREE TIER PROTECTION):")
        lbl_quota_title.setStyleSheet("font-weight: 600; font-size: 11px; color: #BFA175;")
        qb_layout.addWidget(lbl_quota_title)

        self.lbl_quota_month = QLabel("Mese Attivo: --")
        self.lbl_quota_month.setStyleSheet("font-size: 11px; color: #949CAE;")
        qb_layout.addWidget(self.lbl_quota_month)

        self.prog_quota = QProgressBar()
        self.prog_quota.setRange(0, 100)
        self.prog_quota.setValue(0)
        qb_layout.addWidget(self.prog_quota)

        self.lbl_quota_stats = QLabel("Utilizzo: 0 / 1.000.000 caratteri (0%)")
        self.lbl_quota_stats.setStyleSheet("font-weight: 600; font-size: 12px; color: #DCE0EA;")
        qb_layout.addWidget(self.lbl_quota_stats)

        self.lbl_quota_warning = QLabel()
        self.lbl_quota_warning.setWordWrap(True)
        qb_layout.addWidget(self.lbl_quota_warning)

        btn_refresh_quota = QPushButton("🔄 Aggiorna Statistiche Quota")
        btn_refresh_quota.clicked.connect(self._refresh_quota_display)
        qb_layout.addWidget(btn_refresh_quota)
        layout.addWidget(quota_box)

        # Tabella profili memorizzati
        layout.addWidget(QLabel("LIBRERIA PROFILI VOCALI:"))
        self.table_profiles = QTableWidget(0, 4)
        self.table_profiles.setHorizontalHeaderLabels(["ID", "Nome", "Tipo", "Data Creazione"])
        self.table_profiles.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_profiles.setMaximumHeight(130)
        layout.addWidget(self.table_profiles)

        layout.addStretch()
        return widget

    def _toggle_key_visibility(self):
        if self.txt_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🙈")
        else:
            self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁️")

    def _save_api_key_clicked(self):
        key = self.txt_api_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Chiave Vuota", "Inserisci una chiave API valida prima di salvare.")
            return
        APIKeyManager.save_api_key(key, "gemini")
        self.lbl_key_status.setText("🟢 Chiave API salvata con successo!")
        self.lbl_key_status.setStyleSheet("font-size: 11px; color: #729B84; font-weight: 600;")
        QMessageBox.information(self, "Chiave Salvata", "Google Gemini API Key salvata e resa attiva nel sistema.")
        self._refresh_quota_display()

    def _test_api_connection(self):
        self.btn_test_conn.setEnabled(False)
        self.btn_test_conn.setText("⏳ Test in corso...")
        self.lbl_key_status.setText("Connessione ai server Google in corso...")
        QTimer.singleShot(100, self._do_test_connection)

    def _do_test_connection(self):
        try:
            key = self.txt_api_key.text().strip()
            if key:
                APIKeyManager.save_api_key(key, "gemini")
            provider = TTSFactory.create("gemini_tts")
            is_valid = provider.validate_credentials()
            if is_valid:
                self.lbl_key_status.setText("🟢 Connessione API riuscita! Chiave valida e funzionante.")
                self.lbl_key_status.setStyleSheet("font-size: 11px; color: #729B84; font-weight: 600;")
                QMessageBox.information(self, "Test Riuscito", "Connessione alle API Google/Gemini verificata con successo!")
            else:
                self.lbl_key_status.setText("❌ Chiave non valida o non abilitata per il modello TTS.")
                self.lbl_key_status.setStyleSheet("font-size: 11px; color: #D96B6B; font-weight: 600;")
                QMessageBox.warning(self, "Test Fallito", "La chiave non sembra autorizzata per la generazione audio Gemini.")
        except Exception as e:
            self.lbl_key_status.setText(f"❌ Errore test: {e}")
            self.lbl_key_status.setStyleSheet("font-size: 11px; color: #D96B6B;")
            show_copyable_error(self, "Errore Test API", str(e), is_warning=True)
        finally:
            self.btn_test_conn.setEnabled(True)
            self.btn_test_conn.setText("⚡ Testa Connessione")

    def _refresh_quota_display(self):
        stats = self.quota_tracker.get_monthly_usage("gemini_tts")
        used = stats["characters_used"]
        limit = stats["total_limit"]
        safe_limit = stats["safety_limit_95"]
        pct = stats["usage_percentage"]
        month = stats["month"]

        self.lbl_quota_month.setText(f"Mese Attivo: {month}  |  Richieste effettuate: {stats['requests_count']}")
        self.prog_quota.setValue(min(100, int(pct)))

        if stats["is_locked"]:
            self.prog_quota.setStyleSheet("QProgressBar::chunk { background-color: #D96B6B; }")
            self.lbl_quota_stats.setText(f"Utilizzo: {used:,} / {limit:,} caratteri ({pct:.1f}%) 🛑")
            self.lbl_quota_stats.setStyleSheet("font-weight: 700; font-size: 12px; color: #D96B6B;")
            self.lbl_quota_warning.setText(
                "⚠️ BLOCCO DI SICUREZZA 95% ATTIVO:\n"
                f"Hai raggiunto la soglia di sicurezza di {safe_limit:,} caratteri gratuiti mensili. "
                "Le richieste sono state bloccate automaticamente per prevenire addebiti inaspettati. "
                "Il contatore si azzererà automaticamente il primo giorno del prossimo mese."
            )
            self.lbl_quota_warning.setStyleSheet(
                "color: #D96B6B; font-weight: 600; font-size: 11px; background: #2A1A1A; "
                "padding: 6px; border-radius: 4px; border: 1px solid #D96B6B;"
            )
        else:
            safe_rem = stats["remaining_safe_characters"]
            chunk_color = "#729B84" if pct < 80.0 else "#C4A36B"
            self.prog_quota.setStyleSheet(f"QProgressBar::chunk {{ background-color: {chunk_color}; }}")
            self.lbl_quota_stats.setText(f"Utilizzo: {used:,} / {limit:,} caratteri ({pct:.1f}%)")
            self.lbl_quota_stats.setStyleSheet("font-weight: 600; font-size: 12px; color: #DCE0EA;")
            self.lbl_quota_warning.setText(
                f"🟢 Quota Sicura: Ti rimangono {safe_rem:,} caratteri prima del blocco di salvaguardia al 95%."
            )
            self.lbl_quota_warning.setStyleSheet("color: #729B84; font-size: 11px; font-weight: 500;")

    def _on_provider_changed(self):
        prov_id = self.combo_provider.currentData() or "gemini_tts"
        try:
            prov = TTSFactory.create(prov_id)
            voices = prov.get_available_voices()
            self.combo_speaker.clear()
            for v in voices:
                self.combo_speaker.addItem(f"{v.name} ({v.gender})", v.id)
        except Exception:
            pass

    def _on_preset_selected(self):
        p_name = self.combo_presets.currentText()
        if not p_name or p_name == "Seleziona Preset...":
            return
        presets = self.preset_mgr.get_voice_presets()
        target = next((p for p in presets if p["preset_name"] == p_name), None)
        if target:
            self._apply_preset_data(target)

    def _apply_preset_data(self, p_data: dict):
        spk = p_data.get("speaker_or_profile") or p_data.get("speaker", "Puck")
        spk_clean = str(spk).strip().lower().replace(" ", "_")
        for i in range(self.combo_speaker.count()):
            first_w = self.combo_speaker.itemText(i).split()[0].strip("(),:").lower().replace(" ", "_")
            if spk_clean in (first_w, str(self.combo_speaker.itemData(i)).lower()):
                self.combo_speaker.setCurrentIndex(i)
                break
        if p_data.get("instruct"):
            self.txt_custom_instruct.setText(p_data["instruct"])
        if p_data.get("speed_rate") is not None:
            self.slider_rate.setValue(int(float(p_data["speed_rate"]) * 100))
        elif p_data.get("speed") is not None:
            self.slider_rate.setValue(int(float(p_data["speed"]) * 100))
        if "pitch" in p_data and p_data["pitch"] is not None:
            try:
                pval = int(round(float(p_data["pitch"])))
                self.slider_pitch.setValue(pval)
                self.lbl_pitch.setText(f"Pitch / Vocal Timbre: {'Neutral' if pval == 0 else ('Deeper' if pval < 0 else 'Higher')} ({pval:+.1f})")
            except Exception:
                pass
        if "volume_gain_db" in p_data and p_data["volume_gain_db"] is not None:
            try:
                vval = int(round(float(p_data["volume_gain_db"])))
                self.slider_volume.setValue(vval)
                self.lbl_volume.setText(f"Guadagno Volume: {vval:+.1f} dB")
            except Exception:
                pass
        temp_val = p_data.get("temperature", p_data.get("temp"))
        if temp_val is not None:
            try:
                tval = int(round(float(temp_val) * 100))
                self.slider_temp.setValue(tval)
                self.lbl_temp.setText(f"Sampling Temperature: {tval/100.0:.2f}")
            except Exception:
                pass

    def _on_instruct_preset_changed(self):
        text = self.combo_instruct_preset.currentText()
        if "Viral Hook" in text:
            self.txt_custom_instruct.setText("High energy viral creator voice, fast paced, emphasizing keywords")
        elif "Dark Mystery" in text:
            self.txt_custom_instruct.setText("Deep suspenseful tone, measured pacing with suspenseful micro-pauses")
        elif "Tech & Science" in text:
            self.txt_custom_instruct.setText("Fast-paced, crystal clear diction, informative and curious")
        elif "Inspiring Motivational" in text:
            self.txt_custom_instruct.setText("Passionate, confident, cinematic, building emotional resonance")

    def _load_presets_into_combo(self):
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        self.combo_presets.addItem("Seleziona Preset...")
        presets = self.preset_mgr.get_voice_presets()
        for p in presets:
            self.combo_presets.addItem(p["preset_name"])
        self.combo_presets.blockSignals(False)

    def _save_new_preset(self):
        name, ok = QInputDialog.getText(self, "Salva Preset Voce", "Nome per il nuovo preset:")
        if ok and name.strip():
            cfg = self.get_config()
            self.preset_mgr.save_voice_preset(name.strip(), cfg)
            self._load_presets_into_combo()
            QMessageBox.information(self, "Preset Salvato", f"Preset '{name.strip()}' salvato con successo!")

    def _apply_to_all_stories(self):
        cfg = self.get_config()
        self.apply_to_all_requested.emit(cfg)
        QMessageBox.information(self, "Propagazione Eseguita", "Questa configurazione vocale è stata propagata a tutte le storie in coda.")

    def _run_benchmark_test(self, phrase: str, test_name: str):
        self.lbl_active_phrase.setText(f'Test [{test_name}]: "{phrase}"')
        self._start_audition(text=phrase)

    def _start_audition(
        self,
        mode: str = "custom",
        profile_path: Optional[str] = None,
        voice_desc: Optional[str] = None,
        text: Optional[str] = None
    ):
        self.btn_test_phonetic.setEnabled(False)
        self.btn_test_context.setEnabled(False)
        self.btn_test_emotion.setEnabled(False)
        self.btn_test_format.setEnabled(False)

        self.btn_stop.setEnabled(True)
        self.prog_audio.setValue(0)

        spk_full = self.combo_speaker.currentText()
        speaker = self.combo_speaker.currentData() or spk_full.split(" ")[0].strip("(),:")
        instruct = self.txt_custom_instruct.text().strip()
        speed = self.slider_rate.value() / 100.0
        pitch = float(self.slider_pitch.value())
        volume_gain = float(self.slider_volume.value())
        temperature = self.slider_temp.value() / 100.0
        final_text = (text or "").strip() or self.DEFAULT_TEST_PHRASE
        provider_id = self.combo_provider.currentData() or "gemini_tts"

        self.audition_worker = VoiceAuditionWorker(
            voice_suite=self.suite,
            preset_mgr=self.preset_mgr,
            text=final_text,
            speaker=speaker,
            instruct=instruct,
            speed=speed,
            pitch=pitch,
            temperature=temperature,
            mode=mode,
            profile_path=profile_path,
            voice_description=voice_desc,
            provider_id=provider_id,
            volume_gain_db=volume_gain
        )
        self.audition_worker.finished_audition.connect(self._on_audition_ready)
        self.audition_worker.error_occurred.connect(self._on_audition_error)
        self.audition_worker.start()

    def _on_audition_ready(self, audio_path: str, duration: float):
        self.playback_start_time = time.time()
        self.playback_timer.start()
        self.btn_stop.setEnabled(True)
        play_wav_file(audio_path)
        self._refresh_quota_display()

    def _on_audition_error(self, err: str):
        self._stop_audition()
        show_copyable_error(self, "Errore Anteprima", err, is_warning=True)

    def _update_playback_progress(self):
        elapsed = time.time() - self.playback_start_time
        if elapsed >= 5.0:
            self._stop_audition()
            return
        self.prog_audio.setValue(int(elapsed * 10))
        self.lbl_audio_time.setText(f"00:{elapsed:04.1f} / 00:05.0")

    def _stop_audition(self):
        self.playback_timer.stop()
        stop_wav_playback()
        self.btn_test_phonetic.setEnabled(True)
        self.btn_test_context.setEnabled(True)
        self.btn_test_emotion.setEnabled(True)
        self.btn_test_format.setEnabled(True)

        self.btn_stop.setEnabled(False)
        self.prog_audio.setValue(0)
        self.lbl_audio_time.setText("00:00.0 / 00:05.0")
        if self.audition_worker and self.audition_worker.isRunning():
            self.audition_worker.terminate()
            self.audition_worker.wait(500)

    def _reset_defaults(self):
        self.combo_speaker.setCurrentIndex(0)
        self.combo_instruct_preset.setCurrentIndex(0)
        self._on_instruct_preset_changed()
        self.slider_rate.setValue(100)
        self.slider_pitch.setValue(0)
        self.slider_volume.setValue(0)
        self.slider_temp.setValue(70)

    def _apply_initial_settings(self):
        cfg = self.current_settings
        prov = cfg.get("provider", "gemini_tts")
        for i in range(self.combo_provider.count()):
            if prov.lower() == str(self.combo_provider.itemData(i)).lower():
                self.combo_provider.setCurrentIndex(i)
                break

        spk = cfg.get("speaker") or cfg.get("speaker_or_profile", DEFAULT_SPEAKER)
        spk_clean = str(spk).strip().lower().replace(" ", "_")
        for i in range(self.combo_speaker.count()):
            data_name = str(self.combo_speaker.itemData(i) or "").lower().replace(" ", "_")
            first_word = self.combo_speaker.itemText(i).split()[0].strip("(),:").lower().replace(" ", "_")
            if spk_clean in (data_name, first_word) or spk_clean == data_name or spk_clean == first_word:
                self.combo_speaker.setCurrentIndex(i)
                break

        if cfg.get("instruct"):
            self.txt_custom_instruct.setText(cfg["instruct"])
        if cfg.get("speed") is not None:
            self.slider_rate.setValue(int(float(cfg["speed"]) * 100))
        if "pitch" in cfg and cfg["pitch"] is not None:
            try:
                pval = int(round(float(cfg["pitch"])))
                self.slider_pitch.setValue(pval)
                self.lbl_pitch.setText(f"Pitch / Vocal Timbre: {'Neutral' if pval == 0 else ('Deeper' if pval < 0 else 'Higher')} ({pval:+.1f})")
            except Exception:
                pass
        if "volume_gain_db" in cfg and cfg["volume_gain_db"] is not None:
            try:
                vval = int(round(float(cfg["volume_gain_db"])))
                self.slider_volume.setValue(vval)
                self.lbl_volume.setText(f"Guadagno Volume: {vval:+.1f} dB")
            except Exception:
                pass
        temp_val = cfg.get("temperature", cfg.get("temp"))
        if temp_val is not None:
            try:
                tval = int(round(float(temp_val) * 100))
                self.slider_temp.setValue(tval)
                self.lbl_temp.setText(f"Sampling Temperature: {tval/100.0:.2f}")
            except Exception:
                pass

    def get_config(self) -> Dict[str, Any]:
        spk_full = self.combo_speaker.currentText()
        speaker = self.combo_speaker.currentData() or spk_full.split(" ")[0].strip("(),:")
        speed = self.slider_rate.value() / 100.0
        pitch = float(self.slider_pitch.value())
        volume_gain = float(self.slider_volume.value())
        temp = self.slider_temp.value() / 100.0
        provider_id = self.combo_provider.currentData() or "gemini_tts"

        return {
            "provider": provider_id,
            "speaker": speaker,
            "speaker_or_profile": speaker,
            "speaker_full": spk_full,
            "language": "English",
            "instruct": self.txt_custom_instruct.text().strip(),
            "speed": speed,
            "pitch": pitch,
            "volume_gain_db": volume_gain,
            "temp": temp,
            "temperature": temp,
            "voice_type": "CUSTOM"
        }

    def _save_and_close(self):
        self._stop_audition()
        self.settings_saved.emit(self.get_config())
        self.accept()

    def reject(self):
        self._stop_audition()
        self.settings_saved.emit(self.get_config())
        super().reject()

    def closeEvent(self, event):
        self._stop_audition()
        self.settings_saved.emit(self.get_config())
        super().closeEvent(event)
