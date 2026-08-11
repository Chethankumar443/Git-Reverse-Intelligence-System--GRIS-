import type {
  RepositoryAnalysis,
  RecreationPrompt,
  SessionHistoryItem,
  ChatMessage,
} from '../types';

const API_BASE = (import.meta as any).env?.PUBLIC_API_URL || 'http://localhost:8000';

export class ApiService {
  /**
   * Validate GitHub repository URL format
   */
  static validateRepoUrl(url: string): { valid: boolean; owner?: string; repo?: string; error?: string } {
    const regex = /^https?:\/\/(www\.)?github\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9._-]+)\/?$/;
    const match = url.trim().match(regex);
    if (!match) {
      return {
        valid: false,
        error: 'Invalid GitHub URL. Expected format: https://github.com/owner/repository',
      };
    }
    return {
      valid: true,
      owner: match[2],
      repo: match[3].replace(/\.git$/, ''),
    };
  }

  /**
   * Start a new repository reverse intelligence analysis job
   */
  static async startAnalysis(repoUrl: string, depth: 'quick' | 'deep' | 'recreation' = 'recreation'): Promise<RepositoryAnalysis> {
    try {
      const response = await fetch(`${API_BASE}/api/analysis/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: repoUrl, depth }),
      });
      if (response.ok) {
        return await response.json();
      }
    } catch {
      // Fallback for standalone frontend demonstration or disconnected local server
    }

    const { owner = 'paradise-labs', repo = 'git-reverse-v2' } = this.validateRepoUrl(repoUrl);
    
    return {
      id: `analysis-${Date.now()}`,
      url: repoUrl,
      owner,
      name: repo,
      branch: 'main',
      description: 'High-performance AI repository reverse-engineering system & system prompt recreation engine.',
      starsCount: 1420,
      forksCount: 184,
      primaryLanguage: 'TypeScript / Rust',
      languages: [
        { name: 'TypeScript', percentage: 48.5, color: '#3178c6' },
        { name: 'Rust', percentage: 32.1, color: '#dea584' },
        { name: 'Python', percentage: 14.4, color: '#3572A5' },
        { name: 'CSS/Astro', percentage: 5.0, color: '#ff5a03' },
      ],
      fileCount: 142,
      totalLinesOfCode: 18940,
      sizeFormatted: '4.2 MB',
      license: {
        spdxId: 'MIT',
        name: 'MIT Open Source License',
        isCopyleft: false,
        requiresAttribution: true,
      },
      dependenciesCount: 38,
      astModulesCount: 64,
    };
  }

  /**
   * Fetch generated Recreation System Prompt for a repo
   */
  static async getRecreationPrompt(repoId: string): Promise<RecreationPrompt> {
    try {
      const res = await fetch(`${API_BASE}/api/analysis/${repoId}/prompt`);
      if (res.ok) return await res.json();
    } catch {
      // Fallback response
    }

    return {
      id: `prompt-${repoId}`,
      repoUrl: 'https://github.com/paradise-labs/git-reverse-v2',
      repoName: 'git-reverse-v2',
      generatedAt: new Date().toISOString(),
      systemPrompt: `# SYSTEM PROMPT — RECREATE GIT REVERSE V2 ENGINE
You are an expert full-stack systems engineer. Recreate the codebase using the following architectural specifications.

## ARCHITECTURE OVERVIEW
- Core Engine: Python FastAPI / Rust CLI background worker
- UI Layer: Astro 5.0 + React 19 + Framer Motion + Tailwind CSS
- Data Persistence: SQLite local DB with vector embeddings index (hnswlib/sqlite-vss)
- AI Pipeline: BYOK OpenAI/Anthropic/Ollama provider dispatcher with streaming chunk parser
- Security: Local OS Keyring storage via Windows Credential Manager

## DIRECTORY STRUCTURE
├── main.py (FastAPI entrypoint)
├── app/
│   ├── services/ (analyzer.py, parser.py, exporter.py)
│   └── viewmodels/
├── crates/ (Rust fast scanner CLI)
└── frontend/
    ├── src/islands/ (React streaming components)
    ├── src/components/ (Vercel Geist styled UI)
    └── src/styles/globals.css

## CORE CONTRACTS & API SPEC
1. Endpoint POST /api/analysis/start accepts { url: string, depth: string }
2. Endpoint WS /ws/stream-{id} streams token chunks & AST progress steps
3. PDF Exporter generates Geist-styled vector PDF with SDG-4 license attribution footer.`,
      architecturalOverview: 'Multi-threaded hybrid Python/Rust intelligence core with React 19 / Astro 5 streaming interface.',
      directoryTree: `git-reverse-v2/
├── app/
│   ├── services/
│   │   ├── analyzer.py
│   │   ├── exporter.py
│   │   └── parser.py
│   └── views/
├── crates/audit/
└── frontend/
    ├── src/components/
    ├── src/lib/api.ts
    └── src/pages/index.astro`,
      keyDependencies: [
        { name: 'fastapi', purpose: 'High-speed async API server', license: 'MIT' },
        { name: 'tree-sitter', purpose: 'AST Code Parsing & Tokenization', license: 'MIT' },
        { name: 'framer-motion', purpose: 'Spring physics micro-interactions', license: 'MIT' },
        { name: 'reportlab', purpose: 'PDF Export Engine', license: 'BSD' },
      ],
      modelUsed: 'OpenAI gpt-4o / Local Ollama (BYOK)',
      tokensStreamed: 4820,
      generationTimeMs: 1420,
      attributionBlock: {
        sourceUrl: 'https://github.com/paradise-labs/git-reverse-v2',
        licenseSpdx: 'MIT',
        disclaimer: 'Generated by Git Reverse Intelligence System V2 under SDG-4 Open Science protocol.',
        generatedDate: new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
      },
    };
  }

  /**
   * Fetch session history list
   */
  static async getHistory(): Promise<SessionHistoryItem[]> {
    try {
      const res = await fetch(`${API_BASE}/api/history`);
      if (res.ok) return await res.json();
    } catch {
      // Fallback
    }

    return [
      {
        id: 'hist-1',
        repoUrl: 'https://github.com/paradise-labs/git-reverse-v2',
        repoName: 'git-reverse-v2',
        owner: 'paradise-labs',
        timestamp: '10 mins ago',
        status: 'completed',
        language: 'TypeScript / Rust',
        fileCount: 142,
        licenseSpdx: 'MIT',
        recreationPromptSnippet: 'Full system recreation prompt for multi-threaded Python/Rust repository intelligence...',
      },
      {
        id: 'hist-2',
        repoUrl: 'https://github.com/vercel/next.js',
        repoName: 'next.js',
        owner: 'vercel',
        timestamp: '2 hours ago',
        status: 'completed',
        language: 'Rust / TypeScript',
        fileCount: 3840,
        licenseSpdx: 'MIT',
        recreationPromptSnippet: 'Extracted Turbopack build engine & React Server Component routing graph specs...',
      },
      {
        id: 'hist-3',
        repoUrl: 'https://github.com/fastapi/fastapi',
        repoName: 'fastapi',
        owner: 'fastapi',
        timestamp: '1 day ago',
        status: 'completed',
        language: 'Python',
        fileCount: 280,
        licenseSpdx: 'MIT',
        recreationPromptSnippet: 'Starlette & Pydantic dependency synthesis prompt with OpenAPI schema generator...',
      },
    ];
  }

  /**
   * Export session to PDF or Markdown
   */
  static async exportPrompt(promptId: string, format: 'pdf' | 'markdown'): Promise<{ success: boolean; downloadUrl?: string; filename: string }> {
    try {
      const res = await fetch(`${API_BASE}/api/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ promptId, format }),
      });
      if (res.ok) return await res.json();
    } catch {
      // Mock fallback
    }

    return {
      success: true,
      filename: `git-reverse-recreation-prompt.${format === 'pdf' ? 'pdf' : 'md'}`,
    };
  }

  /**
   * Send chat message to Codebase Copilot
   */
  static async sendChatMessage(message: string, history: ChatMessage[]): Promise<ChatMessage> {
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history }),
      });
      if (res.ok) return await res.json();
    } catch {
      // Fallback simulated response
    }

    return {
      id: `chat-${Date.now()}`,
      role: 'assistant',
      content: `Based on the reverse analysis of this repository, here is how the architectural flow operates:\n\n1. **Core Service Dispatcher**: In \`app/services/analyzer.py\`, incoming URLs are parsed using standard regular expressions before being queued into the background worker.\n2. **AST Token Extraction**: The scanner parses all language ASTs to extract entrypoints and exported schemas.\n3. **Recreation Prompt Synthesis**: The prompt engine structures these insights into a standardized system prompt suitable for LLM code generation.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      citations: [
        { file: 'app/services/analyzer.py', lineRange: 'L12-L45' },
        { file: 'workspace/api/main.py', lineRange: 'L24-L50' },
      ],
      codeSnippets: [
        {
          language: 'python',
          title: 'app/services/analyzer.py',
          code: `class RepoAnalyzer:\n    async def process_repo(self, url: str) -> AnalysisResult:\n        repo_meta = await self.clone_or_fetch(url)\n        ast_map = await self.parse_ast_tree(repo_meta.local_path)\n        return await self.build_intelligence_graph(ast_map)`,
        },
      ],
    };
  }
}
