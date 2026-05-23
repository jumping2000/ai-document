# Backend Components

## Overview
Il backend è una piattaforma Python basata su FastAPI, strutturata per supportare workflow multi-agente, generazione documentale, validazione e integrazione con servizi esterni (OpenAI, Anthropic, MCP, database, cache, ecc.).

### Struttura principale
- **app/**: codice applicativo principale
  - **main.py**: entrypoint FastAPI
  - **core/**: configurazione, settings, logging
  - **api/**: router REST e websocket
  - **agents/**: agenti logici (lead_writer, orchestrator, procurement, quality, requirement)
  - **skills/**: skill modulari (export, retrieval, validation)
  - **db/**: modelli, sessioni, migrazioni
  - **mcp/**: client per external RAG/KB
  - **templates/**: template Jinja2 per i documenti
  - **workflows/**: runner, state machine
  - **tests/**: test suite

### Componenti chiave
- **FastAPI**: framework web asincrono
- **Agno**: orchestrazione agenti LLM
- **SQLAlchemy/AsyncPG**: database layer
- **Redis**: cache
- **Alembic**: migrazioni DB
- **Structlog**: logging strutturato
- **OpenAI/Anthropic**: provider LLM
- **MCP**: retrieval aumentato (RAG)

### Flusso tipico
1. Ricezione richiesta via REST/WebSocket
2. Validazione e parsing input
3. Attivazione workflow multi-agente
4. Generazione, validazione, arricchimento documenti
5. Persistenza su DB e storage
6. Notifica frontend via websocket

---

## Dettaglio cartelle

- **app/core/**: settings, config, logging
- **app/api/routes/**: endpoint REST
- **app/api/websocket/**: stream eventi
- **app/agents/**: agenti LLM (ognuno con logica e modello)
- **app/skills/**: skill riusabili (export, retrieval, validation)
- **app/db/**: modelli ORM, sessioni, migrazioni
- **app/mcp/**: client MCP (RAG)
- **app/templates/**: template Jinja2
- **app/workflows/**: runner, state machine
- **app/tests/**: test automatici

---

## Dipendenze principali
- FastAPI, SQLAlchemy, Alembic, Redis, Pydantic, Agno, OpenAI, Anthropic, Structlog, Jinja2, Pytest
