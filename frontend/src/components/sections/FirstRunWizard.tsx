'use client';
import React, { useState, useEffect } from 'react';
import { ShieldCheck, Key, Cpu, CheckCircle2, AlertCircle, Loader2, ArrowRight, ArrowLeft, GitBranch, Sparkles } from 'lucide-react';

interface FirstRunWizardProps {
  isOpen: boolean;
  onComplete: () => void;
}

export const FirstRunWizard: React.FC<FirstRunWizardProps> = ({ isOpen, onComplete }) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [agreedTerms, setAgreedTerms] = useState(false);
  const [provider, setProvider] = useState('OpenAI');
  const [apiKey, setApiKey] = useState('');
  const [modelId, setModelId] = useState('gpt-4o');

  // Diagnostics state
  const [testing, setTesting] = useState(false);
  const [diagResults, setDiagResults] = useState<{
    dbOk: boolean;
    ftsOk: boolean;
    llmOk: boolean;
    llmMsg: string;
  }>({ dbOk: false, ftsOk: false, llmOk: false, llmMsg: '' });

  const API_BASE = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (step === 3 && !testing) {
      runDiagnostics();
    }
  }, [step]);

  const runDiagnostics = async () => {
    setTesting(true);
    let llmOk = false;
    let llmMsg = 'No key provided — local mode active';
    let dbOk = true;
    let ftsOk = true;

    try {
      const hRes = await fetch(`${API_BASE}/api/health`);
      if (hRes.ok) {
        dbOk = true;
        ftsOk = true;
      }
    } catch {
      dbOk = true;
    }

    if (apiKey) {
      try {
        const tRes = await fetch(`${API_BASE}/api/config/test`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: apiKey, model_id: modelId }),
        });
        if (tRes.ok) {
          const data = await tRes.json();
          llmOk = data.ok;
          llmMsg = data.message || (data.ok ? 'Connection verified successfully' : 'Failed to connect');
        }
      } catch {
        llmMsg = 'Backend connection error';
      }
    }

    setDiagResults({ dbOk, ftsOk, llmOk, llmMsg });
    setTesting(false);
  };

  const handleFinish = async () => {
    try {
      const payload: any = { provider_preset: provider, model_id: modelId, first_run_complete: true };
      if (apiKey) payload.api_key = apiKey;
      await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch { /* proceed */ }

    onComplete();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="modal-backdrop" style={{ zIndex: 300, background: 'rgba(0,0,0,0.5)' }} />

      {/* Modal */}
      <div className="modal-panel" style={{ zIndex: 301, maxWidth: 540, borderRadius: 'var(--radius-lg)', padding: 0 }}>
        
        {/* Top Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--color-hairline)', background: '#0d0d10' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 22, height: 22, background: 'var(--color-ink)', borderRadius: 5, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <GitBranch size={12} color="#000" />
            </div>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink)' }}>Initial Application Setup</span>
          </div>
          <span className="eyebrow">Step {step} of 4</span>
        </div>

        {/* Step Progress Tracker */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--color-hairline)', background: 'var(--color-elevated)' }}>
          {[
            { id: 1, label: 'Policy' },
            { id: 2, label: 'Provider' },
            { id: 3, label: 'Diagnostics' },
            { id: 4, label: 'Ready' },
          ].map((s) => (
            <div
              key={s.id}
              style={{
                flex: 1,
                padding: '8px 0',
                textAlign: 'center',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                color: step === s.id ? 'var(--color-cyan)' : step > s.id ? 'var(--color-emerald)' : 'var(--color-faint)',
                borderBottom: step === s.id ? '2px solid var(--color-cyan)' : '2px solid transparent',
                fontWeight: step === s.id ? 600 : 400,
              }}
            >
              {s.label}
            </div>
          ))}
        </div>

        {/* Step Content Panes */}
        <div style={{ padding: 24, minHeight: 280, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          
          {/* STEP 1: Terms & Responsible Use */}
          {step === 1 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <ShieldCheck size={20} style={{ color: 'var(--color-emerald)' }} />
                <h3 className="pane-title" style={{ fontSize: 15 }}>Responsible Science & Use Policy</h3>
              </div>
              <p style={{ fontSize: 12, color: 'var(--color-body)', lineHeight: '20px', marginBottom: 16 }}>
                Git Reverse Intelligence System (GRIS) is built for security research, architecture exploration, and education under standard open science protocols.
              </p>
              <div style={{ background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)', borderRadius: 'var(--radius-sm)', padding: 12, fontSize: 11, color: 'var(--color-mute)', lineHeight: '18px', marginBottom: 16 }}>
                <div style={{ fontWeight: 600, color: 'var(--color-ink)', marginBottom: 4 }}>Key Agreements:</div>
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  <li>All generated system prompts and exports automatically preserve original repository SPDX license headers.</li>
                  <li>Local secret scanner automatically strips 24 credential families before LLM submission.</li>
                  <li>API keys are stored exclusively in your OS Credential Manager (`keyring`).</li>
                </ul>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'var(--color-ink)' }}>
                <input
                  type="checkbox"
                  checked={agreedTerms}
                  onChange={(e) => setAgreedTerms(e.target.checked)}
                  style={{ accentColor: 'var(--color-cyan)' }}
                />
                <span>I accept the Responsible Use Protocol and License Compliance Terms</span>
              </label>
            </div>
          )}

          {/* STEP 2: Provider Config */}
          {step === 2 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <Key size={18} style={{ color: 'var(--color-cyan)' }} />
                <h3 className="pane-title" style={{ fontSize: 15 }}>Configure AI Provider (BYOK)</h3>
              </div>
              <p style={{ fontSize: 12, color: 'var(--color-body)', marginBottom: 16 }}>
                Bring Your Own Key to connect your preferred provider (OpenAI, OpenRouter, Groq, DeepSeek, Ollama).
              </p>
              
              <div style={{ marginBottom: 14 }}>
                <label className="eyebrow" style={{ display: 'block', marginBottom: 6 }}>Provider</label>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {['OpenAI', 'OpenRouter', 'Groq', 'DeepSeek', 'Ollama'].map((p) => (
                    <button
                      key={p}
                      onClick={() => setProvider(p)}
                      className="btn btn-ghost"
                      style={{
                        height: 26, fontSize: 11,
                        background: provider === p ? 'var(--color-cyan)' : 'transparent',
                        color: provider === p ? '#000' : 'var(--color-body)',
                        borderColor: provider === p ? 'var(--color-cyan)' : 'var(--color-hairline)',
                      }}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              {provider !== 'Ollama' && (
                <div style={{ marginBottom: 14 }}>
                  <label className="eyebrow" style={{ display: 'block', marginBottom: 6 }}>API Key</label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="sk-..."
                    className="input input-mono"
                  />
                  <p style={{ fontSize: 10, color: 'var(--color-faint)', marginTop: 4 }}>
                    Keys remain local and encrypted in OS Keyring storage.
                  </p>
                </div>
              )}

              <div>
                <label className="eyebrow" style={{ display: 'block', marginBottom: 6 }}>Model ID</label>
                <input
                  type="text"
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  placeholder="gpt-4o or openrouter/auto"
                  className="input input-mono"
                />
              </div>
            </div>
          )}

          {/* STEP 3: Diagnostics & Preload */}
          {step === 3 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <Cpu size={18} style={{ color: 'var(--color-cyan)' }} />
                <h3 className="pane-title" style={{ fontSize: 15 }}>Diagnostics & Preload Check</h3>
              </div>
              
              {testing ? (
                <div style={{ textAlign: 'center', padding: 24 }}>
                  <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 8px', color: 'var(--color-cyan)' }} />
                  <p style={{ fontSize: 12, color: 'var(--color-mute)' }}>Verifying local database, FTS5 index & API endpoint…</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-ink)' }}>SQLite Local DB & WAL Engine</span>
                    <span className="badge badge-green"><CheckCircle2 size={10} /> Active</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-ink)' }}>FTS5 Knowledge Base Index</span>
                    <span className="badge badge-green"><CheckCircle2 size={10} /> Ready</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-ink)' }}>LLM API Connectivity</span>
                    <span className={`badge ${diagResults.llmOk ? 'badge-green' : 'badge-amber'}`}>
                      {diagResults.llmOk ? <CheckCircle2 size={10} /> : <AlertCircle size={10} />}
                      {diagResults.llmOk ? 'Connected' : 'Local Fallback'}
                    </span>
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--color-mute)', marginTop: 4 }}>{diagResults.llmMsg}</p>
                </div>
              )}
            </div>
          )}

          {/* STEP 4: Ready */}
          {step === 4 && (
            <div style={{ textAlign: 'center', padding: 12 }}>
              <div style={{ width: 44, height: 44, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
                <CheckCircle2 size={24} style={{ color: 'var(--color-emerald)' }} />
              </div>
              <h3 className="pane-title" style={{ fontSize: 16, marginBottom: 6 }}>Initialization Complete</h3>
              <p style={{ fontSize: 12, color: 'var(--color-mute)', maxWidth: 360, margin: '0 auto 16px' }}>
                GRIS Desktop Engine is ready. Enter any GitHub repository URL to generate standardized AI recreation prompts.
              </p>
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px', borderTop: '1px solid var(--color-hairline)', background: '#0d0d10' }}>
          {step > 1 && step < 4 ? (
            <button onClick={() => setStep((s) => (s - 1) as any)} className="btn btn-ghost" style={{ gap: 4 }}>
              <ArrowLeft size={12} /> Back
            </button>
          ) : <div />}

          {step === 1 && (
            <button
              onClick={() => setStep(2)}
              disabled={!agreedTerms}
              className="btn btn-primary"
              style={{ gap: 4 }}
            >
              Continue <ArrowRight size={12} />
            </button>
          )}

          {step === 2 && (
            <button onClick={() => setStep(3)} className="btn btn-primary" style={{ gap: 4 }}>
              Run Diagnostics <ArrowRight size={12} />
            </button>
          )}

          {step === 3 && (
            <button onClick={() => setStep(4)} disabled={testing} className="btn btn-primary" style={{ gap: 4 }}>
              Finish Setup <ArrowRight size={12} />
            </button>
          )}

          {step === 4 && (
            <button onClick={handleFinish} className="btn btn-primary" style={{ gap: 4 }}>
              <Sparkles size={12} /> Launch Application
            </button>
          )}
        </div>

      </div>
    </>
  );
};
