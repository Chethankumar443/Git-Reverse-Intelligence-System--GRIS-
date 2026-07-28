import json
import os
from typing import Dict, Any, List, Set, Tuple

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript/React",
    ".js": "JavaScript",
    ".jsx": "JavaScript/React",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".json": "JSON",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
}

ENTRYPOINT_WEIGHTS = {
    "main.rs": 100,
    "lib.rs": 95,
    "main.py": 100,
    "app.py": 90,
    "server.py": 85,
    "index.ts": 100,
    "index.js": 95,
    "main.ts": 90,
    "main.js": 90,
    "App.tsx": 95,
    "App.jsx": 90,
    "main.go": 100,
    "Program.cs": 100,
}


class CodebaseAnalyzer:
    """Production codebase analyzer that performs deep AST/manifest parsing,

    entrypoint ranking, line count metrics, and architecture classification.
    """

    @staticmethod
    def analyze(files: Dict[str, str], primary_lang: str = "Unknown",
                progress_callback=None) -> Dict[str, Any]:
        """Analyzes repository files.

        Args:
            files: Dict of {relative_path: content}
            primary_lang: Primary language from GitHub API metadata.
            progress_callback: Optional callable(files_done: int, total: int)
                               for quantitative progress updates (PRD §48).
        """
        lang_line_counts: Dict[str, int] = {}
        detected_frameworks: Set[str] = set()
        ranked_entrypoints: List[Tuple[str, int]] = []
        manifest_facts: List[Dict[str, str]] = []
        dependency_details: List[Dict[str, str]] = []  # §52 dependency intelligence
        dir_structure: Set[str] = set()
        total_lines = 0
        ast_summaries: List[str] = []
        all_files = list(files.items())
        total_files = len(all_files)

        for idx, (path, content) in enumerate(all_files):
            # §48 Quantitative progress callback
            if progress_callback and idx % 20 == 0:
                progress_callback(idx, total_files)

            lines = content.count("\n") + 1
            total_lines += lines
            filename = os.path.basename(path)
            ext = os.path.splitext(filename)[1].lower()

            # Extract AST symbols for key code files
            if ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".cs", ".java") and len(ast_summaries) < 25:
                symbols = CodebaseAnalyzer.extract_symbols(path, content, ext)
                if symbols:
                    ast_summaries.append(f"{path}: {', '.join(symbols)}")

            # Parent directory tracker
            dir_name = os.path.dirname(path)
            if dir_name:
                dir_structure.add(dir_name.split("/")[0])

            # Language line counting
            if ext in EXTENSION_LANGUAGE_MAP:
                lang_name = EXTENSION_LANGUAGE_MAP[ext]
                lang_line_counts[lang_name] = lang_line_counts.get(lang_name, 0) + lines

            # Entrypoint ranking
            if filename in ENTRYPOINT_WEIGHTS:
                weight = ENTRYPOINT_WEIGHTS[filename]
                ranked_entrypoints.append((path, weight))

            # Manifest parsing
            if filename == "package.json":
                try:
                    pkg = json.loads(content)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    
                    if "react" in deps: detected_frameworks.add("React")
                    if "next" in deps: detected_frameworks.add("Next.js")
                    if "vite" in deps: detected_frameworks.add("Vite")
                    if "electron" in deps: detected_frameworks.add("Electron")
                    if "@tauri-apps/api" in deps: detected_frameworks.add("Tauri")
                    if "tailwindcss" in deps or "@tailwindcss/vite" in deps: detected_frameworks.add("Tailwind CSS")

                    for d_name, d_ver in deps.items():
                        ver_str = str(d_ver).lstrip("^~=>=<!")
                        dependency_details.append({
                            "name": d_name,
                            "version": ver_str,
                            "license": "unknown",
                            "source": "package.json",
                        })

                    manifest_facts.append({
                        "key": "package.json",
                        "category": "Manifest",
                        "content": f"Package: {pkg.get('name', 'N/A')} v{pkg.get('version', '0.1.0')} ({len(deps)} dependencies)"
                    })
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to parse package.json in {path}: {e}")

            elif filename == "Cargo.toml":
                if "tauri" in content.lower(): detected_frameworks.add("Tauri")
                if "tokio" in content.lower(): detected_frameworks.add("Tokio Async")
                if "actix" in content.lower() or "axum" in content.lower(): detected_frameworks.add("Rust Web API")
                if "pyside" in content.lower(): detected_frameworks.add("PySide6 Qt")

                import re
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    m = re.match(r"^([A-Za-z0-9_\-]+)\s*=\s*(?:\"([^\"]+)\"|\{.*version\s*=\s*\"([^\"]+)\")", line)
                    if m:
                        dep_name = m.group(1)
                        dep_ver = m.group(2) or m.group(3) or ""
                        dependency_details.append({
                            "name": dep_name,
                            "version": dep_ver,
                            "license": "unknown",
                            "source": "Cargo.toml",
                        })

                manifest_facts.append({
                    "key": "Cargo.toml",
                    "category": "Manifest",
                    "content": "Rust Package & Workspace Manifest"
                })

            elif filename in ("requirements.txt", "pyproject.toml", "Pipfile"):
                lower_c = content.lower()
                if "fastapi" in lower_c: detected_frameworks.add("FastAPI")
                if "django" in lower_c: detected_frameworks.add("Django")
                if "flask" in lower_c: detected_frameworks.add("Flask")
                if "pyside6" in lower_c or "pyqt" in lower_c: detected_frameworks.add("PySide6 Desktop")
                if "sqlalchemy" in lower_c: detected_frameworks.add("SQLAlchemy ORM")

                # §52 Dependency intelligence: parse requirements.txt for name+version
                if filename == "requirements.txt":
                    import re
                    for req_line in content.splitlines():
                        req_line = req_line.strip()
                        if not req_line or req_line.startswith("#"):
                            continue
                        m = re.match(r"^([A-Za-z0-9_\-\.]+)([>=<!~^]+)([^\s;#]+)?", req_line)
                        if m:
                            dep_name = m.group(1)
                            dep_ver = m.group(3) or ""
                            dependency_details.append({
                                "name": dep_name,
                                "version": dep_ver,
                                "license": "unknown",  # License lookup is a future capability
                                "source": "requirements.txt",
                            })

                manifest_facts.append({
                    "key": filename,
                    "category": "Manifest",
                    "content": f"Python Dependency Specification ({filename})"
                })

            elif filename == "go.mod":
                if "gin" in content.lower(): detected_frameworks.add("Gin Web")
                if "fiber" in content.lower(): detected_frameworks.add("Fiber Web")

                import re
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("//") or not line:
                        continue
                    m = re.match(r"^(?:require\s+)?([A-Za-z0-9_\.\-/]+)\s+(v[0-9A-Za-z\.\-+]+)", line)
                    if m:
                        dep_name = m.group(1)
                        dep_ver = m.group(2)
                        dependency_details.append({
                            "name": dep_name,
                            "version": dep_ver,
                            "license": "unknown",
                            "source": "go.mod",
                        })

                manifest_facts.append({
                    "key": "go.mod",
                    "category": "Manifest",
                    "content": "Go Module Specification"
                })

        # Rank entrypoints by weight
        sorted_entrypoints = [ep[0] for ep in sorted(ranked_entrypoints, key=lambda x: x[1], reverse=True)]

        # Sorted languages by line count
        sorted_langs = sorted(lang_line_counts.items(), key=lambda x: x[1], reverse=True)
        detected_languages = [l[0] for l in sorted_langs[:5]]
        if not detected_languages and primary_lang != "Unknown":
            detected_languages = [primary_lang]

        # Architecture Classification
        arch_pattern = "Standard Application Monolith"
        if "Tauri" in detected_frameworks or "Electron" in detected_frameworks or "PySide6 Desktop" in detected_frameworks:
            arch_pattern = "Native Desktop Application (Sidecar/IPC)"
        elif "Next.js" in detected_frameworks or "React" in detected_frameworks:
            arch_pattern = "Modern Web Single Page / Fullstack App"
        elif "FastAPI" in detected_frameworks or "Django" in detected_frameworks or "Rust Web API" in detected_frameworks:
            arch_pattern = "RESTful API Backend Service"
        elif "apps" in dir_structure and "packages" in dir_structure:
            arch_pattern = "Multi-Package Monorepo"

        # §48: Final progress callback (100%)
        if progress_callback:
            progress_callback(total_files, total_files)

        return {
            "detected_languages": detected_languages,
            "detected_frameworks": list(detected_frameworks),
            "entrypoints": sorted_entrypoints[:6],
            "architecture_pattern": arch_pattern,
            "manifest_facts": manifest_facts,
            "dependency_details": dependency_details[:50],  # §52
            "ast_summaries": ast_summaries,
            "total_lines": total_lines,
            "top_directories": list(dir_structure)[:8],
        }

    @staticmethod
    def extract_symbols(path: str, content: str, ext: str) -> List[str]:
        """Extracts top AST symbols (classes, functions, interfaces, structs) with line numbers from source files."""
        symbols = []
        if ext == ".py":
            import ast
            import logging
            try:
                tree = ast.parse(content)
                for node in ast.iter_child_nodes(tree):
                    line_no = getattr(node, "lineno", 1)
                    if isinstance(node, ast.ClassDef):
                        symbols.append(f"class {node.name} (line {line_no})")
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append(f"def {node.name}() (line {line_no})")
            except Exception as e:
                logging.warning(f"AST parse error in {path}: {e}")
        else:
            import re
            for m in re.finditer(r"(?:class|interface|struct|type|enum)\s+([A-Za-z0-9_]+)", content):
                line_no = content[:m.start()].count("\n") + 1
                symbols.append(f"type {m.group(1)} (line {line_no})")
                if len(symbols) >= 3:
                    break
            func_count = 0
            for m in re.finditer(r"(?:function|fn|def|func)\s+([A-Za-z0-9_]+)", content):
                line_no = content[:m.start()].count("\n") + 1
                symbols.append(f"fn {m.group(1)}() (line {line_no})")
                func_count += 1
                if func_count >= 3:
                    break

        return symbols[:5]

