export interface RepositoryAnalysis {
  id: string;
  url: string;
  owner: string;
  name: string;
  branch: string;
  description: string;
  starsCount: number;
  forksCount: number;
  primaryLanguage: string;
  languages: { name: string; percentage: number; color: string }[];
  fileCount: number;
  totalLinesOfCode: number;
  sizeFormatted: string;
  license: {
    spdxId: string;
    name: string;
    isCopyleft: boolean;
    requiresAttribution: boolean;
  };
  dependenciesCount: number;
  astModulesCount: number;
  /** SQLite session ID returned by the FastAPI backend */
  sessionId?: number;
  /** Full generated recreation prompt (returned on WS done event) */
  generatedPrompt?: string;
}

export type AnalysisStepStatus = 'idle' | 'running' | 'completed' | 'error';

export interface AnalysisStep {
  id: string;
  title: string;
  description: string;
  status: AnalysisStepStatus;
  progressPercent: number;
  logOutput?: string[];
  timestamp?: string;
}

export interface RecreationPrompt {
  id: string;
  repoUrl: string;
  repoName: string;
  generatedAt: string;
  systemPrompt: string;
  architecturalOverview: string;
  directoryTree: string;
  keyDependencies: { name: string; purpose: string; license: string }[];
  modelUsed: string;
  tokensStreamed: number;
  generationTimeMs: number;
  attributionBlock: {
    sourceUrl: string;
    licenseSpdx: string;
    disclaimer: string;
    generatedDate: string;
  };
}

export interface SessionHistoryItem {
  id: string;
  repoUrl: string;
  repoName: string;
  owner: string;
  timestamp: string;
  status: 'completed' | 'analyzing' | 'failed';
  language: string;
  fileCount: number;
  licenseSpdx: string;
  recreationPromptSnippet: string;
  /** Backend SQLite ID for API operations */
  sessionId?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  citations?: { file: string; lineRange?: string }[];
  codeSnippets?: { language: string; code: string; title?: string }[];
  isStreaming?: boolean;
}

export interface BYOKConfig {
  provider: 'openai' | 'anthropic' | 'ollama' | 'groq' | 'deepseek';
  apiKey: string;
  modelName: string;
  baseUrl?: string;
  isKeyringSaved: boolean;
  exportDirectory: string;
  enableSdgAttribution: boolean;
  theme: 'dark' | 'light' | 'system';
}

export interface CodebaseEntity {
  path: string;
  type: 'file' | 'directory';
  language?: string;
  sizeBytes?: number;
  complexityScore?: number;
  summary?: string;
  children?: CodebaseEntity[];
}
