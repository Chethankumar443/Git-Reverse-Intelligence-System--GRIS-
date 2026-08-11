'use client';
import React, { useEffect, useState } from 'react';
import { X, Cpu, CheckCircle2, AlertCircle, Loader2, Save, ChevronDown } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Config {
  provider_preset?: string;
  base_url?: string;
  model_id?: string;
  has_api_key?: boolean;
  has_github_token?: boolean;
  daily_spend_limit_usd?: number;
  monthly_spend_limit_usd?: number;
  spend_limit_action?: string;
}

const PROVIDERS = [
  { id: 'OpenRouter',  label: 'OpenRouter', url: 'https://openrouter.ai/api/v1', hint: 'sk-or-v1-...' },
  { id: 'OpenAI',     label: 'OpenAI',     url: 'https://api.openai.com/v1',    hint: 'sk-...' },
  { id: 'Groq',       label: 'Groq',       url: 'https://api.groq.com/openai/v1', hint: 'gsk_...' },
  { id: 'DeepSeek',   label: 'DeepSeek',   url: 'https://api.deepseek.com/v1', hint: 'sk-...' },
  { id: 'Custom',     label: 'Custom',     url: '',                              hint: 'API key' },
];

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [config, setConfig] = useState<Config>({});
  const [apiKey, setApiKey] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [modelId, setModelId] = useState('');
  const [baseUrl, setBaseUrl] = useState('https://api.openai.com/v1');
  const [provider, setProvider] = useState('OpenAI');
  const [models, setModels] = useState<string[]>([]);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const API_BASE = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!isOpen) return;
    fetch(`${API_BASE}/api/config`).then((r) => r.json()).then((c: Config) => {
      setConfig(c);
      setProvider(c.provider_preset || 'OpenAI');
      setBaseUrl(c.base_url || 'https://api.openai.com/v1');
      setModelId(c.model_id || '');
    }).catch(() => {});
    fetch(`${API_BASE}/api/config/models`).then((r) => r.json()).then((d) => {
      setModels(d.models || []);
    }).catch(() => {});
  }, [isOpen]);

  useEffect(() => {
    const preset = PROVIDERS.find((p) => p.id === provider);
    if (preset && preset.url) setBaseUrl(preset.url);
  }, [provider]);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/config/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey || undefined, base_url: baseUrl, model_id: modelId }),
      });
      const data = await res.json();
      setTestResult(data);
    } catch {
      setTestResult({ ok: false, message: 'Connection failed — backend not running.' });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: any = { provider_preset: provider, base_url: baseUrl, model_id: modelId };
      if (apiKey) payload.api_key = apiKey;
      if (githubToken) payload.github_token = githubToken;
      await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 100,
          background: 'rgba(0,0,0,0.32)',
          backdropFilter: 'blur(4px)',
        }}
      />

      {/* Modal */}
      <div
        className="g-card-elevated"
        style={{
          position: 'fixed',
          top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 101,
          width: '100%', maxWidth: 540,
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: 0,
          borderRadius: 'var(--r-lg)',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '16px 24px',
            borderBottom: '1px solid var(--hairline)',
          }}
        >
          <div>
            <p className="g-eyebrow" style={{ marginBottom: 2 }}>Configuration</p>
            <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--ink)', margin: 0, letterSpacing: '-0.02em' }}>
              Settings
            </h2>
          </div>
          <button onClick={onClose} className="g-btn-ghost" style={{ padding: '0 8px' }}>
            <X size={16} />
          </button>
        </div>

        <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 28 }}>

          {/* Provider */}
          <div>
            <p className="g-eyebrow" style={{ marginBottom: 10 }}>LLM Provider</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setProvider(p.id)}
                  style={{
                    padding: '5px 14px',
                    borderRadius: 'var(--r-pill-cat)',
                    border: '1px solid',
                    borderColor: provider === p.id ? 'var(--ink)' : 'var(--hairline)',
                    background: provider === p.id ? 'var(--ink)' : 'var(--canvas-elevated)',
                    color: provider === p.id ? '#fff' : 'var(--body)',
                    fontSize: 13,
                    fontFamily: 'var(--font-sans)',
                    fontWeight: provider === p.id ? 500 : 400,
                    cursor: 'pointer',
                    transition: 'all 0.12s',
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Base URL */}
          {provider === 'Custom' && (
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: 'var(--ink)', marginBottom: 6 }}>
                API Base URL
              </label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1"
                className="g-input"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
              />
            </div>
          )}

          {/* API Key */}
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: 'var(--ink)', marginBottom: 6 }}>
              API Key
              {config.has_api_key && (
                <span className="g-badge g-badge-success" style={{ marginLeft: 8, fontSize: 11 }}>
                  <CheckCircle2 size={10} /> Key saved
                </span>
              )}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={config.has_api_key ? '••••••••••••• (saved — paste to replace)' : PROVIDERS.find((p) => p.id === provider)?.hint || 'API key'}
              className="g-input"
              style={{ fontFamily: 'var(--font-mono)', fontSize: 13 }}
            />
            <p className="g-body-sm" style={{ marginTop: 4 }}>
              Stored in OS Credential Manager — never sent to remote servers.
            </p>
          </div>

          {/* Model */}
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: 'var(--ink)', marginBottom: 6 }}>
              Model
            </label>
            {models.length > 0 ? (
              <div style={{ position: 'relative' }}>
                <select
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  className="g-input"
                  style={{ appearance: 'none', paddingRight: 36, fontFamily: 'var(--font-mono)', fontSize: 12 }}
                >
                  {models.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
                <ChevronDown size={14} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--mute)', pointerEvents: 'none' }} />
              </div>
            ) : (
              <input
                type="text"
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
                placeholder="e.g. gpt-4o or openai/gpt-4o"
                className="g-input"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
              />
            )}
          </div>

          {/* GitHub token */}
          <div>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: 'var(--ink)', marginBottom: 6 }}>
              GitHub Token <span style={{ fontWeight: 400, color: 'var(--mute)' }}>(optional — increases rate limit)</span>
              {config.has_github_token && (
                <span className="g-badge g-badge-success" style={{ marginLeft: 8, fontSize: 11 }}>
                  <CheckCircle2 size={10} /> Token saved
                </span>
              )}
            </label>
            <input
              type="password"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              placeholder="ghp_..."
              className="g-input"
              style={{ fontFamily: 'var(--font-mono)', fontSize: 13 }}
            />
          </div>

          {/* Test connection */}
          {testResult && (
            <div
              className={`g-badge ${testResult.ok ? 'g-badge-success' : 'g-badge-error'}`}
              style={{ padding: '8px 14px', borderRadius: 'var(--r-sm)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}
            >
              {testResult.ok
                ? <CheckCircle2 size={14} />
                : <AlertCircle size={14} />
              }
              {testResult.message}
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div
          style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '14px 24px',
            borderTop: '1px solid var(--hairline)',
            background: 'var(--hairline-soft)',
            gap: 10,
          }}
        >
          <button onClick={handleTest} className="g-btn-ghost" disabled={testing} style={{ gap: 6 }}>
            {testing ? <Loader2 size={13} className="animate-spin" /> : <Cpu size={13} />}
            Test Connection
          </button>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={onClose} className="g-btn-ghost">Cancel</button>
            <button onClick={handleSave} className="g-btn-sm" disabled={saving} style={{ gap: 5 }}>
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              {saved ? 'Saved!' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
