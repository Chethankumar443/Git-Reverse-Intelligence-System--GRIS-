'use client';
import React, { useEffect, useState } from 'react';
import { HardDrive, Cpu, ShieldCheck, Database, Zap } from 'lucide-react';

export const StatusBar: React.FC = () => {
  const [health, setHealth] = useState<{
    db_size_kb?: number;
    disk_free_gb?: number;
    session_count?: number;
  }>({});
  const [modelId, setModelId] = useState('gpt-4o');
  const [hasKey, setHasKey] = useState(false);

  const API_BASE = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const loadHealth = () => {
      fetch(`${API_BASE}/api/health`)
        .then((r) => r.json())
        .then((d) => setHealth(d))
        .catch(() => {});
      fetch(`${API_BASE}/api/config`)
        .then((r) => r.json())
        .then((c) => {
          if (c.model_id) setModelId(c.model_id);
          setHasKey(Boolean(c.has_api_key));
        })
        .catch(() => {});
    };
    loadHealth();
    const timer = setInterval(loadHealth, 30000);
    return () => clearInterval(timer);
  }, []);

  return (
    <footer
      style={{
        gridColumn: '1 / -1',
        height: 24,
        background: 'var(--color-elevated)',
        borderTop: '1px solid var(--color-hairline)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 12px',
        fontSize: 10,
        fontFamily: 'var(--font-mono)',
        color: 'var(--color-mute)',
        userSelect: 'none',
        zIndex: 30,
      }}
    >
      {/* Left indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div className="status-dot ok" />
          <span style={{ color: 'var(--color-ink)' }}>SQLite WAL</span>
          <span>FTS5 Ready</span>
        </div>
        {health.db_size_kb !== undefined && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Database size={10} />
            <span>DB: {health.db_size_kb} KB</span>
          </div>
        )}
        {health.disk_free_gb !== undefined && health.disk_free_gb > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <HardDrive size={10} />
            <span>Free: {health.disk_free_gb} GB</span>
          </div>
        )}
      </div>

      {/* Right indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <Cpu size={10} />
          <span>{modelId}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <ShieldCheck size={10} style={{ color: hasKey ? 'var(--color-green)' : 'var(--color-amber)' }} />
          <span style={{ color: hasKey ? 'var(--color-ink)' : 'var(--color-amber)' }}>
            {hasKey ? 'BYOK Encrypted' : 'Local Mode'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <Zap size={10} style={{ color: 'var(--color-green)' }} />
          <span>SDG-4 Compliant</span>
        </div>
      </div>
    </footer>
  );
};
