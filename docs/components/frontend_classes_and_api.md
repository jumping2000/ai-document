# Frontend — Classi, Store e API

## Componenti principali (src/pages/)
- **WorkflowMonitorPage**: pagina principale per il monitoraggio dei workflow, mostra stato, avanzamento, documenti e report qualità.

## Store (src/stores/)
- **workflowStore.ts**: stato globale dei workflow, gestisce lista, stato corrente, aggiornamenti da API e WebSocket.

## Hook custom (src/hooks/)
- **useWorkflowStream.ts**: gestisce la connessione WebSocket per ricevere eventi in tempo reale dal backend (state_change, agent_start, agent_done, ecc.).

## Tipi (src/types/)
- **index.ts**: definizioni TypeScript condivise per workflow, documenti, eventi, ecc.

---

# API usate dal frontend

## REST API
- **POST /api/v1/workflow/start**: avvia workflow (usata per invio dati form)
- **GET /api/v1/workflow/{id}**: recupera stato e dettagli
- **POST /api/v1/workflow/{id}/approve**: invia approvazione
- **POST /api/v1/workflow/{id}/retry**: richiede retry
- **GET /api/v1/workflow/{id}/documents**: scarica documenti generati
- **GET /api/v1/workflow/{id}/quality-report**: visualizza report qualità

## WebSocket
- **/ws/workflow/{id}**: riceve eventi live per aggiornare UI in tempo reale

---

# Flusso tipico
1. L’utente avvia un workflow tramite form (POST /api/v1/workflow/start)
2. Il frontend si sottoscrive agli eventi live via WebSocket
3. Aggiorna lo stato UI in base agli eventi ricevuti (store + hooks)
4. Visualizza documenti e report generati

---

Per dettagli su props, stato e logica, consultare i file React/TypeScript nelle cartelle src/pages, src/stores, src/hooks, src/types.