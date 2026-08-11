'use client';
import React from 'react';
import { Search, GitBranch, MessageSquare, Clock, ShieldCheck } from 'lucide-react';
import type { RepositoryAnalysis } from '../../types';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  currentAnalysis: RepositoryAnalysis | null;
}

const NAV_ITEMS = [
  { id: 'analyze',  label: 'Analyze',  icon: Search,        shortcut: '⌘1' },
  { id: 'insights', label: 'Insights', icon: GitBranch,     shortcut: '⌘2' },
  { id: 'chat',     label: 'Copilot',  icon: MessageSquare, shortcut: '⌘3' },
  { id: 'history',  label: 'History',  icon: Clock,         shortcut: '⌘4' },
];

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, currentAnalysis }) => {
  return (
    <aside className="app-sidebar">
      <nav style={{ flex: 1, paddingTop: 10, overflow: 'hidden auto' }}>
        <div className="nav-section">Workspace</div>

        {NAV_ITEMS.map(({ id, label, icon: Icon, shortcut }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`nav-item${activeTab === id ? ' active' : ''}`}
          >
            <Icon size={14} style={{ flexShrink: 0, color: activeTab === id ? 'var(--color-cyan)' : 'var(--color-body)' }} />
            <span style={{ flex: 1 }}>{label}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: activeTab === id ? 'var(--color-cyan)' : 'var(--color-faint)', opacity: 0.8 }}>
              {shortcut}
            </span>
          </button>
        ))}

        {/* Active Session Mini Card */}
        {currentAnalysis && (
          <>
            <div className="nav-section" style={{ marginTop: 16 }}>Active Repository</div>
            <div style={{ margin: '0 6px 6px', padding: '10px', background: 'var(--color-canvas)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-hairline)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <img src="/favicon.svg" alt="repo" style={{ width: 14, height: 14 }} />
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {currentAnalysis.name}
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                <span className="badge badge-blue">{currentAnalysis.primaryLanguage}</span>
                <span className="badge badge-green">{currentAnalysis.license.spdxId}</span>
                <span className="badge">{currentAnalysis.fileCount} files</span>
              </div>
            </div>
          </>
        )}
      </nav>

      {/* Footer Status Widget */}
      <div style={{ borderTop: '1px solid var(--color-hairline)', padding: '10px 12px', background: 'var(--color-canvas)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div className="status-dot ok" />
            <span style={{ fontSize: 11, color: 'var(--color-ink)', fontWeight: 500 }}>FTS5 Knowledge Base</span>
          </div>
          <span className="badge badge-cyan" style={{ fontSize: 9, padding: '0 4px' }}>Active</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldCheck size={11} style={{ color: 'var(--color-emerald)' }} />
          <span style={{ fontSize: 10, color: 'var(--color-mute)', fontFamily: 'var(--font-mono)' }}>
            GRIS v1.1.0 · SDG-4
          </span>
        </div>
      </div>
    </aside>
  );
};
