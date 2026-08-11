'use client';
import React, { useState } from 'react';
import { ChevronRight, Search, Settings, Minus, Square, Copy, X } from 'lucide-react';

interface TopbarProps {
  activeTab: string;
  repoName?: string;
  onOpenSettings: () => void;
  onOpenCommandPalette: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ activeTab, repoName, onOpenSettings, onOpenCommandPalette }) => {
  const [maximized, setMaximized] = useState(false);

  const labels: Record<string, string> = {
    analyze:  'Analyze',
    insights: 'Insights',
    chat:     'Copilot',
    history:  'History',
  };

  const handleMinimize = () => {
    if (typeof window !== 'undefined') {
      // In webview / browser mode, blur active element
      (document.activeElement as HTMLElement)?.blur();
    }
  };

  const handleMaximize = () => {
    if (typeof window !== 'undefined') {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
        setMaximized(true);
      } else {
        document.exitFullscreen().catch(() => {});
        setMaximized(false);
      }
    }
  };

  const handleClose = () => {
    if (typeof window !== 'undefined') {
      try {
        window.close();
      } catch {
        // Fallback for browser security policy
      }
    }
  };

  return (
    <header className="app-topbar" style={{ background: '#09090b' }}>
      {/* Left: Windows 11 App Icon & Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <img
          src="/favicon.svg"
          alt="Git Reverse"
          style={{ width: 16, height: 16, objectFit: 'contain' }}
        />
        <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>
          Git Reverse Intelligence System
        </span>
        <span className="badge badge-cyan" style={{ fontSize: 9, padding: '0 5px' }}>v1.1.0</span>
      </div>

      {/* Center: Dynamic Path */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-mute)' }}>
        <span style={{ color: 'var(--color-cyan)', fontWeight: 500 }}>{labels[activeTab] || activeTab}</span>
        {repoName && (
          <>
            <ChevronRight size={10} style={{ color: 'var(--color-faint)' }} />
            <span style={{ color: 'var(--color-body)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {repoName}
            </span>
          </>
        )}
      </div>

      {/* Right: Search, Settings, Windows 11 Native Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <button
          onClick={onOpenCommandPalette}
          className="btn btn-ghost"
          style={{ height: 26, padding: '0 8px', fontSize: 11, gap: 5 }}
          title="Command Palette (Ctrl+K)"
        >
          <Search size={11} style={{ color: 'var(--color-cyan)' }} />
          <span>Search</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--color-faint)', border: '1px solid var(--color-hairline)', borderRadius: 3, padding: '0 4px', background: 'var(--color-canvas)' }}>Ctrl+K</span>
        </button>

        <button onClick={onOpenSettings} className="btn btn-ghost" style={{ height: 26, padding: '0 8px' }} title="Settings (Ctrl+,)">
          <Settings size={12} style={{ color: 'var(--color-body)' }} />
        </button>

        {/* Windows 11 Titlebar Button Controls */}
        <div style={{ display: 'flex', alignItems: 'center', height: '100%', marginLeft: 6 }}>
          <button
            onClick={handleMinimize}
            className="win-btn"
            style={{ width: 44, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--color-body)', transition: 'background 0.1s' }}
            title="Minimize"
          >
            <Minus size={12} />
          </button>

          <button
            onClick={handleMaximize}
            className="win-btn"
            style={{ width: 44, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--color-body)', transition: 'background 0.1s' }}
            title={maximized ? 'Restore' : 'Maximize'}
          >
            {maximized ? <Copy size={11} /> : <Square size={10} />}
          </button>

          <button
            onClick={handleClose}
            className="win-btn-close"
            style={{ width: 44, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--color-body)', transition: 'all 0.1s' }}
            title="Close Window"
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#e81123';
              e.currentTarget.style.color = '#ffffff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--color-body)';
            }}
          >
            <X size={13} />
          </button>
        </div>
      </div>
    </header>
  );
};
