'use client';
import React, { useEffect, useState } from 'react';
import { GitBranch, Clock, FileCode2, Trash2, ExternalLink, Search } from 'lucide-react';
import { ApiService } from '../../lib/api';
import type { SessionHistoryItem } from '../../types';

interface HistoryTimelineProps {
  onSelectHistoryItem: (item: SessionHistoryItem) => void;
}

export const HistoryTimeline: React.FC<HistoryTimelineProps> = ({ onSelectHistoryItem }) => {
  const [items, setItems] = useState<SessionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchHistory = async (q = '') => {
    setLoading(true);
    try {
      const API_BASE = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';
      const url = q ? `${API_BASE}/api/sessions?q=${encodeURIComponent(q)}` : `${API_BASE}/api/sessions`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        const mapped: SessionHistoryItem[] = data.map((r: any) => ({
          id: String(r.id),
          repoUrl: r.repo_url,
          repoName: r.repo_name.split('/').pop() || r.repo_name,
          owner: r.repo_name.split('/')[0] || '',
          timestamp: r.created_at,
          status: r.status,
          language: r.language,
          fileCount: r.file_count,
          licenseSpdx: r.source_license,
          recreationPromptSnippet: r.generated_prompt?.slice(0, 120) || '',
          sessionId: r.id,
        }));
        setItems(mapped);
        return;
      }
    } catch { /* fallback */ }
    const fallback = await ApiService.getHistory();
    setItems(fallback);
  };

  useEffect(() => { fetchHistory(); }, []);

  const handleDelete = async (item: SessionHistoryItem, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!item.sessionId) return;
    setDeleting(String(item.sessionId));
    try {
      const API_BASE = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${API_BASE}/api/sessions/${item.sessionId}`, { method: 'DELETE' });
      setItems((prev) => prev.filter((i) => i.id !== item.id));
    } finally {
      setDeleting(null);
    }
  };

  const filtered = items.filter((i) =>
    !search || i.repoName.toLowerCase().includes(search.toLowerCase()) ||
    i.owner.toLowerCase().includes(search.toLowerCase()) ||
    i.language.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* Pane Header */}
      <div className="pane-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Clock size={13} style={{ color: 'var(--color-cyan)' }} />
          <span className="pane-title">Analysis History</span>
        </div>
        <div style={{ position: 'relative', width: 220 }}>
          <Search size={12} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-cyan)', pointerEvents: 'none' }} />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); fetchHistory(e.target.value); }}
            placeholder="Filter sessions…"
            className="input input-mono"
            style={{ paddingLeft: 26, height: 26, fontSize: 11 }}
          />
        </div>
      </div>

      {/* Pane Scrollable Data Table */}
      <div className="pane-scroll" style={{ padding: 16 }}>
        <div className="card" style={{ overflow: 'hidden' }}>
          <table className="table">
            <thead>
              <tr>
                <th>Repository</th>
                <th>Language</th>
                <th>Files</th>
                <th>License</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} style={{ padding: 32, textAlign: 'center', color: 'var(--color-mute)' }}>
                    Loading session history records…
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: 40, textAlign: 'center', color: 'var(--color-mute)' }}>
                    <div style={{ width: 36, height: 36, background: 'var(--color-elevated)', border: '1px solid var(--color-hairline)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 8px' }}>
                      <Clock size={16} style={{ color: 'var(--color-cyan)' }} />
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-ink)' }}>No Sessions Found</div>
                    <div style={{ fontSize: 11 }}>Analyze a repository to view history records here.</div>
                  </td>
                </tr>
              ) : (
                filtered.map((item) => (
                  <tr key={item.id} onClick={() => onSelectHistoryItem(item)}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 22, height: 22, borderRadius: 4, background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <GitBranch size={11} style={{ color: 'var(--color-cyan)' }} />
                        </div>
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-ink)' }}>
                            {item.owner}/{item.repoName}
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--color-faint)', fontFamily: 'var(--font-mono)' }}>
                            {item.timestamp}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-blue">{item.language}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: 11, color: 'var(--color-body)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        <FileCode2 size={11} /> {item.fileCount}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-green">{item.licenseSpdx}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: 4 }} onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={(e) => handleDelete(item, e)}
                          className="btn btn-ghost"
                          style={{ height: 24, padding: '0 6px' }}
                          title="Delete session"
                          disabled={deleting === String(item.sessionId)}
                        >
                          <Trash2 size={11} style={{ color: 'var(--color-red)' }} />
                        </button>
                        <a
                          href={item.repoUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-ghost"
                          style={{ height: 24, padding: '0 6px' }}
                        >
                          <ExternalLink size={11} />
                        </a>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
