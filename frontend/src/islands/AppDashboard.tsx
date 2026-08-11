'use client';
import { useState, useEffect, useCallback } from 'react';
import { Topbar } from '../components/layout/Topbar';
import { Sidebar } from '../components/layout/Sidebar';
import { StatusBar } from '../components/layout/StatusBar';
import { ToastContainer, type Toast } from '../components/layout/ToastContainer';
import { AnalyzePane } from '../components/sections/Hero';
import { RepoInsights } from '../components/sections/RepoInsights';
import { ChatCopilot } from '../components/sections/ChatCopilot';
import { HistoryTimeline } from '../components/sections/HistoryTimeline';
import { SettingsModal } from '../components/sections/SettingsModal';
import { CommandPalette } from '../components/sections/CommandPalette';
import { FirstRunWizard } from '../components/sections/FirstRunWizard';
import type { RepositoryAnalysis, SessionHistoryItem } from '../types';

/**
 * Root desktop application shell — zero PySide6/Qt overhead.
 * Rendered with Astro islands & desktop app layout grid (Topbar + Sidebar + Main Pane + StatusBar).
 */
export default function AppDashboard() {
  const [activeTab, setActiveTab] = useState<'analyze' | 'insights' | 'chat' | 'history'>('analyze');
  const [currentAnalysis, setCurrentAnalysis] = useState<RepositoryAnalysis | null>(null);
  const [chatPrompt, setChatPrompt] = useState('');
  const [chatSessionId, setChatSessionId] = useState<number | undefined>();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const API_BASE = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';

  const addToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Check first run configuration status on initial load
  useEffect(() => {
    fetch(`${API_BASE}/api/config`)
      .then((res) => res.json())
      .then((config) => {
        if (config.first_run_complete === false) {
          setWizardOpen(true);
        }
      })
      .catch(() => {});
  }, []);

  // Global Keyboard Shortcuts (⌘1..4 for tabs, ⌘, for settings, ⌘K for command palette)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isMod = e.ctrlKey || e.metaKey;
      if (isMod && e.key === 'k') {
        e.preventDefault();
        setCmdOpen(true);
      } else if (isMod && e.key === ',') {
        e.preventDefault();
        setSettingsOpen(true);
      } else if (isMod && e.key === '1') {
        e.preventDefault();
        setActiveTab('analyze');
      } else if (isMod && e.key === '2') {
        e.preventDefault();
        setActiveTab('insights');
      } else if (isMod && e.key === '3') {
        e.preventDefault();
        setActiveTab('chat');
      } else if (isMod && e.key === '4') {
        e.preventDefault();
        setActiveTab('history');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleAnalysisStart = (repoUrl: string) => {
    setActiveTab('analyze');
    addToast(`Started analysis for ${repoUrl}`, 'info');
  };

  const handleAnalysisComplete = (result: RepositoryAnalysis) => {
    setCurrentAnalysis(result);
    if ((result as any).sessionId) setChatSessionId((result as any).sessionId);
    setActiveTab('insights');
    addToast(`Analysis complete: ${result.owner}/${result.name}`, 'success');
  };

  const handleOpenChatWithPrompt = (prompt: string) => {
    setChatPrompt(prompt);
    setActiveTab('chat');
    addToast('Prompt loaded into Copilot chat', 'info');
  };

  const handleHistorySelect = (item: SessionHistoryItem) => {
    const loadedAnalysis: RepositoryAnalysis = {
      id: item.id,
      url: item.repoUrl,
      owner: item.owner,
      name: item.repoName,
      branch: 'main',
      description: '',
      starsCount: 0,
      forksCount: 0,
      primaryLanguage: item.language,
      languages: [{ name: item.language, percentage: 100, color: '#0070f3' }],
      fileCount: item.fileCount,
      totalLinesOfCode: 0,
      sizeFormatted: 'N/A',
      license: { spdxId: item.licenseSpdx || 'unknown', name: item.licenseSpdx || 'Unknown', isCopyleft: false, requiresAttribution: true },
      dependenciesCount: 0,
      astModulesCount: 0,
      sessionId: item.sessionId,
    };
    setCurrentAnalysis(loadedAnalysis);
    if (item.sessionId) setChatSessionId(item.sessionId);
    setActiveTab('insights');
    addToast(`Loaded session: ${item.owner}/${item.repoName}`, 'info');
  };

  return (
    <div className="app-shell">

      {/* Desktop Topbar */}
      <Topbar
        activeTab={activeTab}
        repoName={currentAnalysis?.name}
        onOpenSettings={() => setSettingsOpen(true)}
        onOpenCommandPalette={() => setCmdOpen(true)}
      />

      {/* Desktop Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => setActiveTab(tab as any)}
        currentAnalysis={currentAnalysis}
      />

      {/* Desktop Main Workspace Pane */}
      <main className="app-main">
        {activeTab === 'analyze' && (
          <AnalyzePane
            onAnalysisStart={handleAnalysisStart}
            onAnalysisComplete={handleAnalysisComplete}
          />
        )}
        {activeTab === 'insights' && (
          <RepoInsights
            analysis={currentAnalysis}
            onOpenChatWithPrompt={handleOpenChatWithPrompt}
          />
        )}
        {activeTab === 'chat' && (
          <ChatCopilot
            initialPromptText={chatPrompt}
            sessionId={chatSessionId}
          />
        )}
        {activeTab === 'history' && (
          <HistoryTimeline
            onSelectHistoryItem={handleHistorySelect}
          />
        )}
      </main>

      {/* Desktop Bottom Status Bar */}
      <StatusBar />

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />

      {/* Desktop Modals */}
      <FirstRunWizard isOpen={wizardOpen} onComplete={() => setWizardOpen(false)} />
      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <CommandPalette
        isOpen={cmdOpen}
        onClose={() => setCmdOpen(false)}
        onNavigate={(tab) => { setActiveTab(tab as any); setCmdOpen(false); }}
        onOpenSettings={() => { setSettingsOpen(true); setCmdOpen(false); }}
      />
    </div>
  );
}
