'use client';
import React, { useState } from 'react';
import { Folder, FolderOpen, FileCode, Code2, ChevronRight, ChevronDown, Search } from 'lucide-react';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: FileNode[];
  size?: string;
  symbols?: string[];
}

interface RepoFileTreeProps {
  onSelectFile?: (filePath: string) => void;
}

const MOCK_FILE_TREE: FileNode[] = [
  {
    name: 'src',
    path: 'src',
    type: 'folder',
    children: [
      {
        name: 'core',
        path: 'src/core',
        type: 'folder',
        children: [
          { name: 'engine.py', path: 'src/core/engine.py', type: 'file', size: '14.2 KB', symbols: ['GRISAnalyzer', 'parse_ast()', 'extract_imports()'] },
          { name: 'scanner.py', path: 'src/core/scanner.py', type: 'file', size: '8.4 KB', symbols: ['SecretScanner', 'detect_patterns()'] },
        ],
      },
      {
        name: 'api',
        path: 'src/api',
        type: 'folder',
        children: [
          { name: 'routes.py', path: 'src/api/routes.py', type: 'file', size: '6.1 KB', symbols: ['router', 'start_analysis()', 'stream_ws()'] },
          { name: 'config.py', path: 'src/api/config.py', type: 'file', size: '3.5 KB', symbols: ['save_config()', 'test_connection()'] },
        ],
      },
      { name: 'main.py', path: 'src/main.py', type: 'file', size: '2.8 KB', symbols: ['main()', 'open_browser_when_ready()'] },
    ],
  },
  { name: 'package.json', path: 'package.json', type: 'file', size: '1.2 KB', symbols: ['scripts', 'dependencies'] },
  { name: 'README.md', path: 'README.md', type: 'file', size: '4.5 KB', symbols: ['Overview', 'Installation', 'Architecture'] },
];

export const RepoFileTree: React.FC<RepoFileTreeProps> = ({ onSelectFile }) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ src: true, 'src/core': true });
  const [selectedPath, setSelectedPath] = useState<string>('src/core/engine.py');
  const [search, setSearch] = useState<string>('');

  const toggleExpand = (path: string) => {
    setExpanded((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const renderNode = (node: FileNode, level = 0) => {
    const isFolder = node.type === 'folder';
    const isExpanded = expanded[node.path];
    const isSelected = selectedPath === node.path;

    if (search && !node.name.toLowerCase().includes(search.toLowerCase()) && !isFolder) {
      return null;
    }

    return (
      <div key={node.path} style={{ marginLeft: level * 12 }}>
        <div
          onClick={() => {
            if (isFolder) {
              toggleExpand(node.path);
            } else {
              setSelectedPath(node.path);
              onSelectFile?.(node.path);
            }
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '4px 8px',
            borderRadius: 'var(--radius-xs)',
            background: isSelected ? 'rgba(0, 223, 216, 0.12)' : 'transparent',
            color: isSelected ? 'var(--color-cyan)' : 'var(--color-ink)',
            cursor: 'pointer',
            fontSize: 12,
            fontFamily: 'var(--font-mono)',
            transition: 'background 0.1s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {isFolder ? (
              <>
                {isExpanded ? <ChevronDown size={12} style={{ color: 'var(--color-mute)' }} /> : <ChevronRight size={12} style={{ color: 'var(--color-mute)' }} />}
                {isExpanded ? <FolderOpen size={13} style={{ color: 'var(--color-cyan)' }} /> : <Folder size={13} style={{ color: 'var(--color-mute)' }} />}
              </>
            ) : (
              <>
                <div style={{ width: 12 }} />
                <FileCode size={13} style={{ color: isSelected ? 'var(--color-cyan)' : 'var(--color-mute)' }} />
              </>
            )}
            <span>{node.name}</span>
          </div>

          {!isFolder && node.size && (
            <span style={{ fontSize: 10, color: 'var(--color-faint)' }}>{node.size}</span>
          )}
        </div>

        {isFolder && isExpanded && node.children && (
          <div>{node.children.map((child) => renderNode(child, level + 1))}</div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', borderRight: '1px solid var(--color-hairline)', background: '#0c0c0f' }}>
      {/* File Tree Search Header */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-hairline)' }}>
        <div style={{ position: 'relative' }}>
          <Search size={12} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-cyan)', pointerEvents: 'none' }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search AST symbols & files…"
            className="input input-mono"
            style={{ paddingLeft: 26, height: 26, fontSize: 11 }}
          />
        </div>
      </div>

      {/* File Tree List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
        <div className="eyebrow" style={{ padding: '4px 8px', marginBottom: 6 }}>Repository Tree</div>
        {MOCK_FILE_TREE.map((node) => renderNode(node))}
      </div>

      {/* AST Symbol Inspector Footer */}
      <div style={{ padding: 12, borderTop: '1px solid var(--color-hairline)', background: 'var(--color-canvas)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
          <Code2 size={13} style={{ color: 'var(--color-cyan)' }} />
          <span className="eyebrow">AST Symbols ({selectedPath.split('/').pop()})</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {['GRISAnalyzer', 'parse_ast()', 'extract_imports()', 'SecretScanner'].map((sym) => (
            <span key={sym} className="badge badge-cyan" style={{ fontSize: 10 }}>
              {sym}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
