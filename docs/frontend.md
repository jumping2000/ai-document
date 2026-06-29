# Frontend Components

## Overview

Single Page Application (SPA) built with React 18, TypeScript, Vite, Tailwind CSS 3.4, and Zustand 5. Provides real-time workflow monitoring via WebSocket, MCP connection management, template configuration, and document export.

**Entrypoint:** `frontend/src/main.tsx`
**Dev server:** `npm run dev` → Vite on port 5173

---

## Project Structure

```
frontend/
├── index.html              # HTML entrypoint
├── package.json             # Dependencies & scripts
├── vite.config.ts           # Vite config (port 5173, proxy to :8001)
├── tsconfig.json            # TypeScript strict config
├── tailwind.config.js       # Tailwind configuration
├── postcss.config.js        # PostCSS with Tailwind plugin
├── nginx.conf               # Production Nginx config (HTTP Basic Auth)
├── Dockerfile               # Multi-stage (Node 20 build → Nginx 1.27 serve)
├── src/
│   ├── main.tsx             # React entrypoint
│   ├── index.css            # Global styles (Tailwind + CSS variables)
│   ├── env.d.ts             # Vite client type declarations
│   ├── pages/
│   │   ├── WorkflowMonitor.tsx  # Main app page (5 tabs)
│   │   ├── MCPSettings.tsx      # MCP connection management
│   │   └── TemplateSettings.tsx # Template configuration
│   ├── components/
│   │   ├── ThemeSwitcher.tsx    # Light/Dark/System toggle
│   │   └── LanguageSwitcher.tsx # IT/EN toggle
│   ├── contexts/
│   │   └── ThemeContext.tsx     # Theme state (localStorage)
│   ├── hooks/
│   │   └── useWorkflowStream.ts # WebSocket connection hook
│   ├── stores/
│   │   └── workflowStore.ts     # Zustand global state
│   ├── i18n/
│   │   ├── LanguageContext.tsx  # Locale state
│   │   └── translations.ts     # IT + EN translations (100+ keys)
│   └── types/
│       └── index.ts             # All TypeScript interfaces
└── public/                  # Static assets
```

---

## Build Configuration (`vite.config.ts`)

```typescript
Port: 5173
Proxy:
  /api → http://localhost:8001    (REST API)
  /ws  → ws://localhost:8001     (WebSocket)
Path alias: @ → ./src
```

---

## Dependencies

| Category | Packages |
|----------|----------|
| UI Framework | react 18.3, react-dom, react-router-dom 6.28 |
| State | zustand 5.0, @tanstack/react-query 5.62 |
| Animations | framer-motion 11.13 |
| Icons | lucide-react 0.468 |
| Markdown | react-markdown, remark-gfm |
| Styling | tailwindcss 3.4, @tailwindcss/typography |
| Build | typescript, vite, @vitejs/plugin-react |

---

## Global State (`src/stores/workflowStore.ts`)

Zustand store with combined state + actions in a single slice:

```typescript
interface WorkflowStore {
  // State
  activeWorkflow: Workflow | null
  agentStatuses: Record<AgentName, AgentStatus>
  qualityReport: QualityReport | null
  validationResult: ValidationResult | null
  documentContent: string           // markdown
  events: WorkflowEvent[]           // sliding window, max 100
  isStreaming: boolean
  workflows: Workflow[]

  // Mutations
  setActiveWorkflow(wf: Workflow)
  updateWorkflowState(state: WorkflowStateEnum)
  setAgentRunning(agent: AgentName)
  setAgentDone(agent: AgentName, duration_ms: number)
  setQualityReport(report: QualityReport)
  setValidationResult(result: ValidationResult)
  setDocumentContent(content: string)
  pushEvent(event: WorkflowEvent)
  setStreaming(v: boolean)
  setWorkflows(wfs: Workflow[])
  reset()
}
```

Agent status types: `'idle' | 'running' | 'done' | 'error'`.

---

## WebSocket Hook (`src/hooks/useWorkflowStream.ts`)

Connects to `ws://host/ws/workflow/{workflowId}` and dispatches events to the Zustand store:

| Incoming Event | Store Action |
|---------------|-------------|
| `state_change` | `updateWorkflowState(state)` |
| `agent_start` | `setAgentRunning(agent)` |
| `agent_done` | `setAgentDone(agent, duration_ms)` |
| `quality_report` | `setQualityReport(data)` |
| `pending_approval` | (no store action — frontend shows ApprovalPanel based on state) |
| `validation_result` / `validation_failed` | `setValidationResult(data)` |
| `completed` | `setDocumentContent(data.content)`, `setStreaming(false)` |
| `failed` | `setStreaming(false)` |

Returns `{ isConnected, error }` and auto-reconnects on close.

---

## Pages

### WorkflowMonitor (`src/pages/WorkflowMonitor.tsx`)

Main application page with 5 tabs:

#### Tab 1: Form (New Document)
- **Document Type:** 3-button selector (Capitolato | Requisiti | Documento)
- **Project Title:** text input
- **Knowledge Source:** dropdown (MCP connections or "None")
- **Description:** textarea (min 20 chars)

API call: `POST /api/v1/workflow/start` with `{document_type, title, raw_description, form_data, mcp_connection_id?}`
Response: `{workflow_id, state}` — sets `activeWorkflowId`, navigates to Monitor tab.

#### Tab 2: Monitor (Live Execution)

**Left Column (2/3):**
1. **StateRail:** 9-step vertical progress indicator (INIT → ... → PENDING_APPROVAL → COMPLETED)
   - Completed: filled green circle ✓
   - Active: pulsing indigo-500 border
   - Pending Approval: amber #f59e0b (awaiting human action)
   - Pending: gray outline
2. **Agent Grid:** 5 cards (orchestrator, requirement, procurement, lead_writer, quality)
   - Animated border glow when running (framer-motion)
   - Shows duration when done
   - Status: idle/running/done/error
3. **Quality Gauge:** Circular SVG progress (0–100%)
   - Color: green (passed), orange (>50%), red (<50%)
   - Badge: "✓ APPROVATO" | "✗ REVISIONE"
4. **Quality Issues:** First 3 issues by severity
5. **Approval Panel** (shown when state is `PENDING_APPROVAL`):
   - Amber-colored card with clock icon
   - Quality score + issues/suggestions counts
   - "✓ APPROVA" / "✗ RESPINGI" buttons
   - Optional comment textarea
   - Calls `POST /api/v1/workflow/{id}/approve`

**Right Column (1/3):**
- **Event Log:** Last 20 events, reverse-chronological
  - Timestamp + event type badge + data snippet
  - Nested details for validation/failed events

**Bottom:** Action buttons (if completed/failed): "View Document", "New Workflow"

#### Tab 3: Document (Markdown Viewer & Export)

- Content rendered via `ReactMarkdown` with `remarkGfm` plugin
- Tailwind prose styling (inverted for dark mode)
- Export buttons: DOCX and PDF
  - `POST /api/v1/workflow/{id}/export/{format}` → `{download_url}`
  - Fetch blob → create `<a>` with ObjectURL → trigger download

#### Tab 4: Knowledge (MCP Settings)

Embeds `<MCPSettings />` component directly.

#### Tab 5: Templates

Embeds `<TemplateSettings />` component directly.

**Header:** Title + subtitle, live indicator (blinking "LIVE" badge when `isStreaming`), workflow ID (truncated), Theme & Language switchers.

---

### MCPSettings (`src/pages/MCPSettings.tsx`)

MCP connection management UI.

**API interactions:**
- `GET /api/v1/mcp/connections` → list connections
- `POST /api/v1/mcp/connections` → create + discover
- `POST /api/v1/mcp/connections/test` → test without saving
- `POST /api/v1/mcp/connections/{id}/refresh` → re-discover
- `DELETE /api/v1/mcp/connections/{id}` → delete

**UI Structure:**
1. **Header:** "Knowledge Sources (MCP)" + "Add Connection" button
2. **Create Form Modal** (animated):
   - Inputs: name*, url*, transport (dropdown), api_key (password + eye toggle), description (textarea)
   - "Test & Discover KBs" button → fetches available KBs
   - KB selector dropdown (appears after test)
   - Cancel/Save buttons
3. **Connections List:**
   - Expandable cards with status icon, name, URL
   - Tool/resource/prompt counts
   - Refresh/delete action buttons
   - Expanded view: description, tools grid, resources list, prompts, KBs
   - Status colors: emerald (connected), red (error), zinc (default)

---

### TemplateSettings (`src/pages/TemplateSettings.tsx`)

Template configuration UI for document types.

**API interactions:**
- `GET /api/v1/templates/` → list types
- `GET /api/v1/templates/{id}/config` → get config
- `PUT /api/v1/templates/{id}/config` → save changes
- `POST /api/v1/templates/{id}/reset` → revert to defaults
- `POST /api/v1/templates/{id}/validate-preview` → test validation

**Panels (expandable):**
1. **Sections:** Toggle required/not required for each section
2. **Quality Checks:** Enable/disable individual checks
3. **Required Fields:** Add/edit/remove fields (path, label, min_items)
4. **Validation Preview:** JSON textarea + "Test" button → shows valid/invalid + confidence + issues/warnings
5. **SLA Rules:** Free-form metrics list ({metric, target, note}[]). Obligatory for capitolato and requisiti.

**Message display:** Success (green) or Error (red) alerts.

---

## Styling (`src/index.css`)

**CSS Variables (Light Theme):**
```css
--color-brand: #6366f1          /* Indigo-500 */
--color-brand-dim: rgba(99,102,241,0.15)
--color-bg: #ffffff
--color-bg-secondary: #f4f4f5
--color-text: #18181b
--color-border: #e4e4e7
```

**Dark Theme:** `html.dark` selector toggles all variables to dark values.

**Typography:** IBM Plex Mono (monospace aesthetic), box-sizing: border-box.
**Scrollbar:** 4px custom styling, 2px radius.
**Prose:** Tailwind Typography customized for light/dark modes with brand accent colors.

---

## UI Components

### ThemeSwitcher (`src/components/ThemeSwitcher.tsx`)
- 3 options: ☀️ Light, 🌙 Dark, 🖥️ System
- Persisted to `localStorage` key `'ai-doc-theme'`
- Uses `matchMedia('(prefers-color-scheme: dark)')` for system detection
- Toggles `'light'`/`'dark'` classes on `document.documentElement`

### LanguageSwitcher (`src/components/LanguageSwitcher.tsx`)
- 2 languages: 🇮🇹 Italiano, 🇬🇧 English
- Persisted to `localStorage` key `'ai-doc-locale'`
- Click-outside detection for dropdown close

---

## i18n (`src/i18n/`)

### LanguageContext (`LanguageContext.tsx`)
- `locale: 'it' | 'en'` (default: `'it'`)
- `setLocale()`, `t(key: string) → string` (with fallback to key)

### Translations (`translations.ts`)
100+ keys across namespaces:
- `app` — app title, description, version
- `nav` — tab labels, form, monitor, document, knowledge, templates
- `form` — new document, title, description, type selector, submit
- `state` — workflow states (INIT, BRIEFING, ..., PENDING_APPROVAL)
- `monitor` — live status, agent cards, event log
- `agent` — agent names (orchestrator, requirement, etc.)
- `quality` — quality report labels, score, issues
- `approval` — approval panel title, approve/reject buttons, comment, status messages
- `document` — document viewer, export, download
- `mcp` — 24+ keys for connection management
- `template` — 30+ keys for configuration
- `theme`, `lang`, `general` — UI controls

---

## TypeScript Types (`src/types/index.ts`)

### Workflow & States
```typescript
WorkflowStateEnum = 'INIT' | 'BRIEFING' | 'ENRICHMENT' | 'VALIDATION' | 'WRITING' | 'QUALITY_ANALYSIS' | 'PENDING_APPROVAL' | 'COMPLETED' | 'FAILED'
DocumentType = 'capitolato' | 'requisiti' | 'documento'
Workflow { workflow_id, state, document_type, title, retry_count, quality_score, created_at, updated_at }
```

### WebSocket Events
```typescript
WorkflowEventType = 'state_change' | 'agent_start' | 'agent_done' | 'quality_report' | 'validation_result' | 'validation_failed' | 'completed' | 'failed' | 'heartbeat'
WorkflowEvent { event: WorkflowEventType, data: Record<string, unknown> }
```

### Quality
```typescript
QualityReport { passed, score (0-1), dimension_scores, issues, missing_sections, suggestions, summary }
QualityIssue { id, severity: 'CRITICAL'|'MAJOR'|'MINOR', section, description, suggestion }
```

### Validation
```typescript
ValidationResult { valid, confidence (0-1), missing_fields[], issues[], warnings[] }
```

### Agents
```typescript
AgentName = 'requirement' | 'procurement' | 'lead_writer' | 'quality' | 'orchestrator'
AgentStatus { name, status: 'idle'|'running'|'done'|'error', duration_ms, started_at }
```

### MCP
```typescript
MCPConnection { id, name, url, transport, is_active, health_status, default_kb_id, discovered_tools, discovered_resources, discovered_prompts, discovered_kbs }
MCPTool { name, description, input_schema? }
MCPResource { uri, name, description, mime_type? }
MCPPrompt { name, description, arguments[] }
MCPKnowledgeBase { id, name, documents?, chunks? }
```

---

## Production Setup

### Nginx (`frontend/nginx.conf`)
- Port 80, root `/usr/share/nginx/html`
- HTTP Basic Auth via `.htpasswd`
- SPA fallback: `try_files $uri $uri/ /index.html`
- `/api/` → proxy to `http://backend:8001`
- `/ws/` → WebSocket upgrade proxy to `http://backend:8001`
- Gzip enabled for text/json/js

### Dockerfile
- Stage 1 (builder): Node 20, `npm ci` or `npm install`, `npm run build`
- Stage 2 (runtime): Nginx 1.27 serving `/app/dist`
- Health check: `wget http://localhost:80/`

