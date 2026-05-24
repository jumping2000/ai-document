import { useEffect, useRef } from 'react';
import type { AgentName, WorkflowEvent } from '../types';
import { useWorkflowStore } from '../stores/workflowStore';

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8001';

export function useWorkflowStream(workflowId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const {
    updateWorkflowState,
    setAgentRunning,
    setAgentDone,
    setQualityReport,
    pushEvent,
    setStreaming,
  } = useWorkflowStore();

  useEffect(() => {
    if (!workflowId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/workflow/${workflowId}`);
    wsRef.current = ws;
    setStreaming(true);

    ws.onmessage = (e: MessageEvent) => {
      const msg: WorkflowEvent = JSON.parse(e.data);
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
          break;
        case 'quality_report':
          setQualityReport(msg.data as any);
          break;
        case 'completed':
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
