// ── Workflow ──────────────────────────────────────────────────────────────────

export type DocumentType = 'capitolato' | 'requisiti';

export type WorkflowStateEnum =
  | 'INIT'
  | 'BRIEFING'
  | 'ENRICHMENT'
  | 'VALIDATION'
  | 'WRITING'
  | 'QUALITY_ANALYSIS'
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
  | 'validation_failed'
  | 'completed'
  | 'failed'
  | 'heartbeat';

export interface WorkflowEvent {
  event: WorkflowEventType;
  data: Record<string, unknown>;
}

// ── Agents ────────────────────────────────────────────────────────────────────

export type AgentName = 'requirement' | 'procurement' | 'lead_writer' | 'quality' | 'orchestrator';

export interface AgentStatus {
  name: AgentName;
  status: 'idle' | 'running' | 'done' | 'error';
  duration_ms?: number;
  started_at?: number;
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
