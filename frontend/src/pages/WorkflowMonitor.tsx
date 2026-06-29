import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText, Zap, CheckCircle2, XCircle, Clock,
  ChevronRight, Download, BarChart3, RefreshCw,
  AlertTriangle, Layers, Brain, Search, PenTool, Shield,
  Database, FilePlus, Activity, ClipboardCheck, Settings
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useWorkflowStore } from '../stores/workflowStore';
import { useWorkflowStream } from '../hooks/useWorkflowStream';
import ThemeSwitcher from '../components/ThemeSwitcher';
import LanguageSwitcher from '../components/LanguageSwitcher';
import MCPSettings from './MCPSettings';
import TemplateSettings from './TemplateSettings';
import { useTranslation } from '../i18n/LanguageContext';
import type { AgentName, DocumentType, WorkflowStateEnum } from '../types';

// ── Constants ──────────────────────────────────────────────────────────────────

const STATES: WorkflowStateEnum[] = [
  'INIT', 'BRIEFING', 'ENRICHMENT', 'VALIDATION',
  'WRITING', 'QUALITY_ANALYSIS', 'PENDING_APPROVAL', 'COMPLETED',
];

const AGENT_META: Record<AgentName, { labelKey: string; icon: React.ElementType; color: string }> = {
  orchestrator: { labelKey: 'agent.orchestrator', icon: Layers,   color: '#6366f1' },
  requirement:  { labelKey: 'agent.requirement',  icon: Brain,    color: '#22d3ee' },
  procurement:  { labelKey: 'agent.procurement',  icon: Search,   color: '#a78bfa' },
  lead_writer:  { labelKey: 'agent.leadWriter',   icon: PenTool,  color: '#34d399' },
  quality:      { labelKey: 'agent.quality',      icon: Shield,   color: '#fb923c' },
};

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8001/api/v1';

// ── Helpers ────────────────────────────────────────────────────────────────────

function stateIndex(s: string): number {
  return STATES.indexOf(s as WorkflowStateEnum);
}

function stateColor(s: string): string {
  if (s === 'COMPLETED') return '#34d399';
  if (s === 'FAILED') return '#f87171';
  if (s === 'PENDING_APPROVAL') return '#f59e0b';
  return '#6366f1';
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StateRail({ current }: { current: string }) {
  const { t } = useTranslation();
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
                {t(`state.${s}`)}
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
  const { t } = useTranslation();
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
            {t(meta.labelKey)}
          </div>
          <div className="text-[10px] text-zinc-500 dark:text-zinc-600 mt-0.5">
            {isRunning && (
              <span style={{ color: meta.color }} className="flex items-center gap-1">
                <motion.span
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ repeat: Infinity, duration: 1 }}
                >●</motion.span>
                {t('agent.running')}
              </span>
            )}
            {isDone && duration_ms && `${t('agent.completed')} ${(duration_ms / 1000).toFixed(1)}s`}
            {status === 'idle' && t('agent.waiting')}
            {status === 'error' && <span className="text-red-400">{t('agent.error')}</span>}
          </div>
        </div>
        {isDone && <CheckCircle2 size={14} className="text-emerald-400 flex-shrink-0" />}
        {status === 'error' && <XCircle size={14} className="text-red-400 flex-shrink-0" />}
      </div>
    </motion.div>
  );
}

function QualityGauge({ score, passed }: { score: number; passed: boolean }) {
  const { t } = useTranslation();
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
        {passed ? t('quality.approved') : t('quality.revision')}
      </span>
    </div>
  );
}

// ── Approval Panel ─────────────────────────────────────────────────────────────

function ApprovalPanel({
  workflowId,
  qualityScore,
  issues,
  suggestions,
}: {
  workflowId: string;
  qualityScore: number;
  issues: string[];
  suggestions: string[];
}) {
  const { t } = useTranslation();
  const [comment, setComment] = useState('');
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);

  async function handleApprove(approved: boolean) {
    setSending(true);
    try {
      const res = await fetch(`${API_BASE}/workflow/${workflowId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved, comment }),
      });
      if (res.ok) {
        setDone(true);
      }
    } catch (err) {
      console.error('Approval failed:', err);
    } finally {
      setSending(false);
    }
  }

  if (done) {
    return (
      <div className="bg-amber-50 dark:bg-amber-500/5 border border-amber-200 dark:border-amber-500/30 rounded-2xl p-6 text-center">
        <p className="text-sm text-amber-600 dark:text-amber-400 font-semibold">
          {t('approval.sending')}
        </p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-amber-50 dark:bg-amber-500/5 border border-amber-200 dark:border-amber-500/30 rounded-2xl p-6 space-y-4"
    >
      <div className="flex items-center gap-2">
        <Clock size={18} className="text-amber-500" />
        <h3 className="text-sm font-bold text-amber-600 dark:text-amber-400">
          {t('approval.title')}
        </h3>
      </div>

      <p className="text-xs text-zinc-600 dark:text-zinc-400">
        {t('approval.waiting')}
      </p>

      <div className="flex gap-2 text-xs text-zinc-500">
        <span>Score: <strong>{Math.round(qualityScore * 100)}%</strong></span>
        <span>|</span>
        <span>Issues: <strong>{issues.length}</strong></span>
        <span>|</span>
        <span>Suggestions: <strong>{suggestions.length}</strong></span>
      </div>

      <div>
        <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-1">
          {t('approval.comment')}
        </label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={2}
          className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2
                     text-xs text-zinc-900 dark:text-white placeholder-zinc-400 resize-none
                     focus:outline-none focus:border-amber-500 transition-colors"
        />
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => handleApprove(true)}
          disabled={sending}
          className="flex-1 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50
                     text-white text-xs font-bold rounded-xl transition-colors flex items-center justify-center gap-1.5"
        >
          <CheckCircle2 size={14} />
          {t('approval.approve')}
        </button>
        <button
          onClick={() => handleApprove(false)}
          disabled={sending}
          className="flex-1 py-2.5 bg-red-500 hover:bg-red-400 disabled:opacity-50
                     text-white text-xs font-bold rounded-xl transition-colors flex items-center justify-center gap-1.5"
        >
          <XCircle size={14} />
          {t('approval.reject')}
        </button>
      </div>
    </motion.div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────────

export default function WorkflowMonitorPage() {
  const { t } = useTranslation();
  const [view, setView] = useState<'form' | 'monitor' | 'document' | 'knowledge' | 'templates'>('form');
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  // documentContent is now in the store
  const [mcpConnections, setMcpConnections] = useState<{id: string; name: string}[]>([]);
  const [selectedMcp, setSelectedMcp] = useState<string>('');
  const [formData, setFormData] = useState({
    document_type: 'capitolato' as DocumentType,
    title: '',
    raw_description: '',
  });

  const {
    activeWorkflow,
    agentStatuses,
    qualityReport,
    validationResult,
    documentContent,
    events,
    isStreaming,
    setActiveWorkflow,
    reset,
  } = useWorkflowStore();

  useWorkflowStream(activeWorkflowId);

  // Fetch MCP connections on mount
  useEffect(() => {
    fetch(`${API_BASE}/mcp/connections`)
      .then(res => res.ok ? res.json() : [])
      .then(data => setMcpConnections(data.filter((c: {is_active: boolean}) => c.is_active)))
      .catch(() => {});
  }, []);

  async function handleStart() {
    if (!formData.title || !formData.raw_description) return;
    reset();

    const res = await fetch(`${API_BASE}/workflow/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...formData,
        form_data: {},
        mcp_connection_id: selectedMcp || undefined,
      }),
    });
    const data = await res.json();
    setActiveWorkflow({
      workflow_id: data.workflow_id,
      state: data.state ?? 'INIT',
      document_type: formData.document_type,
      title: formData.title,
      retry_count: 0,
      quality_score: null,
    });
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
              {t('app.title')}
            </h1>
            <p className="text-[10px] text-zinc-400 dark:text-zinc-500 tracking-wider">
              {t('app.subtitle')}
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
          <LanguageSwitcher />
        </div>
      </header>

      {/* ── Nav tabs ───────────────────────────────────────────────────────── */}
      <nav className="border-b border-zinc-200 dark:border-zinc-800 px-6 flex gap-0">
        {(['form', 'monitor', 'document', 'knowledge', 'templates'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setView(tab)}
            className={`
              px-5 py-3 text-[11px] font-semibold uppercase tracking-widest border-b-2
              transition-colors duration-200 flex items-center gap-1.5
              ${view === tab
                ? 'border-indigo-500 text-indigo-500 dark:text-indigo-400'
                : 'border-transparent text-zinc-400 dark:text-zinc-600 hover:text-zinc-600 dark:hover:text-zinc-400'}
            `}
          >
            {tab === 'form' && <FilePlus size={12} />}
            {tab === 'monitor' && <Activity size={12} />}
            {tab === 'document' && <FileText size={12} />}
            {tab === 'knowledge' && <Database size={12} />}
            {tab === 'templates' && <Settings size={12} />}
            {tab === 'form' ? t('nav.new') : tab === 'monitor' ? t('nav.monitor') : tab === 'document' ? t('nav.document') : tab === 'knowledge' ? t('nav.knowledge') : t('nav.templates')}
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
                  {t('form.newDocument')}
                </h2>
                <p className="text-zinc-500 dark:text-zinc-500 text-sm mt-1">
                  {t('form.newDocumentDesc')}
                </p>
              </div>

              <div className="space-y-5">
                {/* Document type selector */}
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-2">
                    {t('form.documentType')}
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {(['capitolato', 'requisiti', 'documento'] as DocumentType[]).map((docType) => (
                      <button
                        key={docType}
                        onClick={() => setFormData(p => ({ ...p, document_type: docType }))}
                        className={`
                          p-4 rounded-xl border text-left transition-all duration-200
                          ${formData.document_type === docType
                            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-300'
                            : 'border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'}
                        `}
                      >
                        <div className="text-sm font-bold mb-1">
                          {docType === 'capitolato' ? t('form.capitolato') : docType === 'requisiti' ? t('form.requisiti') : t('form.documento')}
                        </div>
                        <div className="text-[10px] opacity-70">
                          {docType === 'capitolato'
                            ? t('form.capitolatoDesc')
                            : docType === 'requisiti'
                            ? t('form.requisitiDesc')
                            : t('form.documentoDesc')}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Title */}
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-2">
                    {t('form.projectTitle')}
                  </label>
                  <input
                    value={formData.title}
                    onChange={e => setFormData(p => ({ ...p, title: e.target.value }))}
                    placeholder={t('form.projectTitlePlaceholder')}
                    className="w-full bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-3
                               text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-700
                               focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>

                {/* MCP Connection selector */}
                {mcpConnections.length > 0 && (
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-2">
                      {t('form.knowledgeSource')}
                    </label>
                    <select
                      value={selectedMcp}
                      onChange={e => setSelectedMcp(e.target.value)}
                      className="w-full bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-3
                                 text-sm text-zinc-900 dark:text-white focus:outline-none focus:border-indigo-500 transition-colors"
                    >
                      <option value="">{t('form.noKnowledge')}</option>
                      {mcpConnections.map(conn => (
                        <option key={conn.id} value={conn.id}>{conn.name}</option>
                      ))}
                    </select>
                    {selectedMcp && (
                      <p className="text-[10px] text-emerald-500 mt-1.5">
                        {t('form.knowledgeHint')}
                      </p>
                    )}
                  </div>
                )}

                {/* Description */}
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-2">
                    {t('form.description')}
                  </label>
                  <textarea
                    value={formData.raw_description}
                    onChange={e => setFormData(p => ({ ...p, raw_description: e.target.value }))}
                    placeholder={t('form.descriptionPlaceholder')}
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
                  {t('form.startWorkflow')}
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
                    {t('monitor.title')}
                  </h3>
                  <span className={`
                    text-xs font-bold px-3 py-1 rounded-full
                    ${isCompleted ? 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' :
                      isFailed ? 'bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400' :
                      'bg-indigo-100 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'}
                  `}>
                    {t(`state.${currentState}`) ?? currentState}
                  </span>
                </div>
                <StateRail current={currentState} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left column: Agent AI + Quality + Validation */}
                <div className="lg:col-span-2 space-y-6">
                  {/* Agent grid */}
                  <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-4">
                      {t('monitor.agents')}
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

                  {/* Quality gauge */}
                  {qualityReport && (
                    <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5">
                      <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-4">
                        {t('monitor.qualityScore')}
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

                  {/* Validation Result */}
                  {validationResult && (
                    <div className={`border rounded-2xl p-5 ${
                      validationResult.valid
                        ? 'bg-emerald-50 dark:bg-emerald-500/5 border-emerald-200 dark:border-emerald-500/30'
                        : 'bg-red-50 dark:bg-red-500/5 border-red-200 dark:border-red-500/30'
                    }`}>
                      <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-3 flex items-center gap-2">
                        <ClipboardCheck size={12} />
                        {t('monitor.validation')}
                      </h3>
                      <div className="flex items-center gap-3 mb-3">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          validationResult.valid
                            ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                            : 'bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400'
                        }`}>
                          {validationResult.valid ? t('monitor.validationPassed') : t('monitor.validationFailed')}
                        </span>
                        <span className="text-[10px] text-zinc-500">
                          {t('template.confidence')}: {Math.round(validationResult.confidence * 100)}%
                        </span>
                      </div>
                      {validationResult.missing_fields.length > 0 && (
                        <div className="text-[10px] text-red-600 dark:text-red-400 mb-2">
                          <span className="font-bold">{t('template.missingFields')}:</span>{' '}
                          {validationResult.missing_fields.join(', ')}
                        </div>
                      )}
                      {validationResult.issues.length > 0 && (
                        <div className="space-y-1 mb-2">
                          <span className="text-[10px] font-bold text-zinc-500">{t('template.issues')}:</span>
                          {validationResult.issues.map((issue, i) => (
                            <div key={i} className="text-[10px] text-red-600 dark:text-red-400 flex items-start gap-1">
                              <span className="mt-0.5">•</span>
                              <span>{issue}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {validationResult.warnings.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[10px] font-bold text-zinc-500">{t('template.warnings')}:</span>
                          {validationResult.warnings.map((w, i) => (
                            <div key={i} className="text-[10px] text-amber-600 dark:text-amber-400 flex items-start gap-1">
                              <span className="mt-0.5">⚠</span>
                              <span>{w}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Right column: Event log */}
                <div className="lg:col-span-1">
                  <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4 sticky top-6">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-500 mb-3">
                      {t('monitor.eventLog')}
                    </h3>
                    <div className="space-y-2 max-h-[calc(100vh-200px)] overflow-y-auto">
                      {events.slice(-20).reverse().map((ev, i) => (
                        <div key={i} className={`
                          flex flex-col gap-1 text-[10px] p-2 rounded-lg
                          ${ev.event === 'validation_failed' ? 'bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30' : ''}
                          ${ev.event === 'failed' ? 'bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30' : ''}
                        `}>
                          <div className="flex items-center gap-2">
                            <span className="text-zinc-400 dark:text-zinc-700 w-16 flex-shrink-0 font-mono">
                              {new Date().toLocaleTimeString('it', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                            </span>
                            <span className={`
                              px-1.5 py-0.5 rounded text-[9px] font-bold flex-shrink-0
                              ${ev.event === 'completed' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' :
                                ev.event === 'failed' ? 'bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400' :
                                ev.event === 'validation_failed' ? 'bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400' :
                                ev.event === 'validation_result' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' :
                                ev.event === 'state_change' ? 'bg-indigo-100 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400' :
                                'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-500'}
                            `}>
                              {ev.event === 'validation_failed' ? 'VALIDATION' : ev.event === 'validation_result' ? 'VALIDATION' : ev.event}
                            </span>
                            {!['validation_failed', 'failed', 'validation_result'].includes(ev.event) && (
                              <span className="text-zinc-500 dark:text-zinc-600 truncate">
                                {JSON.stringify(ev.data).slice(0, 40)}
                              </span>
                            )}
                          </div>
                          {/* Show validation details */}
                          {(ev.event === 'validation_failed' || ev.event === 'failed' || ev.event === 'validation_result') && ev.data && (
                            <div className="ml-[4.5rem] space-y-1">
                              {(() => {
                                const data = ev.data as {
                                  issues?: string[];
                                  missing_fields?: string[];
                                  warnings?: string[];
                                  error?: string;
                                  score?: number;
                                  confidence?: number;
                                };
                                return (
                                  <>
                                    {data.issues && Array.isArray(data.issues) && data.issues.map((issue: string, j: number) => (
                                      <div key={j} className="flex items-start gap-1.5">
                                        <span className="text-red-400 mt-0.5">•</span>
                                        <span className="text-red-600 dark:text-red-400">{issue}</span>
                                      </div>
                                    ))}
                                    {data.missing_fields && Array.isArray(data.missing_fields) && data.missing_fields.length > 0 && (
                                      <div className="text-[9px] text-red-500 dark:text-red-400">
                                        Campi mancanti: {data.missing_fields.join(', ')}
                                      </div>
                                    )}
                                    {data.warnings && Array.isArray(data.warnings) && data.warnings.map((w: string, j: number) => (
                                      <div key={j} className="text-[9px] text-amber-500 dark:text-amber-400 flex items-start gap-1">
                                        <span>⚠</span>
                                        <span>{w}</span>
                                      </div>
                                    ))}
                                    {data.error && (
                                      <div className="text-red-600 dark:text-red-400">{data.error}</div>
                                    )}
                                    {data.confidence !== undefined && data.confidence !== null && (
                                      <div className="text-[9px] text-zinc-500">
                                        Confidenza: {Math.round(data.confidence * 100)}%
                                      </div>
                                    )}
                                    {data.score !== undefined && data.score !== null && (
                                      <div className="text-[9px] text-zinc-500">
                                        Score: {Math.round(data.score * 100)}%
                                      </div>
                                    )}
                                  </>
                                );
                              })()}
                            </div>
                          )}
                        </div>
                      ))}
                      {events.length === 0 && (
                        <p className="text-zinc-400 dark:text-zinc-700 text-[10px]">{t('monitor.noEvents')}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Approval Panel — mostrato in PENDING_APPROVAL */}
              {currentState === 'PENDING_APPROVAL' && activeWorkflowId && qualityReport && (
                <ApprovalPanel
                  workflowId={activeWorkflowId}
                  qualityScore={qualityReport.score}
                  issues={qualityReport.issues?.map((i: {description: string}) => i.description) ?? []}
                  suggestions={qualityReport.suggestions ?? []}
                />
              )}

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
                      {t('monitor.viewDocument')}
                    </button>
                  )}
                  <button
                    onClick={() => { reset(); setView('form'); }}
                    className="flex items-center gap-2 px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700
                               text-white text-xs font-bold rounded-xl transition-colors"
                  >
                    <RefreshCw size={14} />
                    {t('monitor.newWorkflow')}
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
                <h2 className="text-lg font-black tracking-tight text-zinc-900 dark:text-white">{t('document.title')}</h2>
                <div className="flex gap-2">
                  <button
                    onClick={async () => {
                      if (!activeWorkflowId) return;
                      try {
                        const res = await fetch(`${API_BASE}/workflow/${activeWorkflowId}/export/docx`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ content: documentContent }),
                        });
                        if (!res.ok) {
                          const err = await res.json().catch(() => ({ detail: 'Export failed' }));
                          throw new Error(err.detail || 'Export failed');
                        }
                        const data = await res.json();
                        const dlUrl = `${API_BASE.replace('/api/v1', '')}${data.download_url}`;
                        const dlRes = await fetch(dlUrl);
                        if (!dlRes.ok) throw new Error('Download failed');
                        const blob = await dlRes.blob();
                        const a = document.createElement('a');
                        a.href = URL.createObjectURL(blob);
                        a.download = `${activeWorkflowId.slice(0, 8)}.docx`;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        URL.revokeObjectURL(a.href);
                        setDownloadError(null);
                      } catch (err) {
                        const msg = err instanceof Error ? err.message : 'Export failed';
                        console.error('DOCX export failed:', err);
                        setDownloadError(msg);
                      }
                    }}
                    disabled={!!downloadError}
                    className="flex items-center gap-1.5 px-4 py-2 bg-zinc-200 dark:bg-zinc-800 hover:bg-zinc-300 dark:hover:bg-zinc-700
                               disabled:opacity-50 text-xs font-bold text-zinc-700 dark:text-white rounded-xl transition-colors"
                  >
                    <Download size={12} />
                    {t('document.downloadDocx')}
                  </button>
                  <button
                    onClick={async () => {
                      if (!activeWorkflowId) return;
                      try {
                        const res = await fetch(`${API_BASE}/workflow/${activeWorkflowId}/export/pdf`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ content: documentContent }),
                        });
                        if (!res.ok) {
                          const err = await res.json().catch(() => ({ detail: 'Export failed' }));
                          throw new Error(err.detail || 'Export failed');
                        }
                        const data = await res.json();
                        const dlUrl = `${API_BASE.replace('/api/v1', '')}${data.download_url}`;
                        const dlRes = await fetch(dlUrl);
                        if (!dlRes.ok) throw new Error('Download failed');
                        const blob = await dlRes.blob();
                        const a = document.createElement('a');
                        a.href = URL.createObjectURL(blob);
                        a.download = `${activeWorkflowId.slice(0, 8)}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        URL.revokeObjectURL(a.href);
                        setDownloadError(null);
                      } catch (err) {
                        const msg = err instanceof Error ? err.message : 'Export failed';
                        console.error('PDF export failed:', err);
                        setDownloadError(msg);
                      }
                    }}
                    disabled={!!downloadError}
                    className="flex items-center gap-1.5 px-4 py-2 bg-zinc-200 dark:bg-zinc-800 hover:bg-zinc-300 dark:hover:bg-zinc-700
                               disabled:opacity-50 text-xs font-bold text-zinc-700 dark:text-white rounded-xl transition-colors"
                  >
                    <Download size={12} />
                    {t('document.downloadPdf')}
                  </button>
                </div>
              </div>
              {downloadError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-700 dark:text-red-300 flex items-center justify-between">
                  <span>⚠ {downloadError}</span>
                  <button onClick={() => setDownloadError(null)} className="text-red-500 hover:text-red-700 dark:hover:text-red-300 font-bold">✕</button>
                </div>
              )}
              <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8">
                {documentContent ? (
                  <div className="prose prose-sm max-w-none
                                  prose-headings:text-zinc-900 dark:prose-headings:text-zinc-100
                                  prose-p:text-zinc-800 dark:prose-p:text-zinc-200
                                  prose-li:text-zinc-800 dark:prose-li:text-zinc-200
                                  prose-strong:text-zinc-900 dark:prose-strong:text-white
                                  prose-a:text-indigo-600 dark:prose-a:text-indigo-400
                                  prose-code:text-zinc-800 dark:prose-code:text-zinc-200
                                  prose-table:text-zinc-800 dark:prose-table:text-zinc-200">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {documentContent}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <div className="text-center py-16 text-zinc-400 dark:text-zinc-600">
                    <FileText size={32} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm">{t('document.noDocument')}</p>
                    <p className="text-xs mt-1">{t('document.completeWorkflow')}</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* ── KNOWLEDGE ──────────────────────────────────────────────────── */}
          {view === 'knowledge' && (
            <motion.div
              key="knowledge"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
            >
              <MCPSettings />
            </motion.div>
          )}

          {/* ── TEMPLATES ─────────────────────────────────────────────────── */}
          {view === 'templates' && (
            <motion.div
              key="templates"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
            >
              <TemplateSettings />
            </motion.div>
          )}

        </AnimatePresence>
      </main>
    </div>
  );
}
