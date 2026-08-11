'use client';
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Search, ArrowRight, CheckCircle2, Loader2, Terminal, Sparkles } from 'lucide-react';
import { ThinkingOrbs } from '../motion/ThinkingOrbs';
import { ApiService } from '../../lib/api';
import type { RepositoryAnalysis } from '../../types';

interface AnalyzePaneProps {
  onAnalysisStart: (repoUrl: string) => void;
  onAnalysisComplete: (result: RepositoryAnalysis) => void;
}

interface Step {
  id: string;
  label: string;
  status: 'idle' | 'running' | 'done' | 'error';
  detail: string;
}

const PRESETS = [
  'https://github.com/vercel/next.js',
  'https://github.com/fastapi/fastapi',
  'https://github.com/tauri-apps/tauri',
  'https://github.com/facebook/react',
];

export const AnalyzePane: React.FC<AnalyzePaneProps> = ({ onAnalysisStart, onAnalysisComplete }) => {
  const [url, setUrl] = useState('');
  const [depth, setDepth] = useState<'quick' | 'deep' | 'recreation'>('recreation');
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [logLines, setLogLines] = useState<string[]>([
    '[INFO] GRIS Engine v1.1.0 ready',
    '[INFO] FTS5 Knowledge Base loaded',
    '[INFO] Local secret scanner active (24 key patterns)',
    '[INFO] Awaiting target repository URL…',
  ]);
  const [metaData, setMetaData] = useState<any>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [steps, setSteps] = useState<Step[]>([
    { id: '1', label: 'URL & Permissions', status: 'idle', detail: 'Validate GitHub URL and public access' },
    { id: '2', label: 'Archive Download',  status: 'idle', detail: 'Stream repository tree and manifests' },
    { id: '3', label: 'AST & Secrets Scan', status: 'idle', detail: 'Extract language symbols, scrub keys' },
    { id: '4', label: 'Prompt Synthesis',   status: 'idle', detail: 'Stream LLM system recreation prompt' },
  ]);

  const patchStep = useCallback((idx: number, patch: Partial<Step>) => {
    setSteps(prev => prev.map((s, i) => i === idx ? { ...s, ...patch } : s));
  }, []);

  const addLog = useCallback((msg: string) => {
    setLogLines(prev => [...prev.slice(-80), msg]);
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logLines]);

  const handleStart = async (urlOverride?: string) => {
    const repoUrl = (urlOverride ?? url).trim();
    setError('');
    const v = ApiService.validateRepoUrl(repoUrl);
    if (!v.valid) { setError(v.error || 'Invalid GitHub URL format'); return; }

    setAnalyzing(true);
    setLogLines([]);
    setMetaData(null);
    setSteps(prev => prev.map(s => ({ ...s, status: 'idle' })));
    patchStep(0, { status: 'running' });
    onAnalysisStart(repoUrl);

    const API = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';

    try {
      const r = await fetch(`${API}/api/analysis/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: repoUrl, prompt_type: depth === 'quick' ? 'Quick Scan' : 'Clone Prompt' }),
      });
      if (!r.ok) throw new Error('Failed to initiate analysis job');
      const { job_id } = await r.json();

      const ws = new WebSocket(`${API.replace('http', 'ws')}/ws/analysis/${job_id}?url=${encodeURIComponent(repoUrl)}`);
      wsRef.current = ws;

      ws.onmessage = ({ data }) => {
        try {
          const ev = JSON.parse(data);
          if (ev.type === 'progress') {
            addLog(`[INFO] ${ev.msg}`);
            if (ev.msg?.includes('Validating'))  patchStep(0, { status: 'running' });
            if (ev.msg?.includes('Connecting') || ev.msg?.includes('Download')) {
              patchStep(0, { status: 'done' }); patchStep(1, { status: 'running' });
            }
            if (ev.msg?.includes('Analyzing') || ev.msg?.includes('files')) {
              patchStep(1, { status: 'done' }); patchStep(2, { status: 'running' });
            }
            if (ev.msg?.includes('Generating') || ev.msg?.includes('LLM')) {
              patchStep(2, { status: 'done' }); patchStep(3, { status: 'running' });
            }
          } else if (ev.type === 'meta') {
            setMetaData(ev.data);
            patchStep(1, { status: 'done', detail: `${ev.data.file_count} files · ${ev.data.source_license}` });
            addLog(`[OK] Detected ${ev.data.repo_name} — ${ev.data.file_count} files, license: ${ev.data.source_license}`);
          } else if (ev.type === 'progress_pct') {
            const pct = ev.total > 0 ? Math.round((ev.done / ev.total) * 100) : 0;
            patchStep(2, { status: 'running', detail: `${pct}% scanned (${ev.done}/${ev.total} files)` });
          } else if (ev.type === 'error') {
            setError(ev.msg);
            setAnalyzing(false);
            addLog(`[ERR] ${ev.msg}`);
            setSteps(prev => prev.map(s => s.status === 'running' ? { ...s, status: 'error' } : s));
          } else if (ev.type === 'done') {
            patchStep(3, { status: 'done', detail: 'Recreation prompt ready' });
            addLog('[OK] Repository intelligence processing complete.');
            const result: RepositoryAnalysis = {
              id: String(ev.session_id),
              url: repoUrl,
              owner: repoUrl.split('/')[3] || '',
              name: repoUrl.split('/')[4] || '',
              branch: metaData?.branch || 'main',
              description: '',
              starsCount: metaData?.stars || 0,
              forksCount: 0,
              primaryLanguage: metaData?.languages?.[0] || 'Unknown',
              languages: (metaData?.languages || []).map((l: string, i: number) => ({
                name: l, percentage: i === 0 ? 70 : 15, color: '#0070f3',
              })),
              fileCount: metaData?.file_count || 0,
              totalLinesOfCode: 0,
              sizeFormatted: 'N/A',
              license: { spdxId: metaData?.source_license || 'MIT', name: metaData?.source_license || 'MIT License', isCopyleft: false, requiresAttribution: true },
              dependenciesCount: metaData?.dependency_details?.length || 0,
              astModulesCount: 0,
              sessionId: ev.session_id,
              generatedPrompt: ev.prompt,
            };
            setAnalyzing(false);
            onAnalysisComplete(result);
          }
        } catch { /* JSON parse error */ }
      };
      ws.onerror = () => {
        addLog('[INFO] Using local fallback demo mode');
        ApiService.startAnalysis(repoUrl, depth).then(res => {
          setAnalyzing(false); onAnalysisComplete(res);
        });
      };
    } catch {
      addLog('[INFO] Using local fallback demo mode');
      const res = await ApiService.startAnalysis(repoUrl, depth);
      setAnalyzing(false); onAnalysisComplete(res);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* Pane Header with Asymmetric Depth Controls */}
      <div className="pane-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sparkles size={14} style={{ color: 'var(--color-cyan)' }} />
          <span className="pane-title">Analyze Repository</span>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { id: 'quick', label: 'Quick Scan' },
            { id: 'deep', label: 'Deep AST' },
            { id: 'recreation', label: 'Recreation Prompt' },
          ].map(o => (
            <button
              key={o.id}
              onClick={() => setDepth(o.id as any)}
              className="btn btn-ghost"
              style={{
                height: 24, padding: '0 8px', fontSize: 11,
                background: depth === o.id ? 'rgba(0,223,216,0.1)' : 'transparent',
                color: depth === o.id ? 'var(--color-cyan)' : 'var(--color-body)',
                borderColor: depth === o.id ? 'rgba(0,223,216,0.3)' : 'var(--color-hairline)',
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* Hero mesh gradient input bar */}
      <div className="mesh-gradient-wash" style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-hairline)' }}>
        <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-cyan)', pointerEvents: 'none' }} />
            <input
              type="text"
              value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleStart()}
              placeholder="https://github.com/owner/repository"
              className="input input-mono"
              style={{ paddingLeft: 36, height: 36, fontSize: 13, background: '#09090b', borderColor: 'var(--color-hairline)' }}
            />
          </div>
          <button
            onClick={() => handleStart()}
            disabled={analyzing || !url}
            className="btn btn-primary"
            style={{ height: 36, padding: '0 18px', gap: 6 }}
          >
            {analyzing ? (
              <ThinkingOrbs label="Analyzing…" size="sm" />
            ) : (
              <><span>Reverse Repo</span><ArrowRight size={14} /></>
            )}
          </button>
        </div>

        {error && (
          <div style={{ fontSize: 12, color: 'var(--color-red)', fontFamily: 'var(--font-mono)', marginBottom: 8 }}>
            {error}
          </div>
        )}

        {/* Presets */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span className="eyebrow" style={{ fontSize: 10 }}>Preset Repos:</span>
          {PRESETS.map(p => (
            <button
              key={p}
              onClick={() => { setUrl(p); handleStart(p); }}
              className="btn btn-ghost"
              style={{ height: 22, padding: '0 8px', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            >
              {p.replace('https://github.com/', '')}
            </button>
          ))}
        </div>
      </div>

      {/* 2-Column Split Workspace */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '260px 1fr', overflow: 'hidden' }}>

        {/* Left: Pipeline Steps */}
        <div style={{ borderRight: '1px solid var(--color-hairline)', background: '#0d0d10', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div className="panel-section" style={{ flex: 1, overflowY: 'auto' }}>
            <div className="eyebrow" style={{ marginBottom: 12 }}>Pipeline Execution</div>
            {steps.map((step, idx) => (
              <div key={step.id} style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
                <div style={{ marginTop: 2, flexShrink: 0 }}>
                  {step.status === 'done' && <CheckCircle2 size={16} style={{ color: 'var(--color-emerald)' }} />}
                  {step.status === 'running' && <Loader2 size={16} className="animate-spin" style={{ color: 'var(--color-cyan)' }} />}
                  {step.status === 'error' && <div className="status-dot error" style={{ width: 16, height: 16 }} />}
                  {step.status === 'idle' && (
                    <div style={{ width: 18, height: 18, borderRadius: '50%', border: '1px solid var(--color-hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--color-faint)' }}>
                      {idx + 1}
                    </div>
                  )}
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: step.status === 'running' ? 'var(--color-cyan)' : step.status === 'done' ? 'var(--color-ink)' : 'var(--color-mute)' }}>
                    {step.label}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-mute)', marginTop: 2 }}>{step.detail}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Meta detection card */}
          {metaData && (
            <div className="panel-section" style={{ flexShrink: 0, background: 'var(--color-canvas)' }}>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Detected Manifest</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                <span className="badge badge-cyan">{metaData.repo_name}</span>
                <span className="badge">{metaData.file_count} files</span>
                <span className="badge badge-green">{metaData.source_license}</span>
              </div>
            </div>
          )}
        </div>

        {/* Right: Live Terminal Log Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 14px', borderBottom: '1px solid var(--color-hairline)', background: '#0d0d10', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Terminal size={12} style={{ color: 'var(--color-cyan)' }} />
              <span className="eyebrow">Realtime Stream Output</span>
            </div>
            {analyzing && <div className="status-dot ok animate-pulse-glow" />}
          </div>

          <div ref={logRef} className="log-surface" style={{ flex: 1, border: 'none', borderRadius: 0 }}>
            {logLines.map((l, i) => (
              <div
                key={i}
                className={
                  l.startsWith('[ERR]')  ? 'log-line-error' :
                  l.startsWith('[OK]')   ? 'log-line-ok' :
                  l.startsWith('[WARN]') ? 'log-line-warn' :
                  l.startsWith('[INFO]') ? 'log-line-info' :
                  'log-line-mute'
                }
              >
                {l}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};
