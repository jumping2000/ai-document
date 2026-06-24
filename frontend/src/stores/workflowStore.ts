import { create } from 'zustand';
import type {
  AgentName,
  AgentStatus,
  QualityReport,
  ValidationResult,
  Workflow,
  WorkflowEvent,
  WorkflowStateEnum,
} from '../types';

interface WorkflowStore {
  // Active workflow
  activeWorkflow: Workflow | null;
  agentStatuses: Record<AgentName, AgentStatus>;
  qualityReport: QualityReport | null;
  validationResult: ValidationResult | null;
  documentContent: string;
  events: WorkflowEvent[];
  isStreaming: boolean;

  // All workflows (dashboard)
  workflows: Workflow[];

  // Actions
  setActiveWorkflow: (wf: Workflow) => void;
  updateWorkflowState: (state: WorkflowStateEnum) => void;
  setAgentRunning: (agent: AgentName) => void;
  setAgentDone: (agent: AgentName, duration_ms: number) => void;
  setQualityReport: (report: QualityReport) => void;
  setValidationResult: (result: ValidationResult) => void;
  setDocumentContent: (content: string) => void;
  pushEvent: (event: WorkflowEvent) => void;
  setStreaming: (v: boolean) => void;
  setWorkflows: (wfs: Workflow[]) => void;
  reset: () => void;
}

const defaultAgentStatuses = (): Record<AgentName, AgentStatus> => ({
  orchestrator: { name: 'orchestrator', status: 'idle' },
  requirement:  { name: 'requirement',  status: 'idle' },
  procurement:  { name: 'procurement',  status: 'idle' },
  lead_writer:  { name: 'lead_writer',  status: 'idle' },
  quality:      { name: 'quality',      status: 'idle' },
});

export const useWorkflowStore = create<WorkflowStore>((set) => ({
  activeWorkflow: null,
  agentStatuses: defaultAgentStatuses(),
  qualityReport: null,
  validationResult: null,
  documentContent: '',
  events: [],
  isStreaming: false,
  workflows: [],

  setActiveWorkflow: (wf) => set({ activeWorkflow: wf }),

  updateWorkflowState: (state) =>
    set((s) => ({
      activeWorkflow: s.activeWorkflow ? { ...s.activeWorkflow, state } : null,
    })),

  setAgentRunning: (agent) =>
    set((s) => ({
      agentStatuses: {
        ...s.agentStatuses,
        [agent]: { name: agent, status: 'running', started_at: Date.now() },
      },
    })),

  setAgentDone: (agent, duration_ms) =>
    set((s) => ({
      agentStatuses: {
        ...s.agentStatuses,
        [agent]: { name: agent, status: 'done', duration_ms },
      },
    })),

  setQualityReport: (report) => set({ qualityReport: report }),

  setValidationResult: (result) => set({ validationResult: result }),

  setDocumentContent: (content) => set({ documentContent: content }),

  pushEvent: (event) =>
    set((s) => ({ events: [...s.events.slice(-99), event] })),

  setStreaming: (v) => set({ isStreaming: v }),

  setWorkflows: (wfs) => set({ workflows: wfs }),

  reset: () =>
    set({
      activeWorkflow: null,
      agentStatuses: defaultAgentStatuses(),
      qualityReport: null,
      validationResult: null,
      documentContent: '',
      events: [],
      isStreaming: false,
    }),
}));
