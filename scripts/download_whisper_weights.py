"""AI Short Generator 1.0 - Download Pesi Faster-Whisper Large-V3-Turbo (Hugging Face)"""

import os
import sys
import time
from pathlib import Path

# Configura encoding console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Assicura import del modulo app
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import MODELS_DIR


def download_whisper(model_size: str = "large-v3-turbo") -> bool:
    repo_id = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
    target_dir = MODELS_DIR / f"faster-whisper-{model_size}"
    target_dir.mkdir(parents=True, exist_ok=True)

    print("============================================================")
    print("  AI SHORT GENERATOR - DOWNLOAD PESI FASTER-WHISPER")
    print("============================================================")
    print(f"Modello: {model_size}")
    print(f"Repository Hugging Face: {repo_id}")
    print(f"Cartella di destinazione: {target_dir}")
    print("Dimensione totale: ~1.6 GB (model.bin INT8/FP16 + tokenizer)")
    print("Download diretto con supporto ripresa automatica (resume)...")
    print("------------------------------------------------------------\n")

    try:
        from huggingface_hub import snapshot_download
        start_t = time.time()
        local_path = snapshot_download(
            repo_id=repo_id,
            repo_type="model",
            local_dir=str(target_dir),
            resume_download=True
        )
        elapsed = time.time() - start_t
        print("\n------------------------------------------------------------")
        print(f"[OK] DOWNLOAD COMPLETATO CON SUCCESSO in {elapsed:.1f}s!")
        print(f"Cartella locale pesi: {local_path}")
        print("Il modello Faster-Whisper e' ora pronto e attivo per l'allineamento sottotitoli.")
        print("============================================================")
        return True
    except Exception as e:
        print(f"\n[ERRORE] durante il download: {e}")
        return False


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "large-v3-turbo"
    success = download_whisper(m)
    sys.exit(0 if success else 1)

