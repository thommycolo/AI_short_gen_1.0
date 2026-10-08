"""AI Short Generator 1.0 - Production Progress Dialog & Granular Cancellation Modals"""

import time
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal, QTimer
from app.core.cancellation_manager import ProductionCancellationManager


class CancelActiveStoryModal(QDialog):
    """Dialogo di conferma interruzione per un testo parzialmente prodotto."""

    def __init__(self, story_title: str, created_parts: int, total_parts: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("⚠️ Conferma Annullamento Testo Incompleto")
        self.resize(600, 320)
        self.setObjectName("ModalWindow")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QLabel("⚠️ ATTENZIONE: ANNULLAMENTO TESTO INCOMPLETO")
        header.setStyleSheet("color: #C4A36B; font-weight: 600; font-size: 14px;")
        layout.addWidget(header)

        msg = QLabel(
            f"Stai interrompendo la produzione del testo:\n"
            f"📌 \"{story_title}\" (Richiede {total_parts} Short - Creati: {created_parts} su {total_parts}).\n\n"
            f"COSA SUCCEDE CONFERMANDO L'ANNULLAMENTO:\n"
            f"1. ELIMINAZIONE SHORT PARZIALI: I {created_parts} Short già creati VERRANNO ELIMINATI da disco.\n"
            f"2. TESTO RIUTILIZZABILE: Lo script tornerà DISPONIBILE nell'archivio per essere riprodotto intero.\n"
            f"3. RIPRISTINO DELLE CLIP VIDEO: Tutte le clip video assegnate tornano disponibili nel Video Pool.\n"
            f"4. I testi già completati al 100% RIMANGONO REGOLARMENTE SALVATI."
        )
        msg.setWordWrap(True)
        msg.setObjectName("HelperText")
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_continue = QPushButton("↩️ Continua Creazione")
        btn_continue.clicked.connect(self.reject)

        btn_confirm = QPushButton(f"🛑 Elimina i {created_parts} Short & Annulla")
        btn_confirm.setObjectName("DangerButton")
        btn_confirm.clicked.connect(self.accept)

        btn_row.addWidget(btn_continue)
        btn_row.addStretch()
        btn_row.addWidget(btn_confirm)
        layout.addLayout(btn_row)


class CancelBatchModal(QDialog):
    """Dialogo di conferma interruzione globale dell'intera coda di lavoro."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("⚠️ Conferma Interruzione Globale Coda")
        self.resize(600, 260)
        self.setObjectName("ModalWindow")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QLabel("⚠️ CONFERMA INTERRUZIONE GLOBALE PRODUZIONE")
        header.setStyleSheet("color: #AA7373; font-weight: 600; font-size: 14px;")
        layout.addWidget(header)

        msg = QLabel(
            "Sei sicuro di voler interrompere la produzione dell'intera coda?\n\n"
            "• I testi completati al 100% rimarranno SALVATI su disco e marcati come UTILIZZATO.\n"
            "• I testi incompleti o in corso verranno ripuliti (Short parziali eliminati, testi DISPONIBILI).\n"
            "• Le clip video residue tornano usabili nel pool."
        )
        msg.setWordWrap(True)
        msg.setObjectName("HelperText")
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_continue = QPushButton("↩️ Continua la Creazione")
        btn_continue.clicked.connect(self.reject)

        btn_confirm = QPushButton("🛑 CONFERMA ED INTERROMPI TUTTO")
        btn_confirm.setObjectName("DangerButton")
        btn_confirm.clicked.connect(self.accept)

        btn_row.addWidget(btn_continue)
        btn_row.addStretch()
        btn_row.addWidget(btn_confirm)
        layout.addLayout(btn_row)


class ProductionProgressDialog(QDialog):
    """
    Finestra Avanzamento Lavori Professionale:
    - Stepper a 4 fasi per la clip corrente
    - Barra progresso globale batch ed ETA
    - Interruzione granulare per singolo testo o batch abort
    """

    cancel_requested = Signal()

    def __init__(
        self,
        cancellation_mgr: ProductionCancellationManager,
        total_stories: int,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.cancellation_mgr = cancellation_mgr
        self.total_stories = total_stories
        self.completed_stories = 0
        self.start_time = time.time()
        self.setWindowTitle("Avanzamento Produzione Video Short")
        self.resize(840, 560)
        self.setObjectName("ModalWindow")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # Header con stato GPU
        top_bar = QHBoxLayout()
        header_lbl = QLabel("AVANZAMENTO PRODUZIONE VIDEO SHORT")
        header_lbl.setObjectName("SectionHeader")

        self.gpu_badge = QLabel("● GPU CUDA ATTIVA ⚡")
        self.gpu_badge.setObjectName("BadgeAvailable")

        top_bar.addWidget(header_lbl)
        top_bar.addStretch()
        top_bar.addWidget(self.gpu_badge)
        layout.addLayout(top_bar)

        # Box Avanzamento Globale
        glob_box = QFrame()
        glob_box.setObjectName("InnerCard")
        gb_layout = QVBoxLayout(glob_box)
        gb_layout.setContentsMargins(10, 8, 10, 8)
        gb_layout.setSpacing(4)

        self.lbl_glob_status = QLabel(f"STATO GLOBALE BATCH: 0 DI {self.total_stories} TESTI COMPLETATI (0%)")
        self.lbl_glob_status.setStyleSheet("font-weight: 600; color: #DCE0EA;")

        self.prog_global = QProgressBar()
        self.prog_global.setRange(0, 100)
        self.prog_global.setValue(0)

        self.lbl_eta = QLabel("Tempo Trascorso: 00m 00s  |  Tempo Rimanente Stimato (ETA): Calcolo in corso...")
        self.lbl_eta.setObjectName("HelperText")

        gb_layout.addWidget(self.lbl_glob_status)
        gb_layout.addWidget(self.prog_global)
        gb_layout.addWidget(self.lbl_eta)
        layout.addWidget(glob_box)

        # Stepper 4 Fasi della Parte Corrente
        layout.addWidget(QLabel("TESTO CORRENTE IN LAVORAZIONE:"))
        stepper_box = QFrame()
        stepper_box.setObjectName("InnerCard")
        st_layout = QVBoxLayout(stepper_box)
        st_layout.setContentsMargins(10, 8, 10, 8)
        st_layout.setSpacing(6)

        self.lbl_current_story = QLabel("Inizializzazione worker isolati...")
        self.lbl_current_story.setStyleSheet("font-weight: 500; color: #BFA175;")
        st_layout.addWidget(self.lbl_current_story)

        # 4 Fasi orizzontali
        phases_row = QHBoxLayout()
        self.step_tts = QLabel("[ 1. VOCE QWEN3 ]\n⏳ IN ATTESA")
        self.step_whisper = QLabel("[ 2. SOTTOTITOLI ]\n⏳ IN ATTESA")
        self.step_bgm = QLabel("[ 3. DUCKING BGM ]\n⏳ IN ATTESA")
        self.step_render = QLabel("[ 4. RENDER NVENC ]\n⏳ IN ATTESA")

        for s in [self.step_tts, self.step_whisper, self.step_bgm, self.step_render]:
            s.setAlignment(Qt.AlignCenter)
            s.setObjectName("HelperText")
            s.setStyleSheet("background-color: #1A1C22; border-radius: 4px; padding: 6px;")
            phases_row.addWidget(s)

        st_layout.addLayout(phases_row)

        self.prog_current_step = QProgressBar()
        self.prog_current_step.setRange(0, 100)
        self.prog_current_step.setValue(0)
        st_layout.addWidget(self.prog_current_step)
        layout.addWidget(stepper_box)

        # Console Log Compatta
        layout.addWidget(QLabel("CONSOLE ESECUZIONE ISOLATA WDDM:"))
        self.lbl_console = QLabel("Avvio orchestratore VRAM serializzato...")
        self.lbl_console.setStyleSheet("font-family: Consolas; font-size: 11px; color: #949CAE; background: #121418; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.lbl_console, stretch=1)

        # Footer
        footer = QHBoxLayout()
        self.btn_abort = QPushButton("🛑 INTERROMPI TUTTA LA CODA RIMANENTE")
        self.btn_abort.setObjectName("DangerButton")
        self.btn_abort.clicked.connect(self._on_abort_clicked)

        footer.addStretch()
        footer.addWidget(self.btn_abort)
        layout.addLayout(footer)

        # Timer aggiornamento tempo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer_labels)
        self.timer.start(1000)

    def update_active_phase(self, phase_idx: int, pct: float):
        """Aggiorna lo stato della fase attiva e la percentuale del passo corrente."""
        self.prog_current_step.setValue(int(pct))
        phases = [
            (self.step_tts, "[ 1. VOCE QWEN3 ]"),
            (self.step_whisper, "[ 2. SOTTOTITOLI ]"),
            (self.step_bgm, "[ 3. DUCKING BGM ]"),
            (self.step_render, "[ 4. RENDER NVENC ]")
        ]
        for i, (lbl, name) in enumerate(phases):
            if i < phase_idx:
                lbl.setText(f"{name}\n✅ COMPLETATO")
                lbl.setStyleSheet("background-color: #22382D; color: #729B84; border-radius: 4px; padding: 6px;")
            elif i == phase_idx:
                lbl.setText(f"{name}\n⚡ IN CORSO")
                lbl.setStyleSheet("background-color: #2F3B4F; color: #DCE0EA; border-radius: 4px; padding: 6px;")
            else:
                lbl.setText(f"{name}\n⏳ IN ATTESA")
                lbl.setStyleSheet("background-color: #1A1C22; color: #666E7F; border-radius: 4px; padding: 6px;")

        phase_names = ["Sintesi Vocale Qwen3-TTS", "Allineamento Sottotitoli Whisper", "Mastering Audio & BGM", "Montaggio Hardware NVENC"]
        p_name = phase_names[phase_idx] if 0 <= phase_idx < len(phase_names) else f"Fase {phase_idx+1}"
        self.lbl_console.setText(f"[{time.strftime('%H:%M:%S')}] {p_name} ({pct:.0f}%) in esecuzione...")

    def update_active_story(self, title: str, current_part: int, total_parts: int = 1, clip_name: str = ""):
        """Aggiorna l'etichetta del testo e della parte attualmente in lavorazione."""
        extra = f" (Categoria: {clip_name})" if clip_name else ""
        self.lbl_current_story.setText(f'📌 "{title}" — Parte {current_part} di {total_parts}{extra}')

    def finish_production(self, total_completed: int):
        """Conclude l'animazione di progresso e commuta il dialogo in stato completato."""
        self.completed_stories = self.total_stories
        self.prog_global.setValue(100)
        self.prog_current_step.setValue(100)
        self.lbl_glob_status.setText(
            f"STATO GLOBALE BATCH: {self.total_stories} DI {self.total_stories} TESTI COMPLETATI (100%)"
        )
        self.lbl_current_story.setText("✅ Produzione terminata con successo!")
        self.lbl_console.setText(f"[{time.strftime('%H:%M:%S')}] Tutti i {total_completed} Short sono pronti nella cartella renders.")
        for lbl, name in [
            (self.step_tts, "[ 1. VOCE QWEN3 ]"),
            (self.step_whisper, "[ 2. SOTTOTITOLI ]"),
            (self.step_bgm, "[ 3. DUCKING BGM ]"),
            (self.step_render, "[ 4. RENDER NVENC ]")
        ]:
            lbl.setText(f"{name}\n✅ COMPLETATO")
            lbl.setStyleSheet("background-color: #22382D; color: #729B84; border-radius: 4px; padding: 6px;")

        self.btn_abort.setText("CHIUDI")
        self.btn_abort.setObjectName("PrimaryButton")
        try:
            self.btn_abort.clicked.disconnect()
        except Exception:
            pass
        self.btn_abort.clicked.connect(self.accept)

    def update_progress(self, story_idx: int, story_title: str, part_num: int, phase_name: str, pct: float):
        self.lbl_current_story.setText(f'📌 "{story_title}" - Parte {part_num}: {phase_name}')
        self.prog_current_step.setValue(int(pct))
        self.lbl_console.setText(f"[{time.strftime('%H:%M:%S')}] {phase_name} ({pct:.0f}%) su worker isolato.")

        # Aggiorna badge stepper
        if "Vocale" in phase_name:
            self.step_tts.setText("[ 1. VOCE QWEN3 ]\n⚡ IN CORSO")
            self.step_tts.setStyleSheet("background-color: #2F3B4F; color: #DCE0EA; border-radius: 4px; padding: 6px;")
        elif "Sottotitoli" in phase_name:
            self.step_tts.setText("[ 1. VOCE QWEN3 ]\n✅ COMPLETATO")
            self.step_tts.setStyleSheet("background-color: #22382D; color: #729B84; border-radius: 4px; padding: 6px;")
            self.step_whisper.setText("[ 2. SOTTOTITOLI ]\n⚡ IN CORSO")
            self.step_whisper.setStyleSheet("background-color: #2F3B4F; color: #DCE0EA; border-radius: 4px; padding: 6px;")
        elif "Video" in phase_name or "BGM" in phase_name:
            self.step_whisper.setText("[ 2. SOTTOTITOLI ]\n✅ COMPLETATO")
            self.step_bgm.setText("[ 3. DUCKING BGM ]\n⚡ IN CORSO")
        elif "NVENC" in phase_name:
            self.step_bgm.setText("[ 3. DUCKING BGM ]\n✅ COMPLETATO")
            self.step_render.setText("[ 4. RENDER NVENC ]\n⚡ IN CORSO")
        elif "Completato" in phase_name:
            self.step_render.setText("[ 4. RENDER NVENC ]\n✅ COMPLETATO")
            self.completed_stories = story_idx
            glob_pct = int((self.completed_stories / max(1, self.total_stories)) * 100)
            self.prog_global.setValue(glob_pct)
            self.lbl_glob_status.setText(
                f"STATO GLOBALE BATCH: {self.completed_stories} DI {self.total_stories} TESTI COMPLETATI ({glob_pct}%)"
            )

    def _update_timer_labels(self):
        elapsed = int(time.time() - self.start_time)
        el_m, el_s = divmod(elapsed, 60)

        if self.completed_stories > 0:
            avg_per_story = elapsed / self.completed_stories
            rem_sec = int(avg_per_story * (self.total_stories - self.completed_stories))
            rem_m, rem_s = divmod(rem_sec, 60)
            eta_str = f"~{rem_m:02d}m {rem_s:02d}s"
        else:
            eta_str = "Stima in corso..."

        self.lbl_eta.setText(f"Tempo Trascorso: {el_m:02d}m {el_s:02d}s  |  Tempo Rimanente Stimato (ETA): {eta_str}")

    def _on_abort_clicked(self):
        modal = CancelBatchModal(self)
        if modal.exec() == QDialog.Accepted:
            self.cancellation_mgr.request_cancellation()
            self.cancel_requested.emit()
            self.reject()

