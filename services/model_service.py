from __future__ import annotations

import logging

logger = logging.getLogger("jarvis.services.model")


class ModelService:
    def __init__(self, provider):
        self.provider = provider

    def get_models(self):
        try:
            return self.provider.list_models()
        except Exception as exc:
            logger.warning("provider_list_models_failed: %s, checking disk manifests", exc)
            try:
                from llm.ollama import _scan_local_ollama_manifests
                local_models = _scan_local_ollama_manifests()
                if local_models:
                    return local_models
            except Exception:
                pass
            raise

    def get_available_models(self) -> dict[str, list]:
        return {"models": self.get_models()}
