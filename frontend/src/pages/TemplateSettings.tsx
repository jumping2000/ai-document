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

interface SlaRules {
  availability?: { min?: number; max?: number };
  rto_gt_rpo?: boolean;
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

  // Update SLA rules
  const updateSla = (field: string, value: string | boolean) => {
    if (!config) return;
    const sla = { ...config.sla_rules };
    if (field === 'availability_min') {
      sla.availability = { ...sla.availability, min: parseFloat(value as string) || 0 };
    } else if (field === 'availability_max') {
      sla.availability = { ...sla.availability, max: parseFloat(value as string) || 0 };
    } else if (field === 'rto_gt_rpo') {
      sla.rto_gt_rpo = value as boolean;
    }
    setConfig({ ...config, sla_rules: sla });
  };

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
          sla_rules: config.sla_rules,
          quality_checks: config.quality_checks,
        }),
      });
      if (res.ok) {
        setMessage({ type: 'success', text: 'Configuration saved successfully' });
      } else {
        setMessage({ type: 'error', text: `Save failed: ${res.statusText}` });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `Save failed: ${err}` });
    } finally {
      setSaving(false);
    }
  };

  // Reset to defaults
  const handleReset = async () => {
    if (!selectedType) return;
    if (!confirm('Reset to default configuration? This will delete your customizations.')) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/templates/${selectedType}/reset`, { method: 'POST' });
      if (res.ok) {
        await loadConfig(selectedType);
        setMessage({ type: 'success', text: 'Configuration reset to defaults' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: `Reset failed: ${err}` });
    } finally {
      setSaving(false);
    }
  };

  const toggleSection_panel = (panel: string) => {
    setExpandedSection(expandedSection === panel ? null : panel);
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
          <h1 className="text-2xl font-bold">Template Configuration</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300
                       hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700 transition"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white
                       hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save
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
              <span className="font-medium">Sections</span>
              <span className="ml-auto text-sm text-gray-400">
                {config.sections.filter(s => s.required).length}/{config.sections.length} required
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
              <span className="font-medium">Quality Checks</span>
              <span className="ml-auto text-sm text-gray-400">
                {config.quality_checks.filter(c => c.enabled).length}/{config.quality_checks.length} active
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

          {/* SLA rules panel */}
          <div className="border rounded-lg dark:border-gray-700">
            <button
              onClick={() => toggleSection_panel('sla')}
              className="w-full flex items-center gap-2 p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              {expandedSection === 'sla' ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <span className="font-medium">SLA Rules</span>
            </button>
            {expandedSection === 'sla' && (
              <div className="border-t dark:border-gray-700 p-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Availability Min (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={config.sla_rules.availability?.min ?? 95}
                      onChange={e => updateSla('availability_min', e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Availability Max (%)</label>
                    <input
                      type="number"
                      step="0.001"
                      value={config.sla_rules.availability?.max ?? 99.999}
                      onChange={e => updateSla('availability_max', e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-600"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => updateSla('rto_gt_rpo', !config.sla_rules.rto_gt_rpo)}
                    className={`w-10 h-6 rounded-full transition relative ${
                      config.sla_rules.rto_gt_rpo ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                        config.sla_rules.rto_gt_rpo ? 'translate-x-4' : ''
                      }`}
                    />
                  </button>
                  <span>RTO must be greater than RPO</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
