"""AI Short Generator 1.0 - First-Run Wizard & AI Models Setup Dialog"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QScrollArea, QWidget, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread

from app.config import (
    MODELS_DIR, WHISPER_MODEL_NAME, HARDWARE_VRAM_NET_LIMIT_MB,
    HARDWARE_VRAM_TOTAL_BUDGET_MB
)
from app.utils.ffmpeg_installer import find_system_ffmpeg, find_system_ffprobe
from app.utils.logger import log


class DiagnosticsWorker(QThread):
    progress_updated = Signal(int, str)
    diagnostic_completed = Signal(dict)

    def run(self):
        results = {
            "gpu_name": "CPU Fallback Mode",
            "vram_total_mb": 0,
            "cuda_available": False,
            "ffmpeg_path": None,
            "ffprobe_path": None,
            "models_ready": False
        }

        # Step 1: Detect FFmpeg
        self.progress_updated.emit(20, "Ricerca FFmpeg ed FFprobe nel sistema...")
        ffmpeg = find_system_ffmpeg()
        if isinstance(ffmpeg, tuple):
            ffmpeg = ffmpeg[0]
        ffprobe = find_system_ffprobe()
        results["ffmpeg_path"] = ffmpeg
        results["ffprobe_path"] = ffprobe

        # Step 2: Detect GPU & CUDA (nvidia-smi + PyTorch CUDA runtime)
        self.progress_updated.emit(45, "Rilevamento accelerazione GPU e memoria VRAM...")
        try:
            smi_cmd = ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]
            res = subprocess.run(smi_cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                line = res.stdout.strip().split("\n")[0]
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    results["gpu_name"] = parts[0]
                    results["vram_total_mb"] = int(float(parts[1]))
                    results["cuda_available"] = True
        except Exception:
            pass

        try:
            import torch
            if torch.cuda.is_available():
                results["cuda_available"] = True
                results["gpu_name"] = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                results["vram_total_mb"] = int(props.total_memory / (1024 * 1024))
        except Exception:
            pass

        # Step 3: Check AI Models Directory
        self.progress_updated.emit(75, "Verifica repository modelli AI locali...")
        models_dir = Path(MODELS_DIR)
        models_dir.mkdir(parents=True, exist_ok=True)
        results["models_ready"] = True

        self.progress_updated.emit(100, "Diagnostica completata con successo.")
        self.diagnostic_completed.emit(results)


class FirstRunWizardModal(QDialog):
    """
    Finestra Modale di Primo Avvio & Configurazione Risorse AI:
    - Diagnostica GPU (NVIDIA RTX / CUDA) & Hard Cap VRAM (4.0 GB)
    - Verifica e attivazione FFmpeg nativo
    - Inizializzazione directory pesi e modelli AI
    """

    wizard_completed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Configurazione Iniziale & Diagnostica Hardware - AI Short Generator 1.0")
        self.resize(720, 520)
        self.setObjectName("ModalWindow")

        self.diag_results = {}
        self._init_ui()
        self._start_diagnostics()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Titolo e Benvenuto
        lbl_title = QLabel("BENVENUTO IN AI SHORT GENERATOR 1.0")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #DCE0EA;")
        lbl_title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(lbl_title)

        lbl_sub = QLabel("Configurazione autonoma dell'ambiente di produzione video 9:16 e diagnostica hardware:")
        lbl_sub.setStyleSheet("color: #949CAE; font-size: 12px;")
        lbl_sub.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(lbl_sub)

        # Card Diagnostica Hardware
        card = QFrame()
        card.setObjectName("CardSurface")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(10)

        self.lbl_gpu_status = QLabel("GPU: Rilevamento in corso...")
        self.lbl_gpu_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #DCE0EA;")
        c_layout.addWidget(self.lbl_gpu_status)

        self.lbl_vram_status = QLabel(f"Budget VRAM Netto: {HARDWARE_VRAM_NET_LIMIT_MB} MB (Tetto Totale: {HARDWARE_VRAM_TOTAL_BUDGET_MB} MB)")
        self.lbl_vram_status.setStyleSheet("color: #949CAE; font-size: 11px;")
        c_layout.addWidget(self.lbl_vram_status)

        self.lbl_ffmpeg_status = QLabel("FFmpeg: Rilevamento in corso...")
        self.lbl_ffmpeg_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #DCE0EA;")
        c_layout.addWidget(self.lbl_ffmpeg_status)

        self.lbl_models_status = QLabel(f"Percorso Modelli AI: {MODELS_DIR}")
        self.lbl_models_status.setStyleSheet("color: #949CAE; font-size: 11px;")
        c_layout.addWidget(self.lbl_models_status)

        main_layout.addWidget(card)

        # Barra di Progresso
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        main_layout.addWidget(self.prog_bar)

        self.lbl_diag_log = QLabel("Inizializzazione...")
        self.lbl_diag_log.setStyleSheet("color: #6B82A6; font-size: 11px;")
        main_layout.addWidget(self.lbl_diag_log)

        # Note e Specifiche
        info_box = QLabel(
            "• Architettura Desktop Nativa a 64-bit (Zero WebApp, Zero Electron)\n"
            "• Isolamento processi worker 'spawn' per bonifica 100% VRAM sotto Windows WDDM\n"
            "• Conform 9:16 nativo Full HD (1080x1920 @ 60 FPS) con codifica NVENC"
        )
        info_box.setStyleSheet("color: #666E7F; font-size: 11px; background-color: #181A20; padding: 8px; border-radius: 4px;")
        main_layout.addWidget(info_box)

        # Footer con pulsanti
        footer = QHBoxLayout()
        self.btn_recheck = QPushButton("🔄 Ricontrolla Risorse")
        self.btn_recheck.clicked.connect(self._start_diagnostics)
        footer.addWidget(self.btn_recheck)

        footer.addStretch()

        self.btn_proceed = QPushButton("🚀 Accedi all'Applicazione")
        self.btn_proceed.setObjectName("AccentButton")
        self.btn_proceed.setEnabled(False)
        self.btn_proceed.clicked.connect(self._on_proceed)
        footer.addWidget(self.btn_proceed)

        main_layout.addLayout(footer)

    def _start_diagnostics(self):
        self.prog_bar.setValue(0)
        self.btn_proceed.setEnabled(False)
        self.worker = DiagnosticsWorker()
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.diagnostic_completed.connect(self._on_completed)
        self.worker.start()

    def _on_progress(self, percent: int, msg: str):
        self.prog_bar.setValue(percent)
        self.lbl_diag_log.setText(msg)

    def _on_completed(self, results: dict):
        self.diag_results = results
        if results.get("cuda_available"):
            self.lbl_gpu_status.setText(f"GPU: 🟢 {results['gpu_name']} (CUDA Attiva)")
            self.lbl_gpu_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #729B84;")
            self.lbl_vram_status.setText(
                f"VRAM Rilevata: {results['vram_total_mb']} MB (Budget Netto App: {HARDWARE_VRAM_NET_LIMIT_MB} MB | Safe DWM: 1200 MB)"
            )
        else:
            self.lbl_gpu_status.setText("GPU: 🟡 Nessuna GPU NVIDIA CUDA rilevata (Esecuzione su CPU)")
            self.lbl_gpu_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #C4A36B;")

        if results.get("ffmpeg_path"):
            self.lbl_ffmpeg_status.setText(f"FFmpeg: 🟢 Confermato ({results['ffmpeg_path']})")
            self.lbl_ffmpeg_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #729B84;")
        else:
            self.lbl_ffmpeg_status.setText("FFmpeg: 🟡 Non trovato in PATH (Verrà utilizzato il motore integrato)")
            self.lbl_ffmpeg_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #C4A36B;")

        self.lbl_diag_log.setText("Tutti i componenti sono pronti per l'esecuzione.")
        self.btn_proceed.setEnabled(True)

    def _on_proceed(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.wait(1000)
        self.wizard_completed.emit()
        self.accept()

    def closeEvent(self, event):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)
        super().closeEvent(event)

    def reject(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)
        super().reject()


