import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Settings, Save, RotateCcw, Loader2, ChevronDown,
  ChevronRight, Check, AlertTriangle
} from 'lucide-react';
import { useTranslation } from '../i18n/LanguageContext';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8001/api/v1';

interface TemplateSection {
  id: string;
  title: string;
  required: boolean;
}

interface QualityCheck {
  id: string;
  label: string;
  enabled: boolean;
}

interface SlaKpiEntry {
  field: string;
  label: string;
}

interface SlaRules {
  expected_kpis?: SlaKpiEntry[];
  expected_kpos?: SlaKpiEntry[];
}

interface TemplateConfig {
  template_id: string;
  name: string;
  description: string;
  language?: string;
  sections: TemplateSection[];
  required_fields: { path: string; label: string; min_items?: number }[];
  sla_rules: SlaRules;
  quality_checks: QualityCheck[];
}

interface TypeInfo {
  template_id: string;
  name: string;
  description: string;
}

export default function TemplateSettings() {
  const { t } = useTranslation();
  const [types, setTypes] = useState<TypeInfo[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [config, setConfig] = useState<TemplateConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>('sections');

  // Load document types
  useEffect(() => {
    fetch(`${API_BASE}/templates/`)
      .then(r => r.json())
      .then((data: TypeInfo[]) => {
        setTypes(data);
        if (data.length > 0) setSelectedType(data[0].template_id);
      })
      .catch(console.error);
  }, []);

  // Load config when type changes
  const loadConfig = useCallback(async (docType: string) => {
    if (!docType) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/templates/${docType}/config`);
      if (res.ok) setConfig(await res.json());
    } catch (err) {
      console.error('Failed to load config:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedType) loadConfig(selectedType);
  }, [selectedType, loadConfig]);

  // Toggle section required
  const toggleSection = (sectionId: string) => {
    if (!config) return;
    setConfig({
      ...config,
      sections: config.sections.map(s =>
        s.id === sectionId ? { ...s, required: !s.required } : s
      ),
    });
  };

  // Toggle quality check
  const toggleCheck = (checkId: string) => {
    if (!config) return;
    setConfig({
      ...config,
      quality_checks: config.quality_checks.map(c =>
        c.id === checkId ? { ...c, enabled: !c.enabled } : c
      ),
    });
  };

  // (SLA rules are display-only from template.yaml)

  // Save
  const handleSave = async () => {
    if (!config || !selectedType) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/templates/${selectedType}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sections: config.sections,
          required_fields: config.required_fields,
          sla_rules: config.sla_rules,
          quality_checks: config.quality_checks,
        }),
      });
      if (res.ok) {
        setMessage({ type: 'success', text: t('template.saveSuccess') });
      } else {
        setMessage({ type: 'error', text: `${t('template.saveFailed')}: ${res.statusText}` });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `${t('template.saveFailed')}: ${err}` });
    } finally {
      setSaving(false);
    }
  };

  // Reset to defaults
  const handleReset = async () => {
    if (!selectedType) return;
    if (!confirm(t('template.resetConfirm'))) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/templates/${selectedType}/reset`, { method: 'POST' });
      if (res.ok) {
        await loadConfig(selectedType);
        setMessage({ type: 'success', text: t('template.resetSuccess') });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `${t('template.resetFailed')}: ${err}` });
    } finally {
      setSaving(false);
    }
  };

  const toggleSection_panel = (panel: string) => {
    setExpandedSection(expandedSection === panel ? null : panel);
  };

  // Required fields helpers
  const addRequiredField = () => {
    if (!config) return;
    setConfig({
      ...config,
      required_fields: [...config.required_fields, { path: '', label: '', min_items: undefined }],
    });
  };
  const updateRequiredField = (idx: number, key: string, value: string | number | undefined) => {
    if (!config) return;
    setConfig({
      ...config,
      required_fields: config.required_fields.map((f, i) =>
        i === idx ? { ...f, [key]: value } : f
      ),
    });
  };
  const removeRequiredField = (idx: number) => {
    if (!config) return;
    setConfig({
      ...config,
      required_fields: config.required_fields.filter((_, i) => i !== idx),
    });
  };

  // Validation preview state
  const [previewInput, setPreviewInput] = useState('{\n  "project": {"title": "Test"}\n}');
  const [previewResult, setPreviewResult] = useState<Record<string, unknown> | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const handleTestValidation = async () => {
    if (!selectedType) return;
    setPreviewLoading(true);
    setPreviewResult(null);
    try {
      let parsed;
      try {
        parsed = JSON.parse(previewInput);
      } catch {
        setPreviewResult({ valid: false, issues: ['JSON non valido'] });
        return;
      }
      const res = await fetch(`${API_BASE}/templates/${selectedType}/validate-preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requirements: parsed }),
      });
      if (res.ok) setPreviewResult(await res.json());
    } catch {
      setPreviewResult({ valid: false, issues: ['Errore di rete'] });
    } finally {
      setPreviewLoading(false);
    }
  };

  if (!config && loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings className="w-6 h-6 text-blue-500" />
          <h1 className="text-2xl font-bold">{t('template.title')}</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300
                       hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700 transition"
          >
            <RotateCcw className="w-4 h-4" />
            {t('template.reset')}
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white
                       hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {t('general.save')}
          </button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`flex items-center gap-2 p-3 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'
          }`}
        >
          {message.type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {message.text}
        </motion.div>
      )}

      {/* Type selector */}
      <div className="flex gap-2">
        {types.map(dt => (
          <button
            key={dt.template_id}
            onClick={() => setSelectedType(dt.template_id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              selectedType === dt.template_id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            {dt.name || dt.template_id}
          </button>
        ))}
      </div>

      {config && (
        <div className="space-y-4">
          {/* Description */}
          <p className="text-gray-500 dark:text-gray-400 text-sm">{config.description}</p>

          {/* Sections panel */}
          <div className="border rounded-lg dark:border-gray-700">
            <button
              onClick={() => toggleSection_panel('sections')}
              className="w-full flex items-center gap-2 p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              {expandedSection === 'sections' ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <span className="font-medium">{t('template.sections')}</span>
              <span className="ml-auto text-sm text-gray-400">
                {config.sections.filter(s => s.required).length}/{config.sections.length} {t('template.required')}
              </span>
            </button>
            {expandedSection === 'sections' && (
              <div className="border-t dark:border-gray-700 divide-y dark:divide-gray-700">
                {config.sections.map(section => (
                  <div key={section.id} className="flex items-center gap-3 p-3 px-6">
                    <button
                      onClick={() => toggleSection(section.id)}
                      className={`w-10 h-6 rounded-full transition relative ${
                        section.required ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                          section.required ? 'translate-x-4' : ''
                        }`}
                      />
                    </button>
                    <span className={section.required ? 'font-medium' : 'text-gray-400'}>
                      {section.title}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quality checks panel */}
          <div className="border rounded-lg dark:border-gray-700">
            <button
              onClick={() => toggleSection_panel('quality')}
              className="w-full flex items-center gap-2 p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              {expandedSection === 'quality' ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <span className="font-medium">{t('template.qualityChecks')}</span>
              <span className="ml-auto text-sm text-gray-400">
                {config.quality_checks.filter(c => c.enabled).length}/{config.quality_checks.length} {t('template.active')}
              </span>
            </button>
            {expandedSection === 'quality' && (
              <div className="border-t dark:border-gray-700 divide-y dark:divide-gray-700">
                {config.quality_checks.map(check => (
                  <div key={check.id} className="flex items-center gap-3 p-3 px-6">
                    <button
                      onClick={() => toggleCheck(check.id)}
                      className={`w-10 h-6 rounded-full transition relative ${
                        check.enabled ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                          check.enabled ? 'translate-x-4' : ''
                        }`}
                      />
                    </button>
                    <span className={check.enabled ? '' : 'text-gray-400'}>
                      {check.label}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Required Fields panel */}
          <div className="border rounded-lg dark:border-gray-700">
            <button
              onClick={() => toggleSection_panel('requiredFields')}
              className="w-full flex items-center gap-2 p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              {expandedSection === 'requiredFields' ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <span className="font-medium">{t('template.requiredFields')}</span>
              <span className="ml-auto text-sm text-gray-400">
                {config.required_fields.length} {t('template.required')}
              </span>
            </button>
            {expandedSection === 'requiredFields' && (
              <div className="border-t dark:border-gray-700 p-4 space-y-3">
                {config.required_fields.length === 0 && (
                  <p className="text-sm text-gray-400">{t('template.noFields')}</p>
                )}
                {config.required_fields.map((field, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder={t('template.fieldPath')}
                      value={field.path}
                      onChange={e => updateRequiredField(idx, 'path', e.target.value)}
                      className="flex-1 px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:border-gray-600"
                    />
                    <input
                      type="text"
                      placeholder={t('template.fieldLabel')}
                      value={field.label}
                      onChange={e => updateRequiredField(idx, 'label', e.target.value)}
                      className="flex-1 px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:border-gray-600"
                    />
                    <input
                      type="number"
                      placeholder={t('template.fieldMinItems')}
                      value={field.min_items ?? ''}
                      onChange={e => updateRequiredField(idx, 'min_items', e.target.value ? parseInt(e.target.value) : undefined)}
                      className="w-24 px-3 py-2 border rounded-lg text-sm dark:bg-gray-800 dark:border-gray-600"
                    />
                    <button
                      onClick={() => removeRequiredField(idx)}
                      className="px-2 py-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition"
                      title={t('template.removeField')}
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <button
                  onClick={addRequiredField}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 transition"
                >
                  + {t('template.addField')}
                </button>
              </div>
            )}
          </div>

          {/* Validation Preview panel */}
          <div className="border rounded-lg dark:border-gray-700">
            <button
              onClick={() => toggleSection_panel('validationPreview')}
              className="w-full flex items-center gap-2 p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              {expandedSection === 'validationPreview' ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <span className="font-medium">{t('template.validationPreview')}</span>
            </button>
            {expandedSection === 'validationPreview' && (
              <div className="border-t dark:border-gray-700 p-4 space-y-3">
                <textarea
                  value={previewInput}
                  onChange={e => setPreviewInput(e.target.value)}
                  rows={6}
                  className="w-full px-3 py-2 border rounded-lg text-sm font-mono dark:bg-gray-800 dark:border-gray-600"
                  placeholder={t('template.testRequirements')}
                />
                <button
                  onClick={handleTestValidation}
                  disabled={previewLoading}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 transition"
                >
                  {previewLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  {t('template.testValidation')}
                </button>
                {previewResult && (
                  <div className={`p-3 rounded-lg text-sm ${
                    previewResult.valid
                      ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  }`}>
                    <p className="font-medium mb-2">
                      {previewResult.valid ? t('template.validResult') : t('template.invalidResult')}
                    </p>
                    {previewResult.confidence !== undefined && (
                      <p>{t('template.confidence')}: {(previewResult.confidence as number * 100).toFixed(0)}%</p>
                    )}
                    {(previewResult.missing_fields as string[])?.length > 0 && (
                      <p>{t('template.missingFields')}: {(previewResult.missing_fields as string[]).join(', ')}</p>
                    )}
                    {(previewResult.issues as string[])?.length > 0 && (
                      <div className="mt-1">
                        <p className="font-medium">{t('template.issues')}:</p>
                        <ul className="list-disc ml-4">
                          {(previewResult.issues as string[]).map((issue, i) => <li key={i}>{issue}</li>)}
                        </ul>
                      </div>
                    )}
                    {(previewResult.warnings as string[])?.length > 0 && (
                      <div className="mt-1">
                        <p className="font-medium">{t('template.warnings')}:</p>
                        <ul className="list-disc ml-4">
                          {(previewResult.warnings as string[]).map((w, i) => <li key={i}>{w}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* SLA rules panel */}
          <div className="border rounded-lg dark:border-gray-700">
            <button
              onClick={() => toggleSection_panel('sla')}
              className="w-full flex items-center gap-2 p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              {expandedSection === 'sla' ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <span className="font-medium">{t('template.slaRules')}</span>
            </button>
            {expandedSection === 'sla' && config.sla_rules && (
              <div className="border-t dark:border-gray-700 p-4">
                {/* KPIs */}
                <div className="mb-4">
                  <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-400 mb-2">
                    KPI — {t('template.kpiRequired')}
                  </p>
                  {config.sla_rules.expected_kpis && config.sla_rules.expected_kpis.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-zinc-400 text-[10px] uppercase tracking-widest">
                            <th className="py-2 pr-4">ID</th>
                            <th className="py-2">{t('template.kpiLabel')}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y dark:divide-zinc-800">
                          {config.sla_rules.expected_kpis.map((kpi, i) => (
                            <tr key={i}>
                              <td className="py-2 pr-4 font-mono text-indigo-500">{kpi.field}</td>
                              <td className="py-2 text-zinc-700 dark:text-zinc-300">{kpi.label}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-zinc-400">—</p>
                  )}
                </div>
                {/* KPOs */}
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-400 mb-2">
                    KPO — {t('template.kpoTarget')}
                  </p>
                  {config.sla_rules.expected_kpos && config.sla_rules.expected_kpos.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-zinc-400 text-[10px] uppercase tracking-widest">
                            <th className="py-2 pr-4">ID</th>
                            <th className="py-2">{t('template.kpoTarget')}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y dark:divide-zinc-800">
                          {config.sla_rules.expected_kpos.map((kpo, i) => (
                            <tr key={i}>
                              <td className="py-2 pr-4 font-mono text-indigo-500">{kpo.field}</td>
                              <td className="py-2 text-zinc-700 dark:text-zinc-300">{kpo.label}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-zinc-400">—</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
