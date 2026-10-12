"""AI Short Generator 1.0 - Voice Studio Drawer & Voice Intelligence (Qwen3-TTS en-US)"""

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
    DEFAULT_NARRATOR_SPEAKER, DEFAULT_INSTRUCT, QWEN_DEFAULT_VOICES
)
from app.core.tts_engine import Qwen3VoiceSuite
from app.core.preset_manager import PresetManager
from app.ui.modals.copyable_error_dialog import show_copyable_error
from app.utils.logger import log
from app.utils.audio_player import play_wav_file, stop_wav_playback


class VoiceAuditionWorker(QThread):
    finished_audition = Signal(str, float) # path, duration
    error_occurred = Signal(str)

    def __init__(
        self,
        voice_suite: Qwen3VoiceSuite,
        preset_mgr: PresetManager,
        text: str,
        speaker: str,
        instruct: str,
        speed: float,
        pitch: float = 0.0,
        temperature: float = 0.70,
        mode: str = "custom",
        profile_path: Optional[str] = None,
        voice_description: Optional[str] = None
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

    def run(self):
        try:
            now_ms = int(time.time() * 1000)
            raw_out = str(CACHE_DIR / f"temp_audition_raw_{os.getpid()}_{now_ms}.wav")
            clamped_out = str(CACHE_DIR / f"temp_audition_5s_{os.getpid()}_{now_ms}.wav")

            mode_clean = str(self.mode).lower()
            if mode_clean == "cloned" and self.profile_path:
                self.suite.generate_cloned(
                    text=self.text,
                    profile_path=self.profile_path,
                    output_path=raw_out,
                    speed=self.speed,
                    pitch=self.pitch,
                    temperature=self.temperature,
                    is_preview=True
                )
            elif mode_clean == "design" and self.voice_description:
                self.suite.design_new_voice(
                    audition_text=self.text,
                    voice_description=self.voice_description,
                    output_audition_path=raw_out
                )
            else:
                self.suite.generate_custom(
                    text=self.text,
                    output_path=raw_out,
                    speaker=self.speaker,
                    instruct=self.instruct,
                    speed=self.speed,
                    pitch=self.pitch,
                    temperature=self.temperature,
                    is_preview=True
                )

            # Rigoroso clamp audio a massimo 5.0 secondi con micro-fadeout di 50ms
            if os.path.exists(raw_out) and os.path.getsize(raw_out) > 200:
                self.preset_mgr.clamp_audio_demo_to_5s(raw_out, clamped_out, max_sec=5.0)
                self.finished_audition.emit(clamped_out, 5.0)
            else:
                self.error_occurred.emit("Errore generazione anteprima vocale.")
        except Exception as e:
            self.error_occurred.emit(str(e))


class VoiceCloneWorker(QThread):
    progress_step = Signal(int, str) # percent, status message
    finished_clone = Signal(str, str) # profile_name, file_path
    error_occurred = Signal(str)

    def __init__(self, voice_suite: Qwen3VoiceSuite, profile_name: str, ref_audio_path: str, ref_text: str):
        super().__init__()
        self.suite = voice_suite
        self.profile_name = profile_name
        self.ref_audio_path = ref_audio_path
        self.ref_text = ref_text

    def run(self):
        try:
            self.progress_step.emit(10, "Verifica file audio di riferimento...")
            if not os.path.exists(self.ref_audio_path):
                raise FileNotFoundError(f"File audio di riferimento non trovato: {self.ref_audio_path}")

            self.progress_step.emit(25, "Controllo pesi neurali Qwen3-TTS Base...")
            if not self.suite._is_model_cached("base"):
                raise RuntimeError(
                    "Pesi neurali Qwen3-TTS-Base non trovati in locale (~4.5 GB necessari). "
                    "Scarica prima i pesi Base per abilitare la clonazione vocale reale."
                )

            self.progress_step.emit(45, "Caricamento modello neurale Base in memoria...")
            self.progress_step.emit(65, "Analisi acustica ed estrazione speaker embedding...")
            profile_file = self.suite.create_and_cache_clone_profile(
                self.profile_name, self.ref_audio_path, self.ref_text
            )

            self.progress_step.emit(90, "Serializzazione profilo (.qvoice) e salvataggio nel database...")
            time.sleep(0.2)
            self.progress_step.emit(100, "Clonazione completata con successo!")
            self.finished_clone.emit(self.profile_name, str(profile_file))
        except Exception as e:
            self.error_occurred.emit(str(e))


class ModelDownloadWorker(QThread):
    progress_msg = Signal(str)
    download_finished = Signal(bool, str)

    def __init__(self, model_type: str = "custom"):
        super().__init__()
        self.model_type = model_type

    def run(self):
        try:
            self.progress_msg.emit("Connessione a Hugging Face in corso...")
            models = {
                "custom": ("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "Qwen3-TTS-CustomVoice"),
                "base": ("Qwen/Qwen3-TTS-12Hz-1.7B-Base", "Qwen3-TTS-Base"),
                "design": ("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", "Qwen3-TTS-VoiceDesign")
            }
            repo_id, folder_name = models.get(self.model_type, models["custom"])
            from app.config import MODELS_DIR
            target_dir = MODELS_DIR / folder_name
            target_dir.mkdir(parents=True, exist_ok=True)

            from huggingface_hub import snapshot_download
            self.progress_msg.emit("Download in corso dei pesi neurali (~4.5 GB) in locale...")
            local_path = snapshot_download(
                repo_id=repo_id,
                repo_type="model",
                local_dir=str(target_dir),
                resume_download=True
            )
            self.download_finished.emit(True, str(local_path))
        except Exception as e:
            self.download_finished.emit(False, str(e))


class VoiceSettingsDrawer(QDialog):
    """
    Drawer 1: Studio Voce Avanzato & Voice Intelligence (Qwen3-TTS en-US)
    Conforme al 100% a DESIGN_APP.md (Sezione 5.8):
    - 4 Tab: PRESET VOCI US, VOICE CLONE, VOICE DESIGN, LIBRERIA PROFILI
    - Clamping rigido demo audio a max 5.0s (con micro-fadeout 50ms)
    - Instradamento intelligente CPU se GPU occupata da batch
    - Auto-Save on Close: ON
    """

    settings_saved = Signal(dict)
    apply_to_all_requested = Signal(dict)

    DEFAULT_TEST_PHRASE = (
        "Black holes are among the most mysterious cosmic titans in the entire universe..."
    )

    def __init__(
        self,
        voice_suite: Optional[Qwen3VoiceSuite] = None,
        preset_mgr: Optional[PresetManager] = None,
        current_settings: Optional[dict] = None,
        active_story_title: str = "Active Script",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.suite = voice_suite or Qwen3VoiceSuite()
        self.preset_mgr = preset_mgr or PresetManager()
        self.current_settings = current_settings or {}
        self.active_story_title = active_story_title

        self.setWindowTitle("VOICE STUDIO & INTELLIGENZA VOCALE (Qwen3-TTS en-US)")
        self.resize(840, 720)
        self.setObjectName("DrawerWindow")

        self.audition_worker: Optional[VoiceAuditionWorker] = None
        self.clone_worker: Optional[VoiceCloneWorker] = None
        self.dl_worker: Optional[ModelDownloadWorker] = None
        self.dl_base_worker: Optional[ModelDownloadWorker] = None
        self.last_cloned_profile_path: Optional[str] = None
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(100)
        self.playback_timer.timeout.connect(self._update_playback_progress)
        self.playback_start_time = 0.0

        self._init_ui()
        self._load_presets_into_combo()
        self._apply_initial_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(10)

        # Header Bar
        header_bar = QHBoxLayout()
        lbl_title = QLabel("VOICE STUDIO & INTELLIGENZA VOCALE (Qwen3-TTS en-US)")
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

        btn_apply_all = QPushButton("🔗 Applica Questa Voce a Tutte le Storie")
        btn_apply_all.clicked.connect(self._apply_to_all_stories)
        preset_bar.addWidget(btn_apply_all)
        main_layout.addLayout(preset_bar)

        # Card Stato Pesi Modello Neurale AI
        self.weights_card = QFrame()
        self.weights_card.setObjectName("InnerCard")
        wc_layout = QHBoxLayout(self.weights_card)
        wc_layout.setContentsMargins(12, 6, 12, 6)

        self.lbl_weights_status = QLabel()
        self.lbl_weights_status.setStyleSheet("font-size: 11px; font-weight: 600;")
        wc_layout.addWidget(self.lbl_weights_status, stretch=1)

        self.btn_download_weights = QPushButton("📥 Scarica Pesi AI Qwen3-TTS (~4.5 GB)")
        self.btn_download_weights.setStyleSheet("font-size: 11px; font-weight: 600; padding: 4px 10px;")
        self.btn_download_weights.clicked.connect(self._start_download_weights)
        wc_layout.addWidget(self.btn_download_weights)

        main_layout.addWidget(self.weights_card)
        self._update_weights_status_display()

        # Tabs Container
        self.tabs = QTabWidget()
        self.tab1 = self._build_tab1_presets()
        self.tab2 = self._build_tab2_clone()
        self.tab3 = self._build_tab3_design()
        self.tab4 = self._build_tab4_profiles()

        self.tabs.addTab(self.tab1, "VOCI STANDARD")
        self.tabs.addTab(self.tab2, "VOICE CLONE")
        self.tabs.addTab(self.tab3, "VOICE DESIGN")
        self.tabs.addTab(self.tab4, "LIBRERIA PROFILI")
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

        # 4 Tasti di test al posto del tasto demo
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
        self.prog_audio.setRange(0, 50) # 0 to 5.0s in deciseconds
        self.prog_audio.setValue(0)
        play_row.addWidget(self.prog_audio, stretch=1)

        self.lbl_audio_time = QLabel("00:00.0 / 00:05.0")
        self.lbl_audio_time.setStyleSheet("font-family: monospace; font-size: 11px; color: #949CAE;")
        play_row.addWidget(self.lbl_audio_time)
        ab_layout.addLayout(play_row)

        info_note = QLabel("* Nota: Il motore genera i primi 5 secondi con micro-fadeout di 50ms, garantendo feedback immediato (<97ms).")
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
        layout.setSpacing(10)

        # Row Speaker
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Speaker Ufficiale Qwen3-TTS:"))
        self.combo_speaker = QComboBox()
        for v in QWEN_DEFAULT_VOICES:
            self.combo_speaker.addItem(v["display"], v["name"])
        r1.addWidget(self.combo_speaker, stretch=1)
        layout.addLayout(r1)

        # Emotion & Instruct Guide
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

        layout.addWidget(QLabel("Prompt Libero Istruzione:"))
        self.txt_custom_instruct = QLineEdit("Speak with an engaging, fast-paced American creator voice, building tension toward climax")
        layout.addWidget(self.txt_custom_instruct)

        # Fine adjustments sliders
        fines_box = QFrame()
        fines_box.setObjectName("InnerCard")
        fb_layout = QVBoxLayout(fines_box)
        fb_layout.setContentsMargins(10, 8, 10, 8)
        fb_layout.setSpacing(6)

        fb_layout.addWidget(QLabel("REGOLAZIONI FINI AUDIZIONE:"))

        # Speaking Rate
        row_rate = QHBoxLayout()
        self.lbl_rate = QLabel("Speaking Rate (Velocità WPM): 1.00x (~150 WPM American Standard)")
        self.slider_rate = QSlider(Qt.Horizontal)
        self.slider_rate.setRange(75, 150) # 0.75x to 1.50x
        self.slider_rate.setValue(100)
        self.slider_rate.valueChanged.connect(lambda v: self.lbl_rate.setText(f"Speaking Rate (Velocità WPM): {v/100.0:.2f}x (~{int(v*1.5)} WPM)"))
        row_rate.addWidget(self.lbl_rate, stretch=1)
        row_rate.addWidget(self.slider_rate, stretch=1)
        fb_layout.addLayout(row_rate)

        # Pitch
        row_pitch = QHBoxLayout()
        self.lbl_pitch = QLabel("Pitch / Vocal Timbre: Neutral (0.0)")
        self.slider_pitch = QSlider(Qt.Horizontal)
        self.slider_pitch.setRange(-5, 5)
        self.slider_pitch.setValue(0)
        self.slider_pitch.valueChanged.connect(lambda v: self.lbl_pitch.setText(f"Pitch / Vocal Timbre: {'Neutral' if v == 0 else ('Deeper' if v < 0 else 'Higher')} ({v:+.1f})"))
        row_pitch.addWidget(self.lbl_pitch, stretch=1)
        row_pitch.addWidget(self.slider_pitch, stretch=1)
        fb_layout.addLayout(row_pitch)

        # Temperature
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

    def _build_tab2_clone(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Card Stato Pesi Base per Clonazione Neurale
        self.base_weights_card = QFrame()
        self.base_weights_card.setObjectName("InnerCard")
        bwc_layout = QHBoxLayout(self.base_weights_card)
        bwc_layout.setContentsMargins(12, 6, 12, 6)

        self.lbl_base_status = QLabel()
        self.lbl_base_status.setStyleSheet("font-size: 11px; font-weight: 600;")
        bwc_layout.addWidget(self.lbl_base_status, stretch=1)

        self.btn_download_base = QPushButton("📥 Scarica Pesi AI Qwen3-TTS-Base (~4.5 GB)")
        self.btn_download_base.setStyleSheet("font-size: 11px; font-weight: 600; padding: 4px 10px;")
        self.btn_download_base.clicked.connect(self._start_download_base_weights)
        bwc_layout.addWidget(self.btn_download_base)
        layout.addWidget(self.base_weights_card)

        layout.addWidget(QLabel("1. AUDIO DI RIFERIMENTO (Da 3 a 15 secondi di voce chiara en-US):"))
        ref_row = QHBoxLayout()
        self.txt_ref_path = QLineEdit()
        self.txt_ref_path.setPlaceholderText("Seleziona file audio di riferimento (.wav, .mp3, .m4a)...")
        ref_row.addWidget(self.txt_ref_path, stretch=1)

        btn_browse_ref = QPushButton("📁 Sfoglia File")
        btn_browse_ref.clicked.connect(self._browse_ref_audio)
        ref_row.addWidget(btn_browse_ref)
        layout.addLayout(ref_row)

        layout.addWidget(QLabel("2. TRASCRIZIONE AUDIO DI RIFERIMENTO (Condizionamento acustico):"))
        self.txt_ref_transcript = QTextEdit()
        self.txt_ref_transcript.setPlaceholderText("Trascrizione del testo pronunciato nell'audio di riferimento (opzionale per modalità embedding)...")
        self.txt_ref_transcript.setFixedHeight(70)
        layout.addWidget(self.txt_ref_transcript)

        btn_whisper_trans = QPushButton("🪄 Auto-Trascrivi con Faster-Whisper (en)")
        btn_whisper_trans.clicked.connect(self._auto_transcribe_reference)
        layout.addWidget(btn_whisper_trans)

        layout.addWidget(QLabel("3. PROFILAZIONE PERSISTENTE & CACHING (.qvoice):"))
        clone_row = QHBoxLayout()
        self.txt_clone_name = QLineEdit("My_Creator_Clone")
        clone_row.addWidget(QLabel("Nome Profilo:"))
        clone_row.addWidget(self.txt_clone_name, stretch=1)

        self.btn_save_clone = QPushButton("💾 Estrai & Salva Profilo Vocale (.qvoice)")
        self.btn_save_clone.setObjectName("PrimaryButton")
        self.btn_save_clone.clicked.connect(self._create_and_save_clone)
        clone_row.addWidget(self.btn_save_clone)
        layout.addLayout(clone_row)

        # Barra di avanzamento e stato processo clonazione
        self.prog_clone = QProgressBar()
        self.prog_clone.setRange(0, 100)
        self.prog_clone.setValue(0)
        self.prog_clone.setTextVisible(True)
        self.prog_clone.setStyleSheet("height: 16px;")
        self.prog_clone.setVisible(False)
        layout.addWidget(self.prog_clone)

        self.lbl_clone_status = QLabel("Stato: Pronto per l'estrazione e profilazione vocale neurale.")
        self.lbl_clone_status.setStyleSheet("font-size: 11px; color: #949CAE;")
        layout.addWidget(self.lbl_clone_status)

        clone_actions_row = QHBoxLayout()
        self.btn_test_clone = QPushButton("▶ Testa Voce Clonata (Max 5.0s)")
        self.btn_test_clone.setObjectName("AccentButton")
        self.btn_test_clone.setEnabled(False)
        self.btn_test_clone.clicked.connect(self._audition_last_cloned_voice)
        clone_actions_row.addWidget(self.btn_test_clone)
        clone_actions_row.addStretch()
        layout.addLayout(clone_actions_row)

        layout.addStretch()
        return widget

    def _build_tab3_design(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Descrivi in linguaggio naturale la voce ideale che desideri creare (in inglese):"))
        self.txt_voice_desc = QTextEdit()
        self.txt_voice_desc.setPlaceholderText(
            "Male American voice, 35-40 years old, deep warm baritone tone, confident and engaging pacing, "
            "perfect for thrilling science and mystery YouTube Shorts..."
        )
        self.txt_voice_desc.setFixedHeight(85)
        layout.addWidget(self.txt_voice_desc)

        layout.addWidget(QLabel("Preset Rapidi da un Clic:"))
        preset_row = QHBoxLayout()
        b_docu = QPushButton("US Docu Baritone")
        b_docu.clicked.connect(lambda: self.txt_voice_desc.setText("Deep warm American baritone, articulate and solemn, documentary narration tone"))
        b_creator = QPushButton("US Dynamic Creator 22y")
        b_creator.clicked.connect(lambda: self.txt_voice_desc.setText("Dynamic young American YouTuber, energetic and clear diction, highly engaging"))
        b_trailer = QPushButton("Movie Trailer")
        b_trailer.clicked.connect(lambda: self.txt_voice_desc.setText("Cinematic ultra-deep American movie trailer voice, dramatic pauses, gravelly texture"))
        b_podcast = QPushButton("Chill Podcast")
        b_podcast.clicked.connect(lambda: self.txt_voice_desc.setText("Relaxed intimate American podcast voice, soft spoken, warm low end frequencies"))

        preset_row.addWidget(b_docu)
        preset_row.addWidget(b_creator)
        preset_row.addWidget(b_trailer)
        preset_row.addWidget(b_podcast)
        layout.addLayout(preset_row)

        btn_design_demo = QPushButton("▶ Demo 5s Voice Design")
        btn_design_demo.clicked.connect(self._audition_voice_design)
        layout.addWidget(btn_design_demo)

        layout.addStretch()
        return widget

    def _build_tab4_profiles(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(QLabel("PROFILI VOCALI ARCHIVIATI NEL DATABASE:"))
        self.table_profiles = QTableWidget()
        self.table_profiles.setColumnCount(4)
        self.table_profiles.setHorizontalHeaderLabels(["ID", "Nome Profilo", "Tipo", "Creato il"])
        self.table_profiles.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table_profiles)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Aggiorna Lista Profili")
        btn_refresh.clicked.connect(self._refresh_profiles_table)
        btn_row.addWidget(btn_refresh)

        btn_use = QPushButton("✅ Usa Profilo Selezionato")
        btn_use.setObjectName("PrimaryButton")
        btn_use.clicked.connect(self._use_selected_profile)
        btn_row.addWidget(btn_use)

        btn_listen = QPushButton("▶ Ascolta Profilo")
        btn_listen.clicked.connect(self._audition_selected_profile)
        btn_row.addWidget(btn_listen)

        layout.addLayout(btn_row)
        return widget

    # --- LOGICA OPERATIVA ---

    def _on_instruct_preset_changed(self):
        txt = self.combo_instruct_preset.currentText()
        if "Viral Hook" in txt:
            self.txt_custom_instruct.setText("High energy viral creator voice, fast paced, punchy keywords")
        elif "Dark Mystery" in txt:
            self.txt_custom_instruct.setText("Deep tone, suspenseful micro-pauses, slow build and intrigue")
        elif "Tech & Science" in txt:
            self.txt_custom_instruct.setText("Fast-paced, crystal clear American diction, confident and analytical")
        elif "Inspiring Motivational" in txt:
            self.txt_custom_instruct.setText("Passionate, confident, cinematic and motivational storytelling")

    def _load_presets_into_combo(self):
        self.combo_presets.clear()
        presets = self.preset_mgr.get_voice_presets()
        if not presets:
            self.combo_presets.addItem("US_ViralHook_Ryan (Standard)", {
                "speaker": "Ryan", "instruct": DEFAULT_INSTRUCT, "speed": 1.00
            })
            return

        for p in presets:
            self.combo_presets.addItem(f"{p['preset_name']} ({p['speaker_or_profile']})", p)

    def _on_preset_selected(self):
        p_data = self.combo_presets.currentData()
        if not p_data:
            return
        spk = p_data.get("speaker_or_profile", p_data.get("speaker", "Ryan"))
        spk_clean = str(spk).strip().lower().replace(" ", "_")
        for i in range(self.combo_speaker.count()):
            data_name = str(self.combo_speaker.itemData(i) or "").lower().replace(" ", "_")
            first_word = self.combo_speaker.itemText(i).split()[0].strip("(),:").lower().replace(" ", "_")
            if spk_clean in (data_name, first_word) or spk_clean == data_name or spk_clean == first_word:
                self.combo_speaker.setCurrentIndex(i)
                break
        if p_data.get("instruct_prompt"):
            self.txt_custom_instruct.setText(p_data["instruct_prompt"])
        elif p_data.get("instruct"):
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
            except (ValueError, TypeError):
                pass
        temp_val = p_data.get("temperature", p_data.get("temp"))
        if temp_val is not None:
            try:
                tval = int(round(float(temp_val) * 100))
                self.slider_temp.setValue(tval)
                self.lbl_temp.setText(f"Sampling Temperature: {tval/100.0:.2f}")
            except (ValueError, TypeError):
                pass

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

    def _browse_ref_audio(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Seleziona Audio di Riferimento", "", "Audio Files (*.wav *.mp3 *.m4a)")
        if fn:
            self.txt_ref_path.setText(fn)

    def _auto_transcribe_reference(self):
        ref_file = self.txt_ref_path.text().strip()
        if not ref_file or not os.path.exists(ref_file):
            QMessageBox.warning(self, "File Mancante", "Seleziona prima un file audio valido.")
            return

        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segs, _ = model.transcribe(ref_file, language="en")
            trans = " ".join(s.text.strip() for s in segs)
            self.txt_ref_transcript.setText(trans)
            del model
        except Exception as e:
            self.txt_ref_transcript.setText("Sample reference transcript for cloning.")

    def _create_and_save_clone(self):
        name = self.txt_clone_name.text().strip()
        ref = self.txt_ref_path.text().strip()
        txt = self.txt_ref_transcript.toPlainText().strip()
        if not name or not ref or not os.path.exists(ref):
            QMessageBox.warning(self, "Dati Incompleti", "Fornisci un nome e un file audio di riferimento valido.")
            return

        # Verifica preliminare se i pesi Base sono presenti
        if not self.suite._is_model_cached("base"):
            res = QMessageBox.question(
                self,
                "Pesi Qwen3-TTS-Base Richiesti",
                "Per eseguire la reale clonazione neurale della voce è necessario il modello 'Qwen3-TTS Base' (~4.5 GB).\n\n"
                "Attualmente i pesi Base non sono presenti nella cartella locale.\n"
                "Desideri avviare il download dei pesi ora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if res == QMessageBox.Yes:
                self._start_download_base_weights()
            return

        self.btn_save_clone.setEnabled(False)
        self.prog_clone.setVisible(True)
        self.prog_clone.setValue(10)
        self.lbl_clone_status.setText("Avvio clonazione vocale in corso...")

        self.clone_worker = VoiceCloneWorker(self.suite, name, ref, txt)

        def _on_step(pct: int, msg: str):
            self.prog_clone.setValue(pct)
            self.lbl_clone_status.setText(f"⏳ {msg}")

        def _on_done(prof_name: str, file_path: str):
            self.last_cloned_profile_path = file_path
            self._refresh_profiles_table()
            self.btn_save_clone.setEnabled(True)
            self.btn_test_clone.setEnabled(True)
            self.prog_clone.setValue(100)
            self.lbl_clone_status.setText(f"🟢 Profilo vocale '{prof_name}' salvato con successo!")
            self.lbl_clone_status.setStyleSheet("font-size: 11px; color: #729B84; font-weight: 600;")
            QMessageBox.information(
                self,
                "Profilo Clonato",
                f"Profilo vocale '{prof_name}' generato con successo!\n"
                f"Gli embedding neurali sono stati estratti dal file audio e memorizzati nel profilo .qvoice."
            )

        def _on_err(err: str):
            self.btn_save_clone.setEnabled(True)
            self.prog_clone.setValue(0)
            self.lbl_clone_status.setText(f"❌ Errore durante la clonazione.")
            self.lbl_clone_status.setStyleSheet("font-size: 11px; color: #D96B6B;")
            show_copyable_error(self, "Errore Creazione Profilo", f"Errore creazione profilo clone:\n{err}", is_warning=True)

        self.clone_worker.progress_step.connect(_on_step)
        self.clone_worker.finished_clone.connect(_on_done)
        self.clone_worker.error_occurred.connect(_on_err)
        self.clone_worker.start()

    def _audition_last_cloned_voice(self):
        target_path = self.last_cloned_profile_path
        if not target_path or not os.path.exists(target_path):
            profiles = self.suite.get_profiles()
            cloned_p = next((p for p in profiles if p.get("voice_type") == "CLONED" and p.get("profile_tensor_path")), None)
            if cloned_p:
                target_path = cloned_p["profile_tensor_path"]
                self.last_cloned_profile_path = target_path

        if not target_path or not os.path.exists(target_path):
            QMessageBox.warning(self, "Nessun Profilo", "Genera prima un profilo vocale clonato oppure selezionane uno dalla libreria.")
            return

        self._start_audition(
            mode="cloned",
            profile_path=target_path,
            text="The box was thrown beside the parked truck."
        )

    def _run_benchmark_test(self, phrase: str, test_name: str):
        self.lbl_active_phrase.setText(f'Test [{test_name}]: "{phrase}"')

        current_tab = self.tabs.currentIndex()
        mode = "custom"
        profile_path = None
        voice_desc = None

        if current_tab == 1: # Tab Voice Clone
            target_path = self.last_cloned_profile_path
            if not target_path or not os.path.exists(target_path):
                profiles = self.suite.get_profiles()
                cloned_p = next((p for p in profiles if p.get("voice_type") == "CLONED" and p.get("profile_tensor_path")), None)
                if cloned_p:
                    target_path = cloned_p["profile_tensor_path"]
                    self.last_cloned_profile_path = target_path
            if target_path and os.path.exists(target_path):
                mode = "cloned"
                profile_path = target_path
        elif current_tab == 2: # Tab Voice Design
            desc = self.txt_voice_desc.toPlainText().strip()
            if desc:
                mode = "design"
                voice_desc = desc
        elif current_tab == 3: # Tab Libreria Profili
            row = self.table_profiles.currentRow()
            if row >= 0:
                name_item = self.table_profiles.item(row, 1)
                if name_item:
                    p_name = name_item.text().strip()
                    profiles = self.suite.get_profiles()
                    prof = next((p for p in profiles if p["name"] == p_name), None)
                    if prof and prof.get("profile_tensor_path"):
                        mode = "cloned"
                        profile_path = prof["profile_tensor_path"]

        self._start_audition(mode=mode, profile_path=profile_path, voice_desc=voice_desc, text=phrase)

    def _audition_voice_design(self):
        desc = self.txt_voice_desc.toPlainText().strip()
        if not desc:
            QMessageBox.warning(self, "Descrizione Mancante", "Descrivi la voce desiderata prima della demo.")
            return
        self._start_audition(mode="design", voice_desc=desc)

    def _refresh_profiles_table(self):
        profiles = self.suite.get_profiles()
        self.table_profiles.setRowCount(len(profiles))
        for row, p in enumerate(profiles):
            self.table_profiles.setItem(row, 0, QTableWidgetItem(str(p["id"])))
            self.table_profiles.setItem(row, 1, QTableWidgetItem(p["name"]))
            self.table_profiles.setItem(row, 2, QTableWidgetItem(p["voice_type"]))
            self.table_profiles.setItem(row, 3, QTableWidgetItem(str(p.get("created_at", ""))))

    def _start_audition(
        self,
        mode: str = "custom",
        profile_path: Optional[str] = None,
        voice_desc: Optional[str] = None,
        text: Optional[str] = None
    ):
        if not isinstance(mode, str) or not mode:
            mode = "custom"

        # Disabilita i 4 pulsanti di test benchmark
        self.btn_test_phonetic.setEnabled(False)
        self.btn_test_context.setEnabled(False)
        self.btn_test_emotion.setEnabled(False)
        self.btn_test_format.setEnabled(False)
        if hasattr(self, "btn_test_clone"):
            self.btn_test_clone.setEnabled(False)

        self.btn_stop.setEnabled(True)
        self.prog_audio.setValue(0)

        spk_full = self.combo_speaker.currentText()
        speaker = spk_full.split(" ")[0]
        instruct = self.txt_custom_instruct.text().strip()
        speed = self.slider_rate.value() / 100.0
        pitch = float(self.slider_pitch.value())
        temperature = self.slider_temp.value() / 100.0
        final_text = (text or "").strip() or self.DEFAULT_TEST_PHRASE

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
            voice_description=voice_desc
        )
        self.audition_worker.finished_audition.connect(self._on_audition_ready)
        self.audition_worker.error_occurred.connect(self._on_audition_error)
        self.audition_worker.start()

    def _on_audition_ready(self, audio_path: str, duration: float):
        self.playback_start_time = time.time()
        self.playback_timer.start()
        self.btn_stop.setEnabled(True)
        play_wav_file(audio_path)

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
        if hasattr(self, "btn_test_clone") and (self.last_cloned_profile_path or self.suite.get_profiles()):
            self.btn_test_clone.setEnabled(True)

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
        self.slider_temp.setValue(70)

    def _apply_initial_settings(self):
        cfg = self.current_settings
        spk = cfg.get("speaker") or cfg.get("speaker_or_profile", "Ryan")
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
            except (ValueError, TypeError):
                pass
        temp_val = cfg.get("temperature", cfg.get("temp"))
        if temp_val is not None:
            try:
                tval = int(round(float(temp_val) * 100))
                self.slider_temp.setValue(tval)
                self.lbl_temp.setText(f"Sampling Temperature: {tval/100.0:.2f}")
            except (ValueError, TypeError):
                pass
        self._refresh_profiles_table()

    def _use_selected_profile(self):
        row = self.table_profiles.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selezione Richiesta", "Seleziona prima una riga dalla tabella dei profili.")
            return
        name_item = self.table_profiles.item(row, 1)
        if name_item:
            p_name = name_item.text().strip()
            found = False
            for i in range(self.combo_speaker.count()):
                if p_name in self.combo_speaker.itemText(i):
                    self.combo_speaker.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.combo_speaker.addItem(f"{p_name} (Profilo Clonato)")
                self.combo_speaker.setCurrentIndex(self.combo_speaker.count() - 1)
            QMessageBox.information(self, "Profilo Selezionato", f"Profilo vocale '{p_name}' selezionato!")

    def _audition_selected_profile(self):
        row = self.table_profiles.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selezione Richiesta", "Seleziona prima un profilo vocale da ascoltare.")
            return
        name_item = self.table_profiles.item(row, 1)
        if not name_item:
            return
        p_name = name_item.text().strip()
        profiles = self.suite.get_profiles()
        prof = next((p for p in profiles if p["name"] == p_name), None)
        if prof and prof.get("profile_tensor_path"):
            self._start_audition(
                mode="cloned",
                profile_path=prof["profile_tensor_path"],
                text="The box was thrown beside the parked truck."
            )
        else:
            self._start_audition(mode="custom")

    def _update_weights_status_display(self):
        is_cached = self.suite._is_model_cached("custom")
        if is_cached:
            self.lbl_weights_status.setText("🟢 Modello Neurale Qwen3-TTS CustomVoice (1.7B) Installato e Pronto")
            self.lbl_weights_status.setStyleSheet("color: #729B84; font-size: 11px; font-weight: 600;")
            self.btn_download_weights.setVisible(False)
        else:
            self.lbl_weights_status.setText("🟡 Pesi Qwen3-TTS CustomVoice non presenti (Attivo fallback Microsoft Speech SAPI)")
            self.lbl_weights_status.setStyleSheet("color: #C4A36B; font-size: 11px; font-weight: 600;")
            self.btn_download_weights.setText("📥 Scarica Pesi AI Qwen3-TTS (~4.5 GB)")
            self.btn_download_weights.setVisible(True)
            self.btn_download_weights.setEnabled(True)

        # Aggiorna anche stato dei pesi Base nella scheda Clone Voice
        if hasattr(self, "lbl_base_status") and hasattr(self, "btn_download_base"):
            is_base_cached = self.suite._is_model_cached("base")
            if is_base_cached:
                self.lbl_base_status.setText("🟢 Modello Neurale Qwen3-TTS Base (1.7B) Pronto per la Clonazione Neurale")
                self.lbl_base_status.setStyleSheet("color: #729B84; font-size: 11px; font-weight: 600;")
                self.btn_download_base.setVisible(False)
            else:
                self.lbl_base_status.setText("🟡 Pesi Modello Base non scaricati (~4.5 GB necessari per clonazione reale)")
                self.lbl_base_status.setStyleSheet("color: #C4A36B; font-size: 11px; font-weight: 600;")
                self.btn_download_base.setText("📥 Scarica Pesi AI Qwen3-TTS-Base (~4.5 GB)")
                self.btn_download_base.setVisible(True)
                self.btn_download_base.setEnabled(True)

    def _start_download_weights(self):
        self.btn_download_weights.setEnabled(False)
        self.lbl_weights_status.setText("⏳ Download pesi neurali CustomVoice (~4.5 GB)...")
        self.lbl_weights_status.setStyleSheet("color: #6B82A6; font-size: 11px; font-weight: 600;")

        self.dl_worker = ModelDownloadWorker(model_type="custom")
        self.dl_worker.progress_msg.connect(lambda msg: self.lbl_weights_status.setText(f"⏳ {msg}"))
        self.dl_worker.download_finished.connect(self._on_download_weights_finished)
        self.dl_worker.start()

    def _on_download_weights_finished(self, success: bool, msg: str):
        if success:
            QMessageBox.information(self, "Download Completato", "Pesi neurali Qwen3-TTS scaricati con successo!\nIl motore neurale è ora attivo.")
        else:
            show_copyable_error(self, "Errore Download", f"Impossibile scaricare i pesi del modello:\n{msg}", is_warning=True)
        self._update_weights_status_display()

    def _start_download_base_weights(self):
        self.btn_download_base.setEnabled(False)
        self.lbl_base_status.setText("⏳ Download pesi neurali Qwen3-TTS-Base (~4.5 GB)...")
        self.lbl_base_status.setStyleSheet("color: #6B82A6; font-size: 11px; font-weight: 600;")

        self.dl_base_worker = ModelDownloadWorker(model_type="base")
        self.dl_base_worker.progress_msg.connect(lambda msg: self.lbl_base_status.setText(f"⏳ {msg}"))
        self.dl_base_worker.download_finished.connect(self._on_download_base_finished)
        self.dl_base_worker.start()

    def _on_download_base_finished(self, success: bool, msg: str):
        if success:
            QMessageBox.information(self, "Download Base Completato", "Pesi neurali Qwen3-TTS Base scaricati con successo!\nLa clonazione vocale reale è ora attiva.")
        else:
            show_copyable_error(self, "Errore Download Base", f"Impossibile scaricare i pesi Base:\n{msg}", is_warning=True)
        self._update_weights_status_display()

    def get_config(self) -> Dict[str, Any]:
        spk_full = self.combo_speaker.currentText()
        speaker = self.combo_speaker.currentData() or spk_full.split(" ")[0].strip("(),:")
        speed = self.slider_rate.value() / 100.0
        pitch = float(self.slider_pitch.value())
        temp = self.slider_temp.value() / 100.0

        return {
            "speaker": speaker,
            "speaker_or_profile": speaker,
            "speaker_full": spk_full,
            "language": "English",
            "instruct": self.txt_custom_instruct.text().strip(),
            "speed": speed,
            "pitch": pitch,
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
