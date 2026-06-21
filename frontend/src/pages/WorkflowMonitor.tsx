import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText, Zap, CheckCircle2, XCircle, Clock,
  ChevronRight, Download, BarChart3, RefreshCw,
  AlertTriangle, Layers, Brain, Search, PenTool, Shield
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useWorkflowStore } from '../stores/workflowStore';
import { useWorkflowStream } from '../hooks/useWorkflowStream';
import ThemeSwitcher from '../components/ThemeSwitcher';
import type { AgentName, DocumentType, WorkflowStateEnum } from '../types';

// ── Constants ──────────────────────────────────────────────────────────────────

const STATES: WorkflowStateEnum[] = [
  'INIT', 'BRIEFING', 'ENRICHMENT', 'VALIDATION',
  'WRITING', 'QUALITY_ANALYSIS', 'COMPLETED',
];

const STATE_LABELS: Record<string, string> = {
  INIT: 'Inizializzazione',
  BRIEFING: 'Raccolta Requisiti',
  ENRICHMENT: 'Arricchimento KB',
  VALIDATION: 'Validazione',
  WRITING: 'Generazione Doc.',
  QUALITY_ANALYSIS: 'Quality Review',
  COMPLETED: 'Completato',
  FAILED: 'Errore',
};

const AGENT_META: Record<AgentName, { label: string; icon: React.ElementType; color: string }> = {
  orchestrator: { label: 'Orchestrator',    icon: Layers,   color: '#6366f1' },
  requirement:  { label: 'Requirement',     icon: Brain,    color: '#22d3ee' },
  procurement:  { label: 'Procurement',     icon: Search,   color: '#a78bfa' },
  lead_writer:  { label: 'Lead Writer',     icon: PenTool,  color: '#34d399' },
  quality:      { label: 'Quality Agent',   icon: Shield,   color: '#fb923c' },
};

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8001/api/v1';

// ── Helpers ────────────────────────────────────────────────────────────────────

function stateIndex(s: string): number {
  return STATES.indexOf(s as WorkflowStateEnum);
}

function stateColor(s: string): string {
  if (s === 'COMPLETED') return '#34d399';
  if (s === 'FAILED') return '#f87171';
  return '#6366f1';
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StateRail({ current }: { current: string }) {
  const idx = stateIndex(current);
  return (
    <div className="flex items-center gap-0 w-full overflow-x-auto pb-2">
      {STATES.map((s, i) => {
        const done = i < idx;
        const active = i === idx;
        const failed = current === 'FAILED';
        return (
          <div key={s} className="flex items-center flex-1 min-w-0">
            <div className="flex flex-col items-center flex-1 min-w-0">
              <motion.div
                animate={{
                  scale: active ? [1, 1.15, 1] : 1,
                  boxShadow: active ? '0 0 20px rgba(99,102,241,0.6)' : 'none',
                }}
                transition={{ repeat: active ? Infinity : 0, duration: 2 }}
                className={`
                  w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold
                  transition-all duration-500
                  ${done ? 'bg-indigo-500 border-indigo-500 text-white' : ''}
                  ${active && !failed ? 'bg-indigo-500/20 border-indigo-400 text-indigo-300' : ''}
                  ${!done && !active ? 'bg-zinc-200 dark:bg-zinc-800 border-zinc-300 dark:border-zinc-700 text-zinc-400 dark:text-zinc-600' : ''}
                  ${failed && active ? 'bg-red-500/20 border-red-500 text-red-400' : ''}
                `}
              >
                {done ? <CheckCircle2 size={14} /> : i + 1}
              </motion.div>
              <span className={`
                text-[9px] mt-1 text-center leading-tight max-w-[64px]
                ${active ? 'text-indigo-300 font-semibold' : done ? 'text-zinc-400' : 'text-zinc-600'}
              `}>
                {STATE_LABELS[s]}
              </span>
            </div>
            {i < STATES.length - 1 && (
              <div className={`
                h-[2px] flex-1 mx-1 transition-all duration-500
                ${i < idx ? 'bg-indigo-500' : 'bg-zinc-700'}
              `} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function AgentCard({ name, status, duration_ms }: {
  name: AgentName; status: string; duration_ms?: number;
}) {
  const meta = AGENT_META[name];
  const Icon = meta.icon;
  const isRunning = status === 'running';
  const isDone = status === 'done';

  return (
    <motion.div
      animate={isRunning ? { borderColor: [meta.color + '40', meta.color, meta.color + '40'] } : {}}
      transition={{ repeat: Infinity, duration: 1.5 }}
      className={`
        relative p-3 rounded-xl border transition-all duration-300
        ${isRunning ? 'bg-zinc-100 dark:bg-zinc-800/80' : 'bg-zinc-50 dark:bg-zinc-900/50'}
        ${isDone ? 'border-zinc-300 dark:border-zinc-700' : isRunning ? '' : 'border-zinc-200 dark:border-zinc-800'}
      `}
      style={{ borderColor: isRunning ? meta.color : undefined }}
    >
      <div className="flex items-center gap-2.5">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: meta.color + '20' }}
        >
          <Icon size={15} style={{ color: meta.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className={`text-xs font-semibold ${isRunning ? 'text-zinc-900 dark:text-white' : 'text-zinc-500 dark:text-zinc-400'}`}>
            {meta.label}
          </div>
          <div className="text-[10px] text-zinc-500 dark:text-zinc-600 mt-0.5">
            {isRunning && (
              <span style={{ color: meta.color }} className="flex items-center gap-1">
                <motion.span
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ repeat: Infinity, duration: 1 }}
                >●</motion.span>
                In esecuzione…
              </span>
            )}
            {isDone && duration_ms && `Completato in ${(duration_ms / 1000).toFixed(1)}s`}
            {status === 'idle' && 'In attesa'}
            {status === 'error' && <span className="text-red-400">Errore</span>}
          </div>
        </div>
        {isDone && <CheckCircle2 size={14} className="text-emerald-400 flex-shrink-0" />}
        {status === 'error' && <XCircle size={14} className="text-red-400 flex-shrink-0" />}
      </div>
    </motion.div>
  );
}

function QualityGauge({ score, passed }: { score: number; passed: boolean }) {
  const pct = Math.round(score * 100);
  const color = passed ? '#34d399' : score > 0.5 ? '#fb923c' : '#f87171';
  const circumference = 2 * Math.PI * 36;
  const dash = circumference * score;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
          <circle cx="40" cy="40" r="36" fill="none" stroke="#27272a" strokeWidth="6" />
          <motion.circle
            cx="40" cy="40" r="36" fill="none"
            stroke={color} strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={`${circumference}`}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference - dash }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-black" style={{ color }}>{pct}</span>
          <span className="text-[9px] text-zinc-500 -mt-1">/ 100</span>
        </div>
      </div>
      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
        passed ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
      }`}>
        {passed ? '✓ APPROVATO' : '✗ REVISIONE'}
      </span>
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────────

export default function WorkflowMonitorPage() {
  const [view, setView] = useState<'form' | 'monitor' | 'document'>('form');
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);
  const [docPreview, setDocPreview] = useState<string>('');
  const [formData, setFormData] = useState({
    document_type: 'capitolato' as DocumentType,
    title: '',
    raw_description: '',
  });

  const {
    activeWorkflow,
    agentStatuses,
    qualityReport,
    events,
    isStreaming,
    reset,
  } = useWorkflowStore();

  useWorkflowStream(activeWorkflowId);

  async function handleStart() {
    if (!formData.title || !formData.raw_description) return;
    reset();

    const res = await fetch(`${API_BASE}/workflow/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...formData, form_data: {} }),
    });
    const data = await res.json();
    setActiveWorkflowId(data.workflow_id);
    setView('monitor');
  }

  const currentState = activeWorkflow?.state ?? 'INIT';
  const isFailed = currentState === 'FAILED';
  const isCompleted = currentState === 'COMPLETED';

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-white font-mono">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center">
            <FileText size={16} />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-widest uppercase text-zinc-900 dark:text-white">
              AI Document Platform
            </h1>
            <p className="text-[10px] text-zinc-400 dark:text-zinc-500 tracking-wider">
              Enterprise Document Generator
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {isStreaming && (
            <motion.div
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ repeat: Infinity, duration: 1.2 }}
              className="flex items-center gap-1.5 text-[10px] text-indigo-400"
            >
              <Zap size={10} />
              LIVE
            </motion.div>
          )}
          {activeWorkflowId && (
            <span className="text-[10px] text-zinc-400 dark:text-zinc-600 font-mono">
              {activeWorkflowId.slice(0, 8)}…
            </span>
          )}
          <ThemeSwitcher />
        </div>
      </header>

      {/* ── Nav tabs ───────────────────────────────────────────────────────── */}
      <nav className="border-b border-zinc-200 dark:border-zinc-800 px-6 flex gap-0">
        {(['form', 'monitor', 'document'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setView(tab)}
            className={`
              px-5 py-3 text-[11px] font-semibold uppercase tracking-widest border-b-2
              transition-colors duration-200
              ${view === tab
                ? 'border-indigo-500 text-indigo-500 dark:text-indigo-400'
                : 'border-transparent text-zinc-400 dark:text-zinc-600 hover:text-zinc-600 dark:hover:text-zinc-400'}
            `}
          >
            {tab === 'form' ? 'Nuovo' : tab === 'monitor' ? 'Monitor' : 'Documento'}
          </button>
        ))}
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <AnimatePresence mode="wait">

          {/* ── FORM ──────────────────────────────────────────────────────── */}
          {view === 'form' && (
            <motion.div
              key="form"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              className="max-w-2xl mx-auto"
            >
              <div className="mb-8">
                <h2 className="text-2xl font-black tracking-tight text-zinc-900 dark:text-white">
                  Nuovo Documento
                </h2>
                <p className="text-zinc-500 dark:text-zinc-500 text-sm mt-1">
                  Avvia la generazione automatica tramite workflow multi-agente
                </p>
              </div>

              <div className="space-y-5">
                {/* Document type selector */}
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-2">
                    Tipo Documento
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {(['capitolato', 'requisiti'] as DocumentType[]).map((t) => (
                      <button
                        key={t}
                        onClick={() => setFormData(p => ({ ...p, document_type: t }))}
                        className={`
                          p-4 rounded-xl border text-left transition-all duration-200
                          ${formData.document_type === t
                            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-300'
                            : 'border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'}
                        `}
                      >
                        <div className="text-sm font-bold mb-1">
                          {t === 'capitolato' ? 'Capitolato di Gara' : 'Requisiti Funzionali'}
                        </div>
                        <div className="text-[10px] opacity-70">
                          {t === 'capitolato'
                            ? 'Documento procurement IT completo'
                            : 'Specifica requisiti tecnici e funzionali'}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Title */}
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-2">
                    Titolo Progetto
                  </label>
                  <input
                    value={formData.title}
                    onChange={e => setFormData(p => ({ ...p, title: e.target.value }))}
                    placeholder="es. Sistema ERP Cloud per PA"
                    className="w-full bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-3
                               text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-700
                               focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-2">
                    Descrizione Requisiti
                  </label>
                  <textarea
                    value={formData.raw_description}
                    onChange={e => setFormData(p => ({ ...p, raw_description: e.target.value }))}
                    placeholder="Descrivi il progetto IT, gli obiettivi, i requisiti principali, le integrazioni necessarie, i vincoli di sicurezza e compliance…"
                    rows={6}
                    className="w-full bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-3
                               text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-700 resize-none
                               focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleStart}
                  disabled={!formData.title || !formData.raw_description}
                  className="w-full py-4 bg-indigo-500 hover:bg-indigo-400 disabled:bg-zinc-800
                             disabled:text-zinc-600 text-white font-bold text-sm rounded-xl
                             transition-colors duration-200 flex items-center justify-center gap-2"
                >
                  <Zap size={16} />
                  Avvia Workflow AI
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* ── MONITOR ───────────────────────────────────────────────────── */}
          {view === 'monitor' && (
            <motion.div
              key="monitor"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              className="space-y-6"
            >
              {/* State rail */}
              <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500">
                    Stato Workflow
                  </h3>
                  <span className={`
                    text-xs font-bold px-3 py-1 rounded-full
                    ${isCompleted ? 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' :
                      isFailed ? 'bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400' :
                      'bg-indigo-100 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'}
                  `}>
                    {STATE_LABELS[currentState] ?? currentState}
                  </span>
                </div>
                <StateRail current={currentState} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Agent grid */}
                <div className="lg:col-span-2 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-4">
                    Agenti AI
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {(Object.keys(AGENT_META) as AgentName[]).map((name) => (
                      <AgentCard
                        key={name}
                        name={name}
                        status={agentStatuses[name]?.status ?? 'idle'}
                        duration_ms={agentStatuses[name]?.duration_ms}
                      />
                    ))}
                  </div>
                </div>

                {/* Quality + events */}
                <div className="space-y-4">
                  {qualityReport && (
                    <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5">
                      <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-4">
                        Quality Score
                      </h3>
                      <QualityGauge
                        score={qualityReport.score}
                        passed={qualityReport.passed}
                      />
                      {qualityReport.issues.length > 0 && (
                        <div className="mt-4 space-y-2">
                          {qualityReport.issues.slice(0, 3).map((issue) => (
                            <div
                              key={issue.id}
                              className={`text-[10px] p-2 rounded-lg ${
                                issue.severity === 'CRITICAL' ? 'bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400' :
                                issue.severity === 'MAJOR' ? 'bg-orange-100 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400' :
                                'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-500'
                              }`}
                            >
                              <span className="font-bold">{issue.id}</span> {issue.description}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Event log */}
                  <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-3">
                      Event Log
                    </h3>
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                      {events.slice(-20).reverse().map((ev, i) => (
                        <div key={i} className="flex items-center gap-2 text-[10px]">
                          <span className="text-zinc-400 dark:text-zinc-700 w-16 flex-shrink-0 font-mono">
                            {new Date().toLocaleTimeString('it', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </span>
                          <span className={`
                            px-1.5 py-0.5 rounded text-[9px] font-bold flex-shrink-0
                            ${ev.event === 'completed' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' :
                              ev.event === 'failed' ? 'bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400' :
                              ev.event === 'state_change' ? 'bg-indigo-100 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400' :
                              'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-500'}
                          `}>
                            {ev.event}
                          </span>
                          <span className="text-zinc-500 dark:text-zinc-600 truncate">
                            {JSON.stringify(ev.data).slice(0, 40)}
                          </span>
                        </div>
                      ))}
                      {events.length === 0 && (
                        <p className="text-zinc-400 dark:text-zinc-700 text-[10px]">Nessun evento ancora…</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              {(isCompleted || isFailed) && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3"
                >
                  {isCompleted && (
                    <button
                      onClick={() => setView('document')}
                      className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400
                                 text-white text-xs font-bold rounded-xl transition-colors"
                    >
                      <FileText size={14} />
                      Visualizza Documento
                    </button>
                  )}
                  <button
                    onClick={() => { reset(); setView('form'); }}
                    className="flex items-center gap-2 px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700
                               text-white text-xs font-bold rounded-xl transition-colors"
                  >
                    <RefreshCw size={14} />
                    Nuovo Workflow
                  </button>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* ── DOCUMENT ──────────────────────────────────────────────────── */}
          {view === 'document' && (
            <motion.div
              key="document"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-black tracking-tight text-zinc-900 dark:text-white">Documento Generato</h2>
                <div className="flex gap-2">
                  <button className="flex items-center gap-1.5 px-4 py-2 bg-zinc-200 dark:bg-zinc-800 hover:bg-zinc-300 dark:hover:bg-zinc-700
                                     text-xs font-bold text-zinc-700 dark:text-white rounded-xl transition-colors">
                    <Download size={12} />
                    DOCX
                  </button>
                  <button className="flex items-center gap-1.5 px-4 py-2 bg-zinc-200 dark:bg-zinc-800 hover:bg-zinc-300 dark:hover:bg-zinc-700
                                     text-xs font-bold text-zinc-700 dark:text-white rounded-xl transition-colors">
                    <Download size={12} />
                    PDF
                  </button>
                </div>
              </div>
              <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8">
                {docPreview ? (
                  <div className="prose dark:prose-invert prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {docPreview}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <div className="text-center py-16 text-zinc-400 dark:text-zinc-600">
                    <FileText size={32} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm">Nessun documento disponibile.</p>
                    <p className="text-xs mt-1">Completa un workflow per generare un documento.</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </main>
    </div>
  );
}
