"""AI Short Generator 1.0 - Main Desktop Application Entry Point (Native Windows 64-bit PySide6)"""

import os
import sys
import multiprocessing
from pathlib import Path

# Assicura che la root del progetto sia sempre in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Assicura che la directory dei binari portabili (ffmpeg, sox) sia in cima al PATH di Windows
BIN_DIR = PROJECT_ROOT / "app_data" / "bin"
BIN_DIR.mkdir(parents=True, exist_ok=True)
bin_dir_str = str(BIN_DIR.resolve())
if bin_dir_str not in os.environ.get("PATH", ""):
    os.environ["PATH"] = bin_dir_str + os.pathsep + os.environ.get("PATH", "")

# Disattiva warning symlink di Hugging Face su Windows (senza modalità sviluppatore)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont

# Assicura che tutti i QMessageBox mostrati abbiano il testo selezionabile e copiabile
_orig_qmessagebox_exec = QMessageBox.exec
def _copyable_qmessagebox_exec(self, *args, **kwargs):
    self.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    return _orig_qmessagebox_exec(self, *args, **kwargs)
QMessageBox.exec = _copyable_qmessagebox_exec

from app.config import APP_DATA_DIR
from app.ui.theme import QSS_STYLESHEET
from app.ui.main_window import MainWindow
from app.ui.modals.first_run_wizard import FirstRunWizardModal
from app.utils.logger import log


def main():
    # Fondamentale per il packaging Windows PyInstaller e processi isolati 'spawn'
    multiprocessing.freeze_support()

    # Configurazione High-DPI per display ad alta densità (4K / 2K)
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("AI Short Generator")
    app.setOrganizationName("DeepMind")
    app.setApplicationVersion("1.0")

    # Font di sistema esplicito con dimensione positiva (risolve QFont::setPointSize warning)
    app.setFont(QFont("Segoe UI", 10))

    # Applicazione Palette Soft Dark Globale (Zero #000000, Zero Fluo)
    app.setStyleSheet(QSS_STYLESHEET)

    # Impostazione Icona Nativa
    icon_path = Path("assets/icons/app.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Verifica First-Run Wizard
    first_run_flag = APP_DATA_DIR / ".setup_done"
    if not first_run_flag.exists():
        log.info("Primo avvio rilevato: apertura del First-Run Setup Wizard...")
        wizard = FirstRunWizardModal()
        if wizard.exec():
            first_run_flag.parent.mkdir(parents=True, exist_ok=True)
            first_run_flag.write_text("SETUP_COMPLETED", encoding="utf-8")
        else:
            log.warning("Setup iniziale saltato o chiuso dall'utente.")

    # Avvio Finestra Principale
    window = MainWindow()
    window.show()

    log.info("Applicazione desktop avviata in modalità nativa DirectX/OpenGL a 60 FPS.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

