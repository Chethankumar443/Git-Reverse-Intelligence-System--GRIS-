'use client';
import React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 500,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        pointerEvents: 'none',
      }}
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="animate-fade-up"
          style={{
            pointerEvents: 'auto',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-elevated)',
            border: '1px solid var(--color-hairline)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.12), 0 1px 3px rgba(0,0,0,0.06)',
            fontSize: 12,
            color: 'var(--color-ink)',
            maxWidth: 340,
          }}
        >
          {toast.type === 'success' && <CheckCircle2 size={15} style={{ color: 'var(--color-green)', flexShrink: 0 }} />}
          {toast.type === 'error'   && <AlertCircle size={15} style={{ color: 'var(--color-red)', flexShrink: 0 }} />}
          {toast.type === 'info'    && <Info size={15} style={{ color: 'var(--color-blue)', flexShrink: 0 }} />}
          
          <span style={{ flex: 1, lineHeight: '16px' }}>{toast.message}</span>
          
          <button
            onClick={() => onDismiss(toast.id)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'var(--color-mute)' }}
          >
            <X size={12} />
          </button>
        </div>
      ))}
    </div>
  );
};
