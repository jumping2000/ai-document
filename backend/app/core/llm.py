"""
LLM factory: returns an agno-compatible model instance based on settings.
"""
from typing import Any

from app.core.config import settings


def get_model_adapter() -> Any:
    provider = settings.default_ai_provider.lower()

    if provider == "openai":
        try:
            from agno.models.openai import OpenAIChat

            return OpenAIChat(id=settings.default_ai_model, api_key=settings.openai_api_key)
        except Exception as exc:  # pragma: no cover - import/runtime errors
            raise ImportError("OpenAI model support is not available: " + str(exc))

    if provider == "anthropic":
        try:
            from agno.models.anthropic.claude import Claude

            return Claude(id=settings.default_ai_model, api_key=settings.anthropic_api_key)
        except Exception as exc:  # pragma: no cover
            raise ImportError("Anthropic model support is not available: " + str(exc))

    if provider == "openrouter":
        try:
            from agno.models.openrouter.openrouter import OpenRouter

            return OpenRouter(id=settings.default_ai_model, api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)
        except Exception as exc:  # pragma: no cover
            raise ImportError("OpenRouter model support is not available: " + str(exc))

    if provider == "ollama":
        try:
            from agno.models.ollama.chat import Ollama

            return Ollama(id=settings.default_ai_model, host=settings.ollama_url, api_key=settings.ollama_api_key)
        except Exception as exc:  # pragma: no cover
            raise ImportError("Ollama model support is not available: " + str(exc))

    raise ValueError(f"Unsupported LLM provider: {settings.default_ai_provider}")
