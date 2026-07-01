// ── Workflow ──────────────────────────────────────────────────────────────────

export type DocumentType = 'capitolato' | 'requisiti' | 'documento';

export type WorkflowStateEnum =
  | 'INIT'
  | 'BRIEFING'
  | 'ENRICHMENT'
  | 'VALIDATION'
  | 'WRITING'
  | 'QUALITY_ANALYSIS'
  | 'PENDING_APPROVAL'
  | 'COMPLETED'
  | 'FAILED';

export interface Workflow {
  workflow_id: string;
  state: WorkflowStateEnum;
  document_type: DocumentType;
  title: string;
  retry_count: number;
  quality_score: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface StartWorkflowRequest {
  document_type: DocumentType;
  title: string;
  raw_description: string;
  form_data: Record<string, unknown>;
}

// ── SSE Events ────────────────────────────────────────────────────────────────

export type WorkflowEventType =
  | 'state_change'
  | 'agent_start'
  | 'agent_done'
  | 'quality_report'
  | 'validation_result'
  | 'validation_failed'
  | 'pending_approval'
  | 'completed'
  | 'failed'
  | 'heartbeat';

export interface WorkflowEvent {
  event: WorkflowEventType;
  data: Record<string, unknown>;
}

// ── Agents ────────────────────────────────────────────────────────────────────

export type AgentName = 'requirement' | 'procurement' | 'lead_writer' | 'quality';

export interface AgentStatus {
  name: AgentName;
  status: 'idle' | 'running' | 'done' | 'error';
  duration_ms?: number;
  started_at?: number;
  tokens?: { input: number; output: number; total: number };
}

// ── Quality Report ────────────────────────────────────────────────────────────

export interface QualityIssue {
  id: string;
  severity: 'CRITICAL' | 'MAJOR' | 'MINOR';
  section: string;
  description: string;
  suggestion: string;
}

export interface QualityReport {
  passed: boolean;
  score: number;
  dimension_scores: Record<string, number>;
  issues: QualityIssue[];
  missing_sections: string[];
  suggestions: string[];
  summary: string;
}

// ── Validation Result ──────────────────────────────────────────────────────

export interface ValidationResult {
  valid: boolean;
  confidence: number;
  missing_fields: string[];
  issues: string[];
  warnings: string[];
}

// ── Document ──────────────────────────────────────────────────────────────────

export interface Document {
  id: string;
  workflow_id: string;
  name: string;
  format: 'markdown' | 'docx' | 'pdf';
  content_md: string;
  file_path: string;
  version: number;
  created_at: string;
}

// ── MCP Connection ────────────────────────────────────────────────────────────

export interface MCPConnection {
  id: string;
  name: string;
  description: string | null;
  url: string;
  transport: string;
  is_active: boolean;
  health_status: string;
  last_health_check: string | null;
  default_kb_id: string | null;
  discovered_tools: MCPTool[];
  discovered_resources: MCPResource[];
  discovered_prompts: MCPPrompt[];
  discovered_kbs: MCPKnowledgeBase[];
  created_at: string;
  updated_at: string;
}

export interface MCPKnowledgeBase {
  id: string;
  name: string;
  documents?: number;
  chunks?: number;
}

export interface MCPTool {
  name: string;
  description: string;
  input_schema?: Record<string, unknown>;
}

export interface MCPResource {
  uri: string;
  name: string;
  description: string;
  mime_type?: string;
}

export interface MCPPrompt {
  name: string;
  description: string;
  arguments?: {
    name: string;
    description: string;
    required?: boolean;
  }[];
}
