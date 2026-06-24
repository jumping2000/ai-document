import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Database, Plus, Trash2, RefreshCw, CheckCircle2, XCircle,
  Wrench, FileText, MessageSquare, Loader2, ExternalLink,
  Eye, EyeOff, X
} from 'lucide-react';
import { useTranslation } from '../i18n/LanguageContext';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8001/api/v1';

interface MCPConnection {
  id: string;
  name: string;
  description: string | null;
  url: string;
  transport: string;
  is_active: boolean;
  health_status: string;
  last_health_check: string | null;
  default_kb_id: string | null;
  discovered_tools: { name: string; description: string }[];
  discovered_resources: { uri: string; name: string }[];
  discovered_prompts: { name: string; description: string }[];
  discovered_kbs: { id: string; name: string; documents?: number; chunks?: number }[];
  created_at: string;
  updated_at: string;
}

interface FormData {
  name: string;
  description: string;
  url: string;
  transport: string;
  api_key: string;
  default_kb_id: string;
}

const emptyForm: FormData = {
  name: '',
  description: '',
  url: '',
  transport: 'streamable-http',
  api_key: '',
  default_kb_id: '',
};

export default function MCPSettings() {
  const { t } = useTranslation();
  const [connections, setConnections] = useState<MCPConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<FormData>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [availableKbs, setAvailableKbs] = useState<{id: string; name: string; documents?: number; chunks?: number}[]>([]);
  const [testingKbs, setTestingKbs] = useState(false);

  useEffect(() => {
    fetchConnections();
  }, []);

  async function fetchConnections() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/mcp/connections`);
      if (res.ok) {
        setConnections(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch connections:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!formData.name || !formData.url) return;
    setSaving(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/mcp/connections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        const conn = await res.json();
        setConnections(prev => [conn, ...prev]);
        setShowForm(false);
        setFormData(emptyForm);
        setAvailableKbs([]);
      } else {
        const err = await res.json();
        setError(err.detail || t('mcp.connectionFailed'));
      }
    } catch (err) {
      setError(t('mcp.networkError'));
    } finally {
      setSaving(false);
    }
  }

  async function handleTestConnection() {
    if (!formData.url) return;
    setTestingKbs(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/mcp/connections/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: formData.url, api_key: formData.api_key }),
      });

      if (res.ok) {
        const data = await res.json();
        setAvailableKbs(data.kbs || []);
        if (data.kbs && data.kbs.length > 0 && !formData.default_kb_id) {
          setFormData(p => ({ ...p, default_kb_id: data.kbs[0].id }));
        }
      } else {
        const err = await res.json();
        setError(err.detail || t('mcp.testFailed'));
      }
    } catch (err) {
      setError(t('mcp.networkError'));
    } finally {
      setTestingKbs(false);
    }
  }

  async function handleRefresh(id: string) {
    try {
      const res = await fetch(`${API_BASE}/mcp/connections/${id}/refresh`, {
        method: 'POST',
      });
      if (res.ok) {
        const conn = await res.json();
        setConnections(prev => prev.map(c => c.id === id ? conn : c));
      }
    } catch (err) {
      console.error('Failed to refresh:', err);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm(t('mcp.deleteConfirm'))) return;
    try {
      const res = await fetch(`${API_BASE}/mcp/connections/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setConnections(prev => prev.filter(c => c.id !== id));
      }
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-emerald-500';
      case 'error': return 'text-red-500';
      default: return 'text-zinc-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return <CheckCircle2 size={14} />;
      case 'error': return <XCircle size={14} />;
      default: return <Database size={14} />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-zinc-900 dark:text-white">
            {t('mcp.title')}
          </h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            {t('mcp.subtitle')}
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600
                     text-white text-sm font-medium rounded-xl transition-colors"
        >
          <Plus size={16} />
          {t('mcp.addConnection')}
        </button>
      </div>

      {/* Create Form Modal */}
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-2xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-zinc-900 dark:text-white">
                {t('mcp.newConnection')}
              </h3>
              <button
                onClick={() => { setShowForm(false); setError(null); }}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
              >
                <X size={18} />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-1.5">
                  {t('mcp.name')} *
                </label>
                <input
                  value={formData.name}
                  onChange={e => setFormData(p => ({ ...p, name: e.target.value }))}
                  placeholder={t('mcp.namePlaceholder')}
                  className="w-full bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700
                             rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white
                             placeholder-zinc-400 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-1.5">
                  {t('mcp.url')} *
                </label>
                <input
                  value={formData.url}
                  onChange={e => setFormData(p => ({ ...p, url: e.target.value }))}
                  placeholder={t('mcp.urlPlaceholder')}
                  className="w-full bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700
                             rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white
                             placeholder-zinc-400 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-1.5">
                  {t('mcp.transport')}
                </label>
                <select
                  value={formData.transport}
                  onChange={e => setFormData(p => ({ ...p, transport: e.target.value }))}
                  className="w-full bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700
                             rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white
                             focus:outline-none focus:border-indigo-500"
                >
                  <option value="streamable-http">Streamable HTTP</option>
                  <option value="stdio">STDIO</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-1.5">
                  {t('mcp.apiKey')}
                </label>
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={formData.api_key}
                    onChange={e => setFormData(p => ({ ...p, api_key: e.target.value }))}
                    placeholder={t('mcp.apiKeyPlaceholder')}
                    className="w-full bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700
                               rounded-lg px-3 py-2 pr-10 text-sm text-zinc-900 dark:text-white
                               placeholder-zinc-400 focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                  >
                    {showApiKey ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              {/* Test connection button */}
              <div className="md:col-span-2">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={!formData.url || testingKbs}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium
                             bg-zinc-200 dark:bg-zinc-700 hover:bg-zinc-300 dark:hover:bg-zinc-600
                             disabled:bg-zinc-100 dark:disabled:bg-zinc-800 disabled:text-zinc-400
                             text-zinc-700 dark:text-zinc-300 rounded-lg transition-colors"
                >
                  {testingKbs ? <Loader2 size={12} className="animate-spin" /> : <Database size={12} />}
                  {testingKbs ? t('mcp.testingKb') : t('mcp.testKb')}
                </button>
              </div>

              {/* KB Selection - shown after testing */}
              {availableKbs.length > 0 && (
                <div className="md:col-span-2">
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-1.5">
                    {t('mcp.knowledgeBase')}
                  </label>
                  <select
                    value={formData.default_kb_id}
                    onChange={e => setFormData(p => ({ ...p, default_kb_id: e.target.value }))}
                    className="w-full bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700
                               rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white
                               focus:outline-none focus:border-indigo-500"
                  >
                    {availableKbs.map(kb => (
                      <option key={kb.id} value={kb.id}>
                        {kb.name} {kb.documents !== undefined ? `(${kb.documents} ${t('mcp.docs')})` : ''}
                      </option>
                    ))}
                  </select>
                  <p className="text-[10px] text-emerald-500 mt-1">
                    {t('mcp.kbSelected')} {availableKbs.find(k => k.id === formData.default_kb_id)?.name || '—'}
                  </p>
                </div>
              )}

              <div className="md:col-span-2">
                <label className="block text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-1.5">
                  {t('mcp.description')}
                </label>
                <textarea
                  value={formData.description}
                  onChange={e => setFormData(p => ({ ...p, description: e.target.value }))}
                  placeholder={t('mcp.descriptionPlaceholder')}
                  rows={2}
                  className="w-full bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700
                             rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white
                             placeholder-zinc-400 focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>
            </div>

            {error && (
              <div className="mt-3 p-3 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-lg">
                <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => { setShowForm(false); setError(null); }}
                className="px-4 py-2 text-sm text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
              >
                {t('general.cancel')}
              </button>
              <button
                onClick={handleCreate}
                disabled={!formData.name || !formData.url || saving}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600
                           disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-zinc-500
                           text-white text-sm font-medium rounded-lg transition-colors"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Database size={14} />}
                {saving ? t('mcp.connecting') : t('mcp.testSave')}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Connections List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={24} className="animate-spin text-zinc-400" />
        </div>
      ) : connections.length === 0 ? (
        <div className="text-center py-12 bg-zinc-50 dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800">
          <Database size={32} className="mx-auto mb-3 text-zinc-300 dark:text-zinc-600" />
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{t('mcp.noConnections')}</p>
          <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-1">
            {t('mcp.noConnectionsDesc')}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {connections.map((conn) => (
            <motion.div
              key={conn.id}
              layout
              className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden"
            >
              {/* Connection Header */}
              <div
                className="flex items-center gap-4 p-4 cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors"
                onClick={() => setExpandedId(expandedId === conn.id ? null : conn.id)}
              >
                <div className={`${getStatusColor(conn.health_status)}`}>
                  {getStatusIcon(conn.health_status)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-zinc-900 dark:text-white">
                      {conn.name}
                    </span>
                    {!conn.is_active && (
                      <span className="text-[9px] px-1.5 py-0.5 bg-zinc-200 dark:bg-zinc-700 text-zinc-500 rounded">
                        {t('mcp.inactive')}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate">
                    {conn.url}
                  </div>
                </div>

                <div className="flex items-center gap-3 text-[10px] text-zinc-500">
                  <span className="flex items-center gap-1">
                    <Wrench size={10} />
                    {conn.discovered_tools.length}
                  </span>
                  <span className="flex items-center gap-1">
                    <FileText size={10} />
                    {conn.discovered_resources.length}
                  </span>
                  <span className="flex items-center gap-1">
                    <MessageSquare size={10} />
                    {conn.discovered_prompts.length}
                  </span>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRefresh(conn.id); }}
                    className="p-1.5 rounded-lg hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-400 transition-colors"
                    title={t('mcp.refresh')}
                  >
                    <RefreshCw size={14} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(conn.id); }}
                    className="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-500/10 text-zinc-400 hover:text-red-500 transition-colors"
                    title={t('mcp.delete')}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Expanded Details */}
              <AnimatePresence>
                {expandedId === conn.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="border-t border-zinc-200 dark:border-zinc-800"
                  >
                    <div className="p-4 space-y-4">
                      {conn.description && (
                        <p className="text-xs text-zinc-500 dark:text-zinc-400">
                          {conn.description}
                        </p>
                      )}

                      {/* Tools */}
                      {conn.discovered_tools.length > 0 && (
                        <div>
                          <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-2">
                            {t('mcp.tools')} ({conn.discovered_tools.length})
                          </h4>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {conn.discovered_tools.map((tool, i) => (
                              <div key={i} className="p-2 bg-white dark:bg-zinc-800 rounded-lg border border-zinc-200 dark:border-zinc-700">
                                <div className="text-xs font-mono font-medium text-indigo-600 dark:text-indigo-400">
                                  {tool.name}
                                </div>
                                {tool.description && (
                                  <div className="text-[10px] text-zinc-500 mt-0.5 line-clamp-2">
                                    {tool.description}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Resources */}
                      {conn.discovered_resources.length > 0 && (
                        <div>
                          <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-2">
                            {t('mcp.resources')} ({conn.discovered_resources.length})
                          </h4>
                          <div className="space-y-1">
                            {conn.discovered_resources.map((res, i) => (
                              <div key={i} className="text-xs font-mono text-zinc-600 dark:text-zinc-300">
                                <span className="text-emerald-500">{res.uri}</span>
                                {res.name && <span className="text-zinc-400 ml-2">({res.name})</span>}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Prompts */}
                      {conn.discovered_prompts.length > 0 && (
                        <div>
                          <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-2">
                            {t('mcp.prompts')} ({conn.discovered_prompts.length})
                          </h4>
                          <div className="space-y-1">
                            {conn.discovered_prompts.map((prompt, i) => (
                              <div key={i} className="text-xs">
                                <span className="font-mono text-purple-500">{prompt.name}</span>
                                {prompt.description && (
                                  <span className="text-zinc-400 ml-2">{prompt.description}</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Connection Info */}
                      <div className="text-[10px] text-zinc-400">
                        <span>{t('mcp.transportLabel')}: {conn.transport}</span>
                        <span className="mx-2">•</span>
                        <span>{t('mcp.status')}: {conn.health_status}</span>
                        {conn.last_health_check && (
                          <>
                            <span className="mx-2">•</span>
                            <span>{t('mcp.lastCheck')}: {new Date(conn.last_health_check).toLocaleString()}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
