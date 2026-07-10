import json
import re
from pathlib import Path
from gitreverse.analyzers.base import Analyzer, AnalysisContext, AnalysisResult
from gitreverse.utils.logging import get_logger

logger = get_logger("analyzers.framework")

# Framework signatures: (name, evidence detection logic)
# Each entry defines a framework name and what to look for
FRAMEWORK_SIGNATURES = [
    # JavaScript/Frontend
    {
        "name": "React",
        "manifest_key": "dependencies.react",
        "import_patterns": [r"from ['\"]react['\"]", r"require\(['\"]react['\"]\)"],
        "config_files": [],
    },
    {
        "name": "Next.js",
        "manifest_key": "dependencies.next",
        "import_patterns": [r"from ['\"]next/"],
        "config_files": ["next.config.js", "next.config.ts", "next.config.mjs"],
    },
    {
        "name": "Vue.js",
        "manifest_key": "dependencies.vue",
        "import_patterns": [r"from ['\"]vue['\"]"],
        "config_files": ["vue.config.js"],
    },
    {
        "name": "Express.js",
        "manifest_key": "dependencies.express",
        "import_patterns": [r"require\(['\"]express['\"]\)", r"from ['\"]express['\"]"],
        "config_files": [],
    },
    # Python frameworks
    {
        "name": "FastAPI",
        "manifest_key": None,
        "import_patterns": [r"from fastapi import", r"import fastapi"],
        "config_files": [],
        "requirements_pattern": r"^fastapi",
    },
    {
        "name": "Django",
        "manifest_key": None,
        "import_patterns": [r"from django", r"import django"],
        "config_files": ["manage.py", "settings.py"],
        "requirements_pattern": r"^[Dd]jango",
    },
    {
        "name": "Flask",
        "manifest_key": None,
        "import_patterns": [r"from flask import", r"import flask"],
        "config_files": [],
        "requirements_pattern": r"^[Ff]lask",
    },
    # Rust frameworks
    {
        "name": "Axum",
        "manifest_key": "dependencies.axum",
        "import_patterns": [r"use axum"],
        "config_files": [],
    },
    {
        "name": "Actix-web",
        "manifest_key": "dependencies.actix-web",
        "import_patterns": [r"use actix_web"],
        "config_files": [],
    },
]

class FrameworkDetector:
    @property
    def name(self) -> str:
        return "framework-detector"

    def supports(self, context: AnalysisContext) -> bool:
        return True  # Always runs; checks for evidence internally

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        extracted = []
        errors = []
        repo_path = context.local_path

        # Load package.json for version info if present
        package_json = {}
        pj_path = repo_path / "package.json"
        if pj_path.exists():
            try:
                package_json = json.loads(pj_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Load requirements.txt for Python version info
        requirements_txt = ""
        req_path = repo_path / "requirements.txt"
        if req_path.exists():
            requirements_txt = req_path.read_text(encoding="utf-8", errors="replace")

        # Collect text from source files for pattern matching (sample ~100 files)
        import_text = self._collect_import_text(repo_path)

        for sig in FRAMEWORK_SIGNATURES:
            evidence = {}
            version = None

            # 1. Check package.json dependency
            if sig.get("manifest_key") and package_json:
                keys = sig["manifest_key"].split(".")
                val = package_json
                for k in keys:
                    val = val.get(k, {}) if isinstance(val, dict) else None
                if val and isinstance(val, str):
                    evidence["manifest"] = f"{pj_path}:{sig['manifest_key']}={val}"
                    version = val.lstrip("^~>=")

            # 2. Check requirements.txt
            if sig.get("requirements_pattern") and requirements_txt:
                pattern = sig["requirements_pattern"]
                match = re.search(pattern + r"[>=<~!]+([\d\.]+)", requirements_txt, re.MULTILINE)
                if match:
                    evidence["requirements"] = f"requirements.txt matches {pattern}, version {match.group(1)}"
                    version = match.group(1)

            # 3. Check import patterns in source files
            for pat in sig.get("import_patterns", []):
                match = re.search(pat, import_text, re.MULTILINE)
                if match:
                    evidence["import_pattern"] = f"Found import pattern: {pat}"
                    break

            # 4. Check config files
            for cfg_file in sig.get("config_files", []):
                cfg_path = repo_path / cfg_file
                if cfg_path.exists():
                    evidence["config_file"] = str(cfg_path)
                    break

            if evidence:
                logger.info(f"Detected framework: {sig['name']} v{version} — evidence: {evidence}")
                extracted.append({
                    "name": sig["name"],
                    "version": version,
                    "evidence": evidence,
                })

        return AnalysisResult(
            analyzer_name=self.name,
            success=True,
            metrics={"frameworks_detected": len(extracted)},
            errors=errors,
            extracted_entities=extracted,
        )

    def _collect_import_text(self, repo_path: Path) -> str:
        """Collect the first N lines of source files for import scanning."""
        chunks = []
        extensions = (".py", ".js", ".ts", ".jsx", ".tsx", ".rs")
        count = 0
        for ext in extensions:
            for src_file in repo_path.rglob(f"*{ext}"):
                if ".git" in src_file.parts or "node_modules" in src_file.parts:
                    continue
                try:
                    lines = src_file.read_text(encoding="utf-8", errors="replace").splitlines()[:30]
                    chunks.append("\n".join(lines))
                    count += 1
                    if count >= 100:
                        break
                except Exception:
                    pass
            if count >= 100:
                break
        return "\n".join(chunks)
