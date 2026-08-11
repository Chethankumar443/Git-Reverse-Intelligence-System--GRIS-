'use client';
import React, { useEffect, useState } from 'react';
import {
  GitBranch, Download, MessageSquare, ChevronRight, ExternalLink, Copy, CheckCheck,
  ShieldCheck, AlertTriangle, Loader2
} from 'lucide-react';
import { ApiService } from '../../lib/api';
import type { RepositoryAnalysis } from '../../types';

interface RepoInsightsProps {
  analysis: RepositoryAnalysis | null;
  onOpenChatWithPrompt: (prompt: string) => void;
}

const LANG_COLORS: Record<string, string> = {
  Python: '#3572A5', TypeScript: '#3178c6', JavaScript: '#f1e05a',
  Rust: '#dea584', Go: '#00add8', Java: '#b07219', 'C++': '#f34b7d',
  'C#': '#178600', Ruby: '#701516', PHP: '#4f5d95', Swift: '#f05138',
};

export const RepoInsights: React.FC<RepoInsightsProps> = ({ analysis, onOpenChatWithPrompt }) => {
  const [prompt, setPrompt] = useState<string>('');
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const [copied, setCopied] = useState(false);
  const [exporting, setExporting] = useState<'pdf' | 'markdown' | null>(null);

  useEffect(() => {
    if (!analysis) return;
    if ((analysis as any).generatedPrompt) {
      setPrompt((analysis as any).generatedPrompt);
      return;
    }
    setLoadingPrompt(true);
    ApiService.getRecreationPrompt(analysis.id)
      .then((p) => setPrompt(p.systemPrompt))
      .finally(() => setLoadingPrompt(false));
  }, [analysis?.id]);

  const copyPrompt = () => {
    if (!prompt) return;
    navigator.clipboard.writeText(prompt).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleExport = async (format: 'pdf' | 'markdown') => {
    if (!analysis?.sessionId) return;
    setExporting(format);
    try {
      const API_BASE = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_BASE}/api/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: analysis.sessionId, format }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `git-reverse-${analysis.name}.${format === 'pdf' ? 'pdf' : 'md'}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } finally {
      setExporting(null);
    }
  };

  if (!analysis) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', alignItems: 'center', justifyContent: 'center', padding: 40, textAlign: 'center' }}>
        <div style={{ width: 44, height: 44, background: 'var(--color-elevated)', border: '1px solid var(--color-hairline)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
          <GitBranch size={20} style={{ color: 'var(--color-cyan)' }} />
        </div>
        <h3 className="pane-title" style={{ fontSize: 14, marginBottom: 4 }}>No Repository Insights Loaded</h3>
        <p style={{ fontSize: 12, color: 'var(--color-mute)' }}>Reverse a repository from the Analyze tab or choose a session from History.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* Header bar */}
      <div className="pane-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="pane-title">{analysis.owner} / {analysis.name}</span>
          <span className="badge badge-cyan">{analysis.primaryLanguage}</span>
          <a
            href={analysis.url}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: 11, color: 'var(--color-cyan)', display: 'inline-flex', alignItems: 'center', gap: 3 }}
          >
            GitHub <ExternalLink size={10} />
          </a>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => onOpenChatWithPrompt(prompt)} className="btn btn-ghost" style={{ gap: 4 }}>
            <MessageSquare size={12} style={{ color: 'var(--color-cyan)' }} />
            <span>Copilot</span>
          </button>
          <button onClick={() => handleExport('markdown')} className="btn btn-ghost" style={{ gap: 4 }} disabled={exporting === 'markdown'}>
            <Download size={12} />
            <span>{exporting === 'markdown' ? 'Exporting…' : 'Markdown'}</span>
          </button>
          <button onClick={() => handleExport('pdf')} className="btn btn-primary" style={{ gap: 4 }} disabled={exporting === 'pdf'}>
            <Download size={12} />
            <span>{exporting === 'pdf' ? 'Exporting…' : 'Export PDF'}</span>
          </button>
        </div>
      </div>

      {/* Scroll Body */}
      <div className="pane-scroll" style={{ padding: 16 }}>

        {/* 4-Cell Metadata Bento Grid */}
        <div className="meta-grid meta-grid-4" style={{ marginBottom: 16 }}>
          <div className="meta-cell">
            <div className="meta-cell-label">Primary Stack</div>
            <div className="meta-cell-value" style={{ color: 'var(--color-cyan)' }}>{analysis.primaryLanguage}</div>
          </div>
          <div className="meta-cell">
            <div className="meta-cell-label">Files Analyzed</div>
            <div className="meta-cell-value">{analysis.fileCount.toLocaleString()}</div>
          </div>
          <div className="meta-cell">
            <div className="meta-cell-label">Dependencies</div>
            <div className="meta-cell-value">{analysis.dependenciesCount}</div>
          </div>
          <div className="meta-cell">
            <div className="meta-cell-label">SPDX License</div>
            <div className="meta-cell-value" style={{ color: 'var(--color-emerald)' }}>{analysis.license.spdxId}</div>
          </div>
        </div>

        {/* Main 2-Column Split: System Prompt Panel + Sidebar Context */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 16, alignItems: 'start' }}>

          {/* System Prompt Code Viewer */}
          <div className="card" style={{ overflow: 'hidden' }}>
            <div className="panel-section" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div className="eyebrow">AI System Recreation Prompt</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink)' }}>Generated Target Architecture Prompt</div>
              </div>
              <button onClick={copyPrompt} className="btn btn-ghost" style={{ gap: 4 }}>
                {copied ? <><CheckCheck size={12} style={{ color: 'var(--color-emerald)' }} /><span>Copied</span></> : <><Copy size={12} /><span>Copy</span></>}
              </button>
            </div>

            <div
              style={{
                height: 480,
                overflowY: 'auto',
                padding: 14,
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                lineHeight: '18px',
                color: 'var(--color-ink)',
                whiteSpace: 'pre-wrap',
                background: '#050507',
              }}
            >
              {loadingPrompt ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-mute)' }}>
                  <Loader2 size={13} className="animate-spin" />
                  <span>Synthesizing system recreation prompt…</span>
                </div>
              ) : prompt ? prompt : (
                <span style={{ color: 'var(--color-mute)' }}>No system prompt generated yet.</span>
              )}
            </div>
          </div>

          {/* Side Context Widgets */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

            {/* Language Breakdown */}
            <div className="card">
              <div className="panel-section">
                <div className="eyebrow" style={{ marginBottom: 8 }}>Language Composition</div>
                {analysis.languages.map((lang) => (
                  <div key={lang.name} style={{ marginBottom: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, color: 'var(--color-ink)', display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: LANG_COLORS[lang.name] || 'var(--color-mute)' }} />
                        {lang.name}
                      </span>
                      <span style={{ fontSize: 11, color: 'var(--color-mute)', fontFamily: 'var(--font-mono)' }}>
                        {lang.percentage.toFixed(1)}%
                      </span>
                    </div>
                    <div style={{ height: 3, background: 'var(--color-hairline)', borderRadius: 99, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${lang.percentage}%`, background: LANG_COLORS[lang.name] || 'var(--color-cyan)', borderRadius: 99 }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* License & Attribution Policy */}
            <div className="card">
              <div className="panel-section">
                <div className="eyebrow" style={{ marginBottom: 8 }}>License Compliance</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <ShieldCheck size={15} style={{ color: 'var(--color-emerald)' }} />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-ink)' }}>{analysis.license.spdxId}</div>
                    <div style={{ fontSize: 11, color: 'var(--color-mute)' }}>{analysis.license.name}</div>
                  </div>
                </div>
                {analysis.license.requiresAttribution && (
                  <div style={{ fontSize: 10, color: 'var(--color-amber)', display: 'flex', alignItems: 'flex-start', gap: 4, marginTop: 4 }}>
                    <AlertTriangle size={11} style={{ flexShrink: 0, marginTop: 1 }} />
                    <span>License attribution header automatically appended to exports.</span>
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="card">
              <div className="panel-section">
                <div className="eyebrow" style={{ marginBottom: 6 }}>Actions</div>
                {[
                  { label: 'Chat with Copilot', action: () => onOpenChatWithPrompt(prompt) },
                  { label: 'Export Markdown (.md)', action: () => handleExport('markdown') },
                  { label: 'Export PDF (.pdf)', action: () => handleExport('pdf') },
                ].map(({ label, action }) => (
                  <button
                    key={label}
                    onClick={action}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      width: '100%', padding: '6px 0', background: 'none', border: 'none',
                      borderBottom: '1px solid var(--color-hairline)', cursor: 'pointer',
                      fontSize: 11, color: 'var(--color-body)', textAlign: 'left',
                    }}
                  >
                    <span>{label}</span>
                    <ChevronRight size={11} style={{ color: 'var(--color-mute)' }} />
                  </button>
                ))}
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};
