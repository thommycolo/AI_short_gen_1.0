"""AI Short Generator 1.0 - Secure API Key Manager & Interactive CLI/UI Fallback"""

import os
import sys
import json
import getpass
from pathlib import Path
from typing import Optional

from app.config import APP_DATA_DIR
from app.utils.logger import log


class APIKeyManager:
    """
    Risolve e memorizza in modo sicuro le API Key per i motori vocali.
    Supporta risoluzione da variabili d'ambiente, file di configurazione locale
    e fallback interattivo da terminale (CMD/PowerShell) o GUI.
    """

    CREDENTIALS_FILE: Path = APP_DATA_DIR / "credentials.json"
    ENV_VARS = ["GEMINI_API_KEY", "GOOGLE_API_KEY"]

    @classmethod
    def get_api_key(cls, provider: str = "gemini", allow_interactive: bool = True) -> str:
        """
        Restituisce la chiave API per il provider richiesto.
        Se non trovata e allow_interactive è True, blocca l'esecuzione e la richiede all'utente.
        """
        # 1. Variabile d'ambiente di sistema
        for env_var in cls.ENV_VARS:
            val = os.environ.get(env_var, "").strip()
            if val:
                return val

        # 2. File di credenziali salvato localmente
        if cls.CREDENTIALS_FILE.exists():
            try:
                with open(cls.CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                key = (
                    data.get(f"{provider.lower()}_api_key")
                    or data.get("gemini_api_key")
                    or data.get("api_key")
                )
                if key and str(key).strip():
                    key_str = str(key).strip()
                    os.environ["GEMINI_API_KEY"] = key_str
                    os.environ["GOOGLE_API_KEY"] = key_str
                    return key_str
            except Exception as e:
                log.warning(f"Errore lettura file credenziali: {e}")

        # 3. Fallback interattivo se la chiave è assente
        if allow_interactive:
            return cls._prompt_key_interactively(provider)

        raise ValueError(
            f"API Key per il provider '{provider}' non trovata. "
            f"Configurala nelle impostazioni dell'app o imposta la variabile d'ambiente {cls.ENV_VARS[0]}."
        )

    @classmethod
    def has_api_key(cls, provider: str = "gemini") -> bool:
        """Verifica se una chiave è già configurata senza attivare prompt interattivi."""
        try:
            key = cls.get_api_key(provider=provider, allow_interactive=False)
            return bool(key and len(key) >= 10)
        except Exception:
            return False

    @classmethod
    def save_api_key(cls, key: str, provider: str = "gemini"):
        """Salva la chiave su disco e la rende immediatamente attiva nel processo corrente."""
        clean_key = key.strip()
        cls.CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        if cls.CREDENTIALS_FILE.exists():
            try:
                with open(cls.CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        data[f"{provider.lower()}_api_key"] = clean_key
        data["last_updated"] = True

        with open(cls.CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        os.environ["GEMINI_API_KEY"] = clean_key
        os.environ["GOOGLE_API_KEY"] = clean_key
        log.info(f"API Key per '{provider}' salvata con successo in {cls.CREDENTIALS_FILE.name}")

    @classmethod
    def mask_key(cls, key: str) -> str:
        """Restituisce una rappresentazione mascherata sicura della chiave."""
        if not key or len(key) < 8:
            return "••••••••"
        return f"{key[:4]}••••••••{key[-4:]}"

    @classmethod
    def _prompt_key_interactively(cls, provider: str) -> str:
        """Blocca l'esecuzione e richiede la chiave tramite terminale o finestra GUI."""
        banner = "=" * 72
        prompt_msg = (
            f"\n{banner}\n"
            f" [AI SHORT GENERATOR] ATTENZIONE: API KEY MANCANTE ({provider.upper()})\n"
            f"{banner}\n"
            f" Il modulo vocale '{provider}' richiede una chiave API valida.\n"
            f" Puoi ottenere una chiave gratuita su: https://aistudio.google.com/\n\n"
        )

        # Fallback 1: Terminale Interattivo (CMD / PowerShell / Bash)
        if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            sys.stderr.write(prompt_msg)
            sys.stderr.flush()

            while True:
                try:
                    try:
                        entered_key = getpass.getpass(" Inserisci la tua Google/Gemini API Key: ").strip()
                    except Exception:
                        entered_key = input(" Inserisci la tua Google/Gemini API Key: ").strip()

                    if not entered_key:
                        print(" ❌ La chiave non può essere vuota. Riprova o premi CTRL+C per interrompere.")
                        continue

                    if len(entered_key) < 15:
                        print(" ⚠️  La chiave inserita sembra incompleta (meno di 15 caratteri). Riprova.")
                        continue

                    cls.save_api_key(entered_key, provider)
                    print(" ✅ Chiave salvata con successo! Ripresa esecuzione in corso...\n")
                    return entered_key
                except KeyboardInterrupt:
                    print("\n Operazione annullata dall'utente.")
                    sys.exit(1)

        # Fallback 2: Se siamo in ambiente GUI PySide6 senza terminale aperto
        try:
            from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit
            app = QApplication.instance()
            if app is not None:
                dialog_title = "Configurazione API Key Richiesta"
                dialog_prompt = (
                    f"Il modulo di generazione vocale richiede la API Key di Google/Gemini.\n\n"
                    f"Inserisci la tua chiave (recuperabile gratis su https://aistudio.google.com/):"
                )
                text, ok = QInputDialog.getText(
                    None, dialog_title, dialog_prompt, QLineEdit.EchoMode.Password
                )
                if ok and text.strip():
                    cls.save_api_key(text.strip(), provider)
                    return text.strip()
        except Exception:
            pass

        raise ValueError(
            f"Nessuna API Key configurata per {provider}. "
            f"Impossibile interagire con il terminale o la GUI."
        )

