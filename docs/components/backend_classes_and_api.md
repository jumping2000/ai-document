# Backend Python Classes — Dettaglio

## Agenti (app/agents/)
- **LeadWriterAgent**: Genera documenti finali a partire da requisiti arricchiti. Usa LLM tramite Agno.
- **OrchestratorAgent**: Coordina il workflow, gestisce stati e transizioni, chiama altri agenti.
- **ProcurementAgent**: Arricchisce i requisiti con normative, best practice, standard.
- **QualityAgent**: Valuta la qualità del documento generato, produce report e punteggi.
- **RequirementAgent**: Raccoglie e struttura i requisiti utente.

## Skill (app/skills/)
- **ExportSkill**: Esporta documenti in vari formati (docx, pdf, markdown).
- **RetrievalSkill**: Recupera informazioni da fonti esterne (RAG/MCP).
- **ValidationSkill**: Valida la correttezza e completezza dei dati.

## Core/Config
- **Settings**: Configurazione centralizzata (env, chiavi, modelli, DB, cache, provider LLM).

## Database (app/db/)
- **models.py**: Definisce i modelli ORM (es. Workflow, Document, User).
- **session.py**: Gestione sessioni DB asincrone.

## Workflow
- **WorkflowRunner**: Esegue e monitora i workflow multi-agente.
- **StateMachine**: Gestisce stati, trigger e transizioni del workflow.

---

# API Reference (REST & WebSocket)

## REST API principali
- **POST /api/v1/workflow/start**: Avvia un nuovo workflow documentale
- **GET /api/v1/workflow/{id}**: Stato e dettagli workflow
- **POST /api/v1/workflow/{id}/approve**: Approvazione umana
- **POST /api/v1/workflow/{id}/retry**: Retry workflow fallito
- **GET /api/v1/workflow/{id}/documents**: Elenco documenti generati
- **GET /api/v1/workflow/{id}/quality-report**: Report qualità
- **GET /health**: Healthcheck backend

## WebSocket
- **/ws/workflow/{id}**: Stream eventi live (state_change, agent_start, agent_done, quality_report, completed, failed, heartbeat)

---

Per ogni endpoint, vedere docstring e validatori in app/api/routes/workflow.py e app/api/websocket/stream.py.

Per dettagli su parametri e modelli, consultare i file Pydantic nelle stesse cartelle.