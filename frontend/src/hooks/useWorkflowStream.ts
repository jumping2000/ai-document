import { useEffect, useRef } from 'react';
import type { AgentName, WorkflowEvent } from '../types';
import { useWorkflowStore } from '../stores/workflowStore';

const WS_BASE = import.meta.env.VITE_WS_URL ?? `ws://${window.location.host}`;

export function useWorkflowStream(workflowId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const {
    updateWorkflowState,
    setAgentRunning,
    setAgentDone,
    setAgentTokens,
    setQualityReport,
    setValidationResult,
    setDocumentContent,
    pushEvent,
    setStreaming,
  } = useWorkflowStore();

  useEffect(() => {
    if (!workflowId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/workflow/${workflowId}`);
    wsRef.current = ws;
    setStreaming(true);
    console.log('[WS] Connecting to:', `${WS_BASE}/ws/workflow/${workflowId}`);

    ws.onopen = () => {
      console.log('[WS] Connected');
    };

    ws.onmessage = (e: MessageEvent) => {
      const msg: WorkflowEvent = JSON.parse(e.data);
      console.log('[WS] Event received:', msg.event, msg.data);
      pushEvent(msg);

      switch (msg.event) {
        case 'state_change':
          updateWorkflowState(msg.data.state as any);
          break;
        case 'agent_start':
          setAgentRunning(msg.data.agent as AgentName);
          break;
        case 'agent_done':
          setAgentDone(msg.data.agent as AgentName, msg.data.duration_ms as number);
          if ((msg.data as Record<string, unknown>).tokens) {
            setAgentTokens(
              msg.data.agent as AgentName,
              (msg.data as Record<string, unknown>).tokens as { input: number; output: number; total: number },
            );
          }
          break;
        case 'quality_report':
          setQualityReport(msg.data as any);
          break;
        case 'pending_approval':
          // Approval gate event — frontend shows ApprovalPanel based on state
          break;
        case 'validation_result':
        case 'validation_failed':
          setValidationResult({
            valid: !!(msg.data as Record<string, unknown>).valid,
            confidence: Number((msg.data as Record<string, unknown>).confidence) || 0,
            missing_fields: ((msg.data as Record<string, unknown>).missing_fields as string[]) ?? [],
            issues: ((msg.data as Record<string, unknown>).issues as string[]) ?? [],
            warnings: ((msg.data as Record<string, unknown>).warnings as string[]) ?? [],
          });
          break;
        case 'completed':
          setDocumentContent((msg.data.document_content as string) || '');
          setStreaming(false);
          break;
        case 'failed':
          setStreaming(false);
          break;
      }
    };

    ws.onerror = () => setStreaming(false);
    ws.onclose = () => setStreaming(false);

    return () => {
      ws.close();
      setStreaming(false);
    };
  }, [workflowId]);

  return wsRef;
}
