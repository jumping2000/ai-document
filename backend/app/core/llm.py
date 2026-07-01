"""
LLM factory: returns an agno-compatible model instance based on settings.
"""

from typing import Any

from app.core.config import settings


def extract_metrics(response: Any) -> dict[str, int]:
    """Extract token counts from an Agno RunOutput, with char-based fallback."""
    tokens: dict[str, int] = {}
    # 1) Try RunMetrics
    if hasattr(response, "metrics") and response.metrics:
        m = response.metrics
        inp = getattr(m, "input_tokens", 0) or 0
        out = getattr(m, "output_tokens", 0) or 0
        if inp > 0 or out > 0:
            tokens = {
                "input": inp,
                "output": out,
                "total": getattr(m, "total_tokens", 0) or inp + out,
            }
    # 2) Try per-message metrics (some providers populate these)
    if not tokens and hasattr(response, "messages"):
        inp = out = 0
        for msg in response.messages:
            if hasattr(msg, "metrics") and msg.metrics:
                inp += getattr(msg.metrics, "input_tokens", 0) or 0
                out += getattr(msg.metrics, "output_tokens", 0) or 0
        if inp > 0 or out > 0:
            tokens = {"input": inp, "output": out, "total": inp + out}
    # 3) Fallback: estimate from content length (~3 chars/token for Italian)
    if not tokens and hasattr(response, "content") and response.content:
        out_est = max(1, len(str(response.content)) // 3)
        tokens = {"input": 0, "output": out_est, "total": out_est}
    return tokens


def get_model_adapter(max_tokens: int | None = None) -> Any:
    provider = settings.default_ai_provider.lower()
    if max_tokens is None:
        max_tokens = settings.max_tokens

    if provider == "openai":
        try:
            from agno.models.openai import OpenAIChat

            return OpenAIChat(
                id=settings.default_ai_model, api_key=settings.openai_api_key, max_tokens=max_tokens
            )
        except Exception as exc:  # pragma: no cover - import/runtime errors
            raise ImportError("OpenAI model support is not available: " + str(exc))

    if provider == "anthropic":
        try:
            from agno.models.anthropic.claude import Claude

            return Claude(
                id=settings.default_ai_model,
                api_key=settings.anthropic_api_key,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # pragma: no cover
            raise ImportError("Anthropic model support is not available: " + str(exc))

    if provider == "openrouter":
        try:
            from agno.models.openrouter.openrouter import OpenRouter

            return OpenRouter(
                id=settings.default_ai_model,
                api_key=settings.openrouter_api_key,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # pragma: no cover
            raise ImportError("OpenRouter model support is not available: " + str(exc))

    if provider == "ollama":
        try:
            from agno.models.ollama.chat import Ollama

            return Ollama(
                id=settings.default_ai_model,
                host=settings.ollama_url,
                api_key=settings.ollama_api_key,
            )
        except Exception as exc:  # pragma: no cover
            raise ImportError("Ollama model support is not available: " + str(exc))

    raise ValueError(f"Unsupported LLM provider: {settings.default_ai_provider}")
