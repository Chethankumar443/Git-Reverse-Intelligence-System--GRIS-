/**
 * Git Reverse — Desktop Dashboard Store & State Manager
 * Implements @bagui/dashboard-store pattern for local persistence,
 * telemetry monitoring, active workspace tabs, and spending metrics.
 */
import type { RepositoryAnalysis, SessionHistoryItem } from '../types';

export interface DashboardMetrics {
  totalReposAnalyzed: number;
  totalTokensUsed: number;
  estimatedCostUsd: number;
  ftsIndexedSessions: number;
  activeLanguage: string;
  activeLicense: string;
}

export interface DashboardStoreState {
  activeTab: 'analyze' | 'insights' | 'chat' | 'history';
  currentAnalysis: RepositoryAnalysis | null;
  selectedHistorySession: SessionHistoryItem | null;
  chatPrompt: string;
  chatSessionId?: number;
  metrics: DashboardMetrics;
}

class DashboardStore {
  private state: DashboardStoreState = {
    activeTab: 'analyze',
    currentAnalysis: null,
    selectedHistorySession: null,
    chatPrompt: '',
    metrics: {
      totalReposAnalyzed: 142,
      totalTokensUsed: 18940,
      estimatedCostUsd: 0.042,
      ftsIndexedSessions: 24,
      activeLanguage: 'TypeScript / Rust',
      activeLicense: 'MIT',
    },
  };

  private listeners: Set<(state: DashboardStoreState) => void> = new Set();

  constructor() {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('git_reverse_dashboard_store');
        if (saved) {
          const parsed = JSON.parse(saved);
          this.state = { ...this.state, ...parsed };
        }
      } catch { /* ignore */ }
    }
  }

  public getState(): DashboardStoreState {
    return this.state;
  }

  public setState(updates: Partial<DashboardStoreState>) {
    this.state = { ...this.state, ...updates };
    this.notify();
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(
          'git_reverse_dashboard_store',
          JSON.stringify({
            activeTab: this.state.activeTab,
            currentAnalysis: this.state.currentAnalysis,
            chatPrompt: this.state.chatPrompt,
          })
        );
      } catch { /* ignore */ }
    }
  }

  public subscribe(listener: (state: DashboardStoreState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify() {
    this.listeners.forEach((listener) => listener(this.state));
  }
}

export const dashboardStore = new DashboardStore();
