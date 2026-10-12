"""AI Short Generator 1.0 - Quota Tracker & Safeguard (95% Threshold Protection)"""

import os
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import APP_DATA_DIR
from app.utils.logger import log


class QuotaSafeguardExceededError(Exception):
    """Sollevata quando l'utilizzo raggiunge o supera la soglia di sicurezza del 95% del limite mensile."""

    def __init__(self, provider: str, current: int, attempted: int, limit: int, threshold_pct: float = 95.0):
        self.provider = provider
        self.current = current
        self.attempted = attempted
        self.limit = limit
        self.threshold = int(limit * (threshold_pct / 100.0))
        self.threshold_pct = threshold_pct
        super().__init__(
            f"BLOCCO DI SICUREZZA 95%: Il provider '{provider}' ha raggiunto {current:,} / {limit:,} caratteri mensili "
            f"(Soglia di sicurezza {threshold_pct:.0f}%: {self.threshold:,}). La richiesta di {attempted:,} caratteri "
            f"porterebbe il consumo a {current + attempted:,}, superando la soglia gratuita sicura. "
            f"Operazione bloccata per prevenire addebiti inaspettati."
        )


class QuotaTracker:
    """
    Monitor persistente dell'utilizzo cumulativo delle API TTS.
    Blocca automaticamente le richieste prima di superare il 95% del limite mensile gratuito.
    """

    DEFAULT_MONTHLY_LIMITS: Dict[str, int] = {
        "gemini_tts": 1_000_000,             # 1.000.000 caratteri/mese limite free tier
        "google_cloud_neural2": 1_000_000,   # 1.000.000 caratteri WaveNet / Neural2
        "google_cloud_standard": 4_000_000,  # 4.000.000 caratteri standard
    }

    _instance: Optional["QuotaTracker"] = None
    _lock = threading.RLock()

    def __new__(cls, storage_path: Optional[Path] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, storage_path: Optional[Path] = None):
        with self._lock:
            if storage_path is not None:
                self.storage_path = Path(storage_path)
                self.safeguard_percentage = 95.0
                self._load()
                self._initialized = True
            elif not getattr(self, "_initialized", False):
                self.storage_path = APP_DATA_DIR / "tts_quota_tracker.json"
                self.safeguard_percentage = 95.0
                self._cache = {}
                self._load()
                self._initialized = True

    @staticmethod
    def get_current_month_key() -> str:
        from datetime import timezone
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _load(self):
        with self._lock:
            if self.storage_path.exists():
                try:
                    with open(self.storage_path, "r", encoding="utf-8") as f:
                        self._cache = json.load(f)
                except Exception as e:
                    log.error(f"Errore lettura quota tracker ({e}), inizializzazione nuovo database.")
                    self._cache = {}
            else:
                self._cache = {}

    def _save(self):
        with self._lock:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.storage_path.with_suffix(".tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f, indent=2, ensure_ascii=False)
                if self.storage_path.exists():
                    os.replace(tmp_path, self.storage_path)
                else:
                    os.rename(tmp_path, self.storage_path)
            except Exception as e:
                log.error(f"Errore scrittura quota tracker: {e}")

    def set_monthly_limit(self, provider_id: str, limit: int):
        with self._lock:
            self.DEFAULT_MONTHLY_LIMITS[provider_id.lower()] = int(limit)

    def get_monthly_usage(self, provider_id: str) -> Dict[str, Any]:
        """Restituisce lo stato d'uso aggiornato per il provider specificato."""
        with self._lock:
            pid = provider_id.lower()
            month = self.get_current_month_key()
            prov_data = self._cache.get(pid, {})
            month_data = prov_data.get(month, {
                "characters": 0,
                "tokens": 0,
                "requests": 0,
                "last_used": None
            })

            limit = self.DEFAULT_MONTHLY_LIMITS.get(pid, 1_000_000)
            safety_limit = int(limit * (self.safeguard_percentage / 100.0))
            chars_used = int(month_data.get("characters", 0))
            usage_pct = (chars_used / limit) * 100.0 if limit > 0 else 0.0

            return {
                "month": month,
                "provider": pid,
                "characters_used": chars_used,
                "tokens_used": int(month_data.get("tokens", 0)),
                "total_limit": limit,
                "safety_limit_95": safety_limit,
                "safeguard_percentage": self.safeguard_percentage,
                "usage_percentage": usage_pct,
                "is_locked": (chars_used >= safety_limit),
                "remaining_safe_characters": max(0, safety_limit - chars_used),
                "requests_count": int(month_data.get("requests", 0)),
                "last_used": month_data.get("last_used")
            }

    def check_and_reserve(self, provider_id: str, text_length: int):
        """
        Verifica preventivamente se la richiesta di sintesi supera la soglia di sicurezza.
        Solleva QuotaSafeguardExceededError se non è sicuro procedere.
        """
        with self._lock:
            stats = self.get_monthly_usage(provider_id)
            current = stats["characters_used"]
            safety_limit = stats["safety_limit_95"]
            total_limit = stats["total_limit"]

            if (current + text_length) > safety_limit:
                raise QuotaSafeguardExceededError(
                    provider=provider_id,
                    current=current,
                    attempted=text_length,
                    limit=total_limit,
                    threshold_pct=self.safeguard_percentage
                )

    def record_usage(self, provider_id: str, characters_count: int, tokens_count: int = 0):
        """Registra i caratteri e token consumati con successo."""
        with self._lock:
            pid = provider_id.lower()
            month = self.get_current_month_key()
            if pid not in self._cache:
                self._cache[pid] = {}
            if month not in self._cache[pid]:
                self._cache[pid][month] = {
                    "characters": 0,
                    "tokens": 0,
                    "requests": 0,
                    "last_used": None
                }

            self._cache[pid][month]["characters"] += int(characters_count)
            self._cache[pid][month]["tokens"] += int(tokens_count)
            self._cache[pid][month]["requests"] += 1
            from datetime import timezone
            self._cache[pid][month]["last_used"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def reset_current_month(self, provider_id: str):
        """Azzera i contatori del mese corrente per il provider (utile per test o override amministrativo)."""
        with self._lock:
            pid = provider_id.lower()
            month = self.get_current_month_key()
            if pid in self._cache and month in self._cache[pid]:
                self._cache[pid][month] = {
                    "characters": 0,
                    "tokens": 0,
                    "requests": 0,
                    "last_used": None
                }
                self._save()

