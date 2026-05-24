# Change Request: Supporto provider LLM aggiuntivi — OpenRouter & Ollama

**Autore:** (tu)
**Data:** 2026-05-23
**Destinatari:** backend team, architettura, sicurezza

## Sintesi
Aggiungere supporto per i provider LLM OpenRouter e Ollama oltre agli attuali OpenAI/Anthropic. L'obiettivo è aumentare resilienza, flessibilità di costi e possibilità di usare LLM on‑premises (Ollama) o broker multi-provider (OpenRouter).

## Motivazione
- Ridurre lock-in verso singolo provider.
- Permettere deployment on‑premise senza chiavi esterne per casi sensibili (Ollama).
- Abilitare failover e routing verso provider più economici tramite OpenRouter.

## Ambito
- Backend (FastAPI) — estrarre/astrarre l'accesso all'LLM e aggiungere adapter per OpenRouter e Ollama.
- Config/Env: nuove variabili e aggiornamento `.env.example` e `docker-compose.yml` per Ollama (se necessario).
- Tests: unit + integrazione (mock client) per provider multipli.
- Documentazione: aggiornare README e docs/architecture.

## Requisiti
- Selezione provider via `DEFAULT_AI_PROVIDER` (`openai|anthropic|openrouter|ollama`).
- Parametri provider nel `Settings` (chiavi, base_url, eventuale socket/path per Ollama).
- Adapter pluggable che espongono interfaccia uniforme usata da `agno.models` o da un wrapper interno.
- Non rompere compatibilità con uso esistente (default `openai`).

## Proposta di implementazione (step tecnici)

1. **Config — `app/core/config.py`**
   - Aggiungere variabili e valori di default:
     ```py
     # AI Models
     openai_api_key: str = ""
     anthropic_api_key: str = ""
     openrouter_api_key: str = ""
     openrouter_base_url: str = "https://api.openrouter.ai"
     ollama_url: str = "http://localhost:11434"  # esempio per Ollama local
     default_ai_provider: Literal["openai","anthropic","openrouter","ollama"] = "openai"
     default_ai_model: str = "gpt-4o"
     ```
   - Aggiornare `env_file` / `.env.example` con le nuove variabili.

2. **Aggiungere un factory adapter — `app/core/llm.py`**
   - Implementare una piccola factory che restituisce l'oggetto modello compatibile con `agno` Agent (o un wrapper che implementa `arun()`):
     ```py
     from app.core.config import settings
     from agno.models.openai import OpenAIChat
     # ipotetici wrappers
     from .llm_adapters import OpenRouterChat, OllamaChat

     def get_model_adapter() -> Any:
         provider = settings.default_ai_provider
         if provider == "openai":
             return OpenAIChat(id=settings.default_ai_model, api_key=settings.openai_api_key)
         if provider == "anthropic":
             return AnthropicChat(id=settings.default_ai_model, api_key=settings.anthropic_api_key)
         if provider == "openrouter":
             return OpenRouterChat(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key, model=settings.default_ai_model)
         if provider == "ollama":
             return OllamaChat(url=settings.ollama_url, model=settings.default_ai_model)
         raise ValueError("Unsupported LLM provider")
     ```
   - `OpenRouterChat` e `OllamaChat` sono adapter che espongono la stessa API che `agno` si aspetta (o un wrapper che fornisce `arun()`/`run()` asincrono).

3. **Adapter implementations — `app/core/llm_adapters.py`**
   - `OpenRouterChat` (HTTP): invia richieste REST conformi a OpenRouter API (chiave + modello + input). Gestire timeout, retry e mapping di parametri.
   - `OllamaChat` (HTTP/local): chiamate al server Ollama (es. `POST /api/llm` o endpoint appropriato). Supportare streaming opzionale.
   - Fornire implementazioni minimali per testing e fallback in modalità mocking.

4. **Integrazione con agenti**
   - Sostituire `model=OpenAIChat(id=settings.default_ai_model)` negli agenti con `model=get_model_adapter()` oppure usare `model=AdapterWrapper(get_model_adapter())` se `agno` richiede tipi specifici.
   - Esempio (in `lead_writer/agent.py`):
     ```py
     from app.core.llm import get_model_adapter
     self._agno = Agent(
         ...,
         model=get_model_adapter(),
     )
     ```

5. **Aggiornamento `.env.example` e `docker-compose.yml`**
   - Aggiungere variabili: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OLLAMA_URL`.
   - Se si desidera eseguire Ollama in Docker, aggiungere servizio opzionale `ollama`/config (documentare come attivarlo con profilo `dev`).

6. **Testing**
   - Aggiungere unit tests per `llm_adapters` con mocking di HTTP.
   - Test di integrazione end‑to‑end con `OLLAMA_URL` puntato a un mock server (es. `scripts/ollama_stub.py`) e con OpenRouter mock.

7. **Documentazione**
   - Aggiornare `README.md` Quick Start con istruzioni su come abilitare `OPENROUTER` o `OLLAMA`.
   - Aggiornare `docs/architecture` e `docs/components` per documentare provider aggiuntivi.

## Rollout e compatibilità
- Default provider rimane `openai` — niente interruzioni.
- Feature flags: abilitare `openrouter`/`ollama` solo quando variabili rilevanti sono presenti.

## Sicurezza e governance
- Non committare chiavi su repo; usare `.env` o segreti CI/CD.
- Se si usa Ollama on‑premise, validare che il server sia isolato e aggiornato.

## Esempi `.env` aggiuntivi
```env
# OpenRouter
OPENROUTER_API_KEY=or-...
OPENROUTER_BASE_URL=https://api.openrouter.ai
DEFAULT_AI_PROVIDER=openrouter

# Ollama (server locale)
OLLAMA_URL=http://ollama.local:11434
DEFAULT_AI_PROVIDER=ollama
```

## Stima di lavoro
- Implementazione factory + adapters: 1–2 giorni
- Aggiornamento agenti e test: 1 giorno
- Documentazione e deploy examples: 0.5 giorno

## Checklist di merge
- [ ] `app/core/llm.py` e `app/core/llm_adapters.py` implementati
- [ ] `.env.example` aggiornato
- [ ] Tests unit e integrazione aggiunti e passanti
- [ ] README e docs aggiornati
- [ ] Code review e approvazione sicurezza per uso on‑premise

---

Se vuoi, applico i cambiamenti base automaticamente:
- creo `app/core/llm.py` (factory) e `app/core/llm_adapters.py` con adapter minimal (HTTP clients),
- aggiorno `app/core/config.py` per aggiungere le nuove variabili,
- aggiorno `.env.example` e `docker-compose.yml` (se richiesto).

Dimmi se procedo con l'implementazione automatica.