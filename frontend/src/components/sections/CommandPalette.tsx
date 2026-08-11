'use client';
import React, { useState, useEffect } from 'react';
import { Search, Sparkles, Key, FileText, History, Terminal, X } from 'lucide-react';

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (tab: string) => void;
  onOpenSettings: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigate,
  onOpenSettings,
}) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const actions = [
    { id: 'analyze', title: 'Analyze GitHub Repository', icon: Sparkles, type: 'nav' },
    { id: 'insights', title: 'View System Recreation Prompt', icon: FileText, type: 'nav' },
    { id: 'chat', title: 'Open Codebase Copilot Chat', icon: Terminal, type: 'nav' },
    { id: 'history', title: 'Browse Session History', icon: History, type: 'nav' },
    { id: 'settings', title: 'Manage BYOK API Keys & Config', icon: Key, type: 'settings' },
  ];

  const filtered = actions.filter((a) => a.title.toLowerCase().includes(query.toLowerCase()));

  const handleSelect = (action: typeof actions[0]) => {
    if (action.type === 'settings') {
      onOpenSettings();
    } else {
      onNavigate(action.id);
    }
  };

  return (
    <>
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-panel" style={{ maxWidth: 500 }}>
        {/* Search header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: '1px solid var(--color-hairline)' }}>
          <Search size={14} style={{ color: 'var(--color-mute)' }} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search workspace…"
            autoFocus
            className="input"
            style={{ border: 'none', background: 'transparent', padding: 0, fontSize: 13 }}
          />
          <button onClick={onClose} className="btn btn-ghost" style={{ padding: '0 6px', height: 24 }}>
            <X size={13} />
          </button>
        </div>

        {/* List */}
        <div style={{ padding: 6, maxHeight: 300, overflowY: 'auto' }}>
          {filtered.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', fontSize: 12, color: 'var(--color-mute)' }}>
              No matching actions.
            </div>
          ) : (
            filtered.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.id}
                  onClick={() => handleSelect(action)}
                  className="nav-item"
                  style={{ width: '100%', margin: 0, padding: '8px 10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Icon size={14} style={{ color: 'var(--color-ink)' }} />
                    <span style={{ fontSize: 12, fontWeight: 500 }}>{action.title}</span>
                  </div>
                  <span className="eyebrow" style={{ fontSize: 9 }}>{action.type}</span>
                </button>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '6px 14px', background: 'var(--color-hairline-soft)', borderTop: '1px solid var(--color-hairline)', display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--color-mute)', fontFamily: 'var(--font-mono)' }}>
          <span>Press ESC to close</span>
          <span>⌘K Command Palette</span>
        </div>
      </div>
    </>
  );
};
