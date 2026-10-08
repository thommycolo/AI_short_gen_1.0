"""AI Short Generator 1.0 - Build Script for PyInstaller (--onedir) Distribution"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
SPEC_FILE = ROOT_DIR / "AI_Short_Generator.spec"


def build():
    print("=" * 60)
    print("AI SHORT GENERATOR 1.0 - BUILD DESKTOP EXECUTABLE")
    print("Modalità: PyInstaller --onedir nativo Windows 64-bit")
    print("=" * 60)

    # Verifica presenza spec file
    if not SPEC_FILE.exists():
        print(f"Errore: Spec file non trovato in {SPEC_FILE}")
        sys.exit(1)

    # Pulizia directory build e dist precedenti
    print("\n[1/3] Pulizia directory build e dist...")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)

    # Esecuzione PyInstaller
    print("\n[2/3] Avvio compilazione PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE)
    ]

    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        print(f"\n[ERRORE] Compilazione fallita con codice {res.returncode}")
        sys.exit(res.returncode)

    # Verifica output
    target_exe = DIST_DIR / "AI_Short_Generator" / "AI_Short_Generator.exe"
    if target_exe.exists():
        print("\n[3/3] Compilazione completata con successo!")
        print(f"Eseguibile generato: {target_exe}")
        print("Cartella portabile pronta in: dist/AI_Short_Generator/")
    else:
        print("\n[ATTENZIONE] Eseguibile non trovato nel path atteso.")


if __name__ == "__main__":
    build()

