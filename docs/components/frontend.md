# Frontend Components

## Overview
Il frontend è una SPA (Single Page Application) sviluppata in React + TypeScript, progettata per interagire in tempo reale con il backend tramite REST API e WebSocket.

### Struttura principale
- **src/**: codice sorgente
  - **main.tsx**: entrypoint React
  - **pages/**: pagine principali (es. WorkflowMonitor)
  - **hooks/**: custom React hooks (es. useWorkflowStream)
  - **stores/**: stato globale (es. workflowStore)
  - **types/**: definizioni TypeScript
  - **index.css**: stili globali (Tailwind)

### Componenti chiave
- **React**: framework UI
- **Vite**: dev server e build tool
- **Tailwind CSS**: utility-first CSS
- **WebSocket**: aggiornamenti in tempo reale
- **REST API**: comunicazione con backend

### Flusso tipico
1. Login/Accesso (se previsto)
2. Navigazione e selezione workflow
3. Invio dati e ricezione stato via API
4. Aggiornamento UI in tempo reale via WebSocket
5. Visualizzazione documenti generati e report

---

## Dettaglio cartelle

- **src/pages/**: pagine React
- **src/hooks/**: hooks custom per stream e API
- **src/stores/**: stato globale (es. Zustand)
- **src/types/**: tipi TypeScript condivisi
- **src/index.css**: stili globali

---

## Dipendenze principali
- React, Vite, Tailwind CSS, Zustand, TypeScript, Axios, motion/react, WebSocket
