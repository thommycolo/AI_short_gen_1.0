"""AI Short Generator 1.0 - Download Pesi Neurali Qwen3-TTS (Hugging Face)"""

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


def download_weights(model_type: str = "custom") -> bool:
    models = {
        "custom": ("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "Qwen3-TTS-CustomVoice"),
        "base": ("Qwen/Qwen3-TTS-12Hz-1.7B-Base", "Qwen3-TTS-Base"),
        "design": ("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", "Qwen3-TTS-VoiceDesign")
    }
    repo_info = models.get(model_type, models["custom"])
    repo_id, folder_name = repo_info
    target_dir = MODELS_DIR / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    print("============================================================")
    print("  AI SHORT GENERATOR - DOWNLOAD PESI QWEN3-TTS")
    print("============================================================")
    print(f"Modello selezionato: {model_type}")
    print(f"Repository Hugging Face: {repo_id}")
    print(f"Cartella di destinazione: {target_dir}")
    print("Dimensione totale: ~4.5 GB (model.safetensors 3.8GB + speech tokenizer)")
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
        print("Il modello neurale e' ora pronto e attivo per la sintesi vocale.")
        print("============================================================")
        return True
    except Exception as e:
        print(f"\n[ERRORE] durante il download: {e}")
        return False


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "custom"
    success = download_weights(m)
    sys.exit(0 if success else 1)

