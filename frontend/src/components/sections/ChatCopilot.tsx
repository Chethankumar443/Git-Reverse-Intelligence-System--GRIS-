'use client';
import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, MessageSquare, Sparkles } from 'lucide-react';
import { ThinkingOrbs } from '../motion/ThinkingOrbs';
import { ApiService } from '../../lib/api';
import type { ChatMessage } from '../../types';

interface ChatCopilotProps {
  initialPromptText?: string;
  sessionId?: number;
}

const AI_MODES = ['General', 'Explain', 'Architect', 'Developer', 'Documentation'] as const;
type AIMode = typeof AI_MODES[number];

export const ChatCopilot: React.FC<ChatCopilotProps> = ({ initialPromptText = '', sessionId }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [aiMode, setAiMode] = useState<AIMode>('General');
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (initialPromptText && messages.length === 0) {
      const welcomeMsg: ChatMessage = {
        id: 'welcome',
        role: 'assistant',
        content: `Repository context loaded into memory.\n\nWhat would you like to explore or clarify about this codebase?`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages([welcomeMsg]);
    }
  }, [initialPromptText]);

  const sendMessage = async () => {
    if (!input.trim() || isStreaming) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsStreaming(true);

    const assistantId = `asst-${Date.now()}`;
    const placeholder: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, placeholder]);

    try {
      const API_BASE = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';
      const history = messages.filter((m) => m.id !== 'welcome').map((m) => ({ role: m.role, content: m.content }));

      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg.content,
          history,
          session_id: sessionId || null,
          ai_mode: aiMode,
        }),
      });

      if (!res.ok || !res.body) throw new Error('Chat stream failed');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const event = JSON.parse(trimmed.slice(6));
              if (event.text) {
                accumulated += event.text;
                setMessages((prev) =>
                  prev.map((m) => m.id === assistantId ? { ...m, content: accumulated } : m)
                );
              }
            } catch { /* ignore parse error */ }
          }
        }
      }

      if (buffer.trim().startsWith('data: ')) {
        try {
          const event = JSON.parse(buffer.trim().slice(6));
          if (event.text) {
            accumulated += event.text;
            setMessages((prev) =>
              prev.map((m) => m.id === assistantId ? { ...m, content: accumulated } : m)
            );
          }
        } catch { /* ignore */ }
      }
    } catch {
      const mockResp = await ApiService.sendChatMessage(userMsg.content, messages);
      setMessages((prev) =>
        prev.map((m) => m.id === assistantId ? { ...m, content: mockResp.content } : m)
      );
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* Header bar with AI mode category pills */}
      <div className="pane-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sparkles size={13} style={{ color: 'var(--color-cyan)' }} />
          <span className="pane-title">Codebase Copilot</span>
        </div>
        <div style={{ display: 'flex', gap: 3, background: 'var(--color-canvas)', padding: 2, borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-hairline)' }}>
          {AI_MODES.map((mode) => (
            <button
              key={mode}
              onClick={() => setAiMode(mode)}
              style={{
                height: 22,
                padding: '0 8px',
                borderRadius: 'var(--radius-xs)',
                border: 'none',
                cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
                fontSize: 11,
                fontWeight: aiMode === mode ? 600 : 400,
                color: aiMode === mode ? '#000000' : 'var(--color-body)',
                background: aiMode === mode ? 'var(--color-cyan)' : 'transparent',
                transition: 'all 0.1s ease',
              }}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Scroll Feed */}
      <div className="pane-scroll" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: 40, textAlign: 'center' }}>
            <div style={{ width: 44, height: 44, background: 'var(--color-elevated)', border: '1px solid var(--color-hairline)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
              <MessageSquare size={20} style={{ color: 'var(--color-cyan)' }} />
            </div>
            <h3 className="pane-title" style={{ fontSize: 14, marginBottom: 4 }}>Ask Codebase Copilot</h3>
            <p style={{ fontSize: 12, color: 'var(--color-mute)', maxWidth: 400 }}>
              Query architectural decisions, dependencies, AST symbols, or code patterns extracted from the repository.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 16, justifyContent: 'center' }}>
              {[
                'Explain system architecture',
                'What are the core dependencies?',
                'How is error handling structured?',
                'List all main entrypoints',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => { setInput(q); inputRef.current?.focus(); }}
                  className="btn btn-ghost"
                  style={{ height: 26, padding: '0 10px', fontSize: 11 }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                gap: 10,
                alignItems: 'flex-start',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              }}
              className="animate-fade-up"
            >
              <div
                style={{
                  width: 26, height: 26, borderRadius: 6, flexShrink: 0,
                  background: msg.role === 'user' ? 'var(--color-cyan)' : 'var(--color-elevated)',
                  border: msg.role === 'user' ? 'none' : '1px solid var(--color-hairline)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                {msg.role === 'user'
                  ? <User size={13} color="#000" />
                  : <Bot size={13} style={{ color: 'var(--color-cyan)' }} />
                }
              </div>

              <div
                style={{
                  maxWidth: '80%',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: msg.role === 'user' ? 'linear-gradient(135deg, var(--color-cyan), var(--color-blue))' : 'var(--color-elevated)',
                  border: msg.role === 'user' ? 'none' : '1px solid var(--color-hairline)',
                  color: msg.role === 'user' ? '#000000' : 'var(--color-ink)',
                  fontWeight: msg.role === 'user' ? 500 : 400,
                  fontSize: 13,
                  lineHeight: '20px',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {msg.content || (
                  <ThinkingOrbs label="Synthesizing response…" size="sm" />
                )}
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input Row */}
      <div style={{ padding: '8px 12px', background: '#0d0d10', borderTop: '1px solid var(--color-hairline)', display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
          }}
          placeholder={`Ask Codebase Copilot in ${aiMode} mode… (Press Enter to send)`}
          rows={1}
          style={{
            flex: 1,
            background: 'var(--color-canvas)',
            border: '1px solid var(--color-hairline)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
            fontFamily: 'var(--font-sans)',
            fontSize: 12,
            lineHeight: '18px',
            color: 'var(--color-ink)',
            resize: 'none',
            outline: 'none',
            maxHeight: 80,
          }}
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim() || isStreaming}
          className="btn btn-primary"
          style={{ height: 32, padding: '0 12px', gap: 4 }}
        >
          {isStreaming ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
        </button>
      </div>
    </div>
  );
};
