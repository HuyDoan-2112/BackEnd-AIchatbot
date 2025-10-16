from __future__ import annotations
import httpx
from typing import Any, Dict, List, Optional

from app.core.config import Settings


def _clean_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values so we only pass explicit parameters downstream."""
    return {k: v for k, v in config.items() if v is not None}


class ModelRegistry:
    """
    Holds chat and embedding model configuration so services can initialize
    providers (LangChain chat models, embedding clients, etc.) without hard-coding.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._chat_models: Dict[str, Dict[str, Any]] = {}
        self._embedding_models: Dict[str, Dict[str, Any]] = {}
        self._default_chat_model = settings.MODEL_NAME
        self._default_embedding_model = settings.EMBEDDING_MODEL_NAME
        self._initialized = False

    async def initialize(self) -> None:
        """Register built-in chat/embedding models from configuration."""
        base_url = self.settings.MODEL_BASE_URL or "http://localhost:1234/v1"
        
        # Fecth the list of modesl from server local
        try: 
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url}/models")
                resp.raise_for_status()
                models_data = resp.json().get("data", [])
                
        except Exception as e:
            models_data = []
            
            
        # Take every model from the list
        for m in models_data:
            model_id = m.get('id')
            if not model_id:
                continue
            self.register_chat_model(
                model_id=model_id,
                config={
                    "model": model_id,
                    "model_provider": "local",
                    "base_url": base_url, 
                    "api_key": self.settings.OPENAI_API_KEY,
                    "temperature": self.settings.MODEL_TEMPERATURE,
                "max_tokens": self.settings.MODEL_MAX_OUTPUT_TOKENS,
                },
                metadata={
                "provider": "local",
                "owned_by": m.get("owned_by", "organization_owner"),
                "context_window": self.settings.MODEL_CONTEXT_WINDOW,
                "completion_reserve": self.settings.MODEL_COMPLETION_RESERVE,
            },
            )
        
        # If fetch fails, take the default one.
        if self._default_embedding_model:
            self.register_embedding_model(
                model_id = self._default_embedding_model,
                config= {
                    "model": self._default_embedding_model,
                    "base_url": self.settings.EMBEDDING_BASE_URL or base_url,
                    "api_key": self.settings.OPENAI_API_KEY,
                }, metadata={
                    "provider": self.settings.EMBEDDING_PROVIDER,
                    "owned_by": self.settings.EMBEDDING_OWNED_BY,
                }
            )
        
        
        self._initialized = True
        
        self.register_chat_model(
            model_id=self._default_chat_model,
            config={
                "model": self._default_chat_model,
                "model_provider": self.settings.MODEL_PROVIDER,
                "base_url": self.settings.MODEL_BASE_URL,
                "api_key": self.settings.OPENAI_API_KEY,
                "temperature": self.settings.MODEL_TEMPERATURE,
                "max_tokens": self.settings.MODEL_MAX_OUTPUT_TOKENS,
            },
            metadata={
                "provider": self.settings.MODEL_PROVIDER,
                "owned_by": self.settings.MODEL_OWNED_BY,
                "context_window": self.settings.MODEL_CONTEXT_WINDOW,
                "completion_reserve": self.settings.MODEL_COMPLETION_RESERVE,
            },
        )

        if self._default_embedding_model:
            self.register_embedding_model(
                model_id=self._default_embedding_model,
                config={
                    "model": self._default_embedding_model,
                    "base_url": self.settings.EMBEDDING_BASE_URL,
                    "api_key": self.settings.OPENAI_API_KEY,
                },
                metadata={
                    "provider": self.settings.EMBEDDING_PROVIDER,
                    "owned_by": self.settings.EMBEDDING_OWNED_BY,
                },
            )

        self._initialized = True

    async def shutdown(self) -> None:
        self._initialized = False


    def register_chat_model(self, model_id: str, config: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> None:
        self._chat_models[model_id] = {
            "config": _clean_config(config),
            "metadata": metadata or {},
        }

    def register_embedding_model(self, model_id: str, config: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> None:
        self._embedding_models[model_id] = {
            "config": _clean_config(config),
            "metadata": metadata or {},
        }


    def get_chat_model(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        key = model_id or self._default_chat_model
        entry = self._chat_models.get(key)
        if not entry:
            raise ValueError(f"Chat model '{key}' not registered")
        return entry["config"].copy()

    def get_chat_model_metadata(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        key = model_id or self._default_chat_model
        entry = self._chat_models.get(key)
        if not entry:
            raise ValueError(f"Chat model '{key}' not registered")
        return entry.get("metadata", {}).copy()

    def get_embedding_model(self, model_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        key = model_id or self._default_embedding_model
        if key is None:
            return None
        entry = self._embedding_models.get(key)
        if not entry:
            raise ValueError(f"Embedding model '{key}' not registered")
        return entry["config"].copy()

    def get_embedding_metadata(self, model_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        key = model_id or self._default_embedding_model
        if key is None:
            return None
        entry = self._embedding_models.get(key)
        if not entry:
            raise ValueError(f"Embedding model '{key}' not registered")
        return entry.get("metadata", {}).copy()

    def list_chat_models(self) -> List[Dict[str, Any]]:
        data: List[Dict[str, Any]] = []
        for model_id, entry in self._chat_models.items():
            meta = entry.get("metadata", {})
            data.append(
                {
                    "id": model_id,
                    "object": "model",
                    "owned_by": meta.get("owned_by", meta.get("provider", "custom")),
                    "metadata": meta,
                }
            )
        return data

    def get_model_name(self) -> str:
        return self._default_chat_model

    def get_context_window(self, model_id: Optional[str] = None) -> int:
        meta = self.get_chat_model_metadata(model_id)
        return meta.get("context_window", self.settings.MODEL_CONTEXT_WINDOW)

    def get_completion_reserve(self, model_id: Optional[str] = None) -> int:
        meta = self.get_chat_model_metadata(model_id)
        return meta.get("completion_reserve", self.settings.MODEL_COMPLETION_RESERVE)

    def get_retrieval_top_k(self) -> int:
        return self.settings.RETRIEVAL_TOP_K

    def is_initialized(self) -> bool:
        return self._initialized


# Module-level singleton storage for the model registry
_model_registry: Optional[ModelRegistry] = None

# Backwards-compat alias if any code referenced the old name
model_registry = _model_registry

def init_model_registry(settings: Settings) -> ModelRegistry:
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry(settings)
    return _model_registry

def get_model_registry() -> ModelRegistry:
    if _model_registry is None:
        raise RuntimeError("Model registry has not been initialized yet")
    return _model_registry
