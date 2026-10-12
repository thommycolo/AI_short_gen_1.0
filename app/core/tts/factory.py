"""AI Short Generator 1.0 - TTS Factory & Provider Registry"""

from typing import Dict, Type, List, Optional
from app.core.tts.base import BaseTTSProvider
from app.utils.logger import log


class TTSFactory:
    """Factory Pattern per la registrazione e creazione dinamica dei motori vocali."""

    _registry: Dict[str, Type[BaseTTSProvider]] = {}
    _default_provider_id: str = "gemini_tts"

    @classmethod
    def register(cls, provider_id: str, provider_cls: Type[BaseTTSProvider]):
        pid = provider_id.lower().strip()
        cls._registry[pid] = provider_cls
        log.info(f"[TTSFactory] Registrato motore '{pid}' -> {provider_cls.__name__}")

    @classmethod
    def create(cls, provider_id: Optional[str] = None, **kwargs) -> BaseTTSProvider:
        pid = (provider_id or cls._default_provider_id).lower().strip()
        if pid not in cls._registry:
            # Fallback intelligente al primo disponibile se pid non presente
            if cls._registry:
                fallback_key = list(cls._registry.keys())[0]
                log.warning(f"[TTSFactory] Provider '{pid}' non trovato. Uso fallback '{fallback_key}'.")
                return cls._registry[fallback_key](**kwargs)
            raise ValueError(f"Nessun provider registrato nel TTSFactory.")

        provider_cls = cls._registry[pid]
        return provider_cls(**kwargs)

    @classmethod
    def get_registered_providers(cls) -> List[Dict[str, str]]:
        result = []
        for pid, p_cls in cls._registry.items():
            disp_name = getattr(p_cls, "DISPLAY_NAME", pid.title())
            result.append({
                "id": pid,
                "name": disp_name
            })
        return result

    @classmethod
    def set_default_provider(cls, provider_id: str):
        pid = provider_id.lower().strip()
        if pid in cls._registry:
            cls._default_provider_id = pid

