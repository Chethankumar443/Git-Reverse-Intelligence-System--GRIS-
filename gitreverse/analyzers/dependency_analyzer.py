import json
import re
import tomllib
from pathlib import Path
from typing import List
from gitreverse.analyzers.base import Analyzer, AnalysisContext, AnalysisResult
from gitreverse.storage.database import DatabaseManager
from gitreverse.utils.logging import get_logger

logger = get_logger("analyzers.dependency")

# Manifest file names mapped to their type
MANIFEST_FILES = {
    "package.json": "nodejs",
    "requirements.txt": "python",
    "requirements-dev.txt": "python-dev",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "pom.xml": "java",
    "build.gradle": "gradle",
    "Gemfile": "ruby",
    "composer.json": "php",
}

class DependencyAnalyzer:
    @property
    def name(self) -> str:
        return "dependency-analyzer"

    def supports(self, context: AnalysisContext) -> bool:
        for manifest in MANIFEST_FILES:
            if (context.local_path / manifest).exists():
                return True
        return False

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        extracted = []
        errors = []

        for manifest_name, ecosystem in MANIFEST_FILES.items():
            manifest_path = context.local_path / manifest_name
            if not manifest_path.exists():
                continue

            logger.info(f"Parsing manifest: {manifest_path}")
            try:
                deps = self._parse_manifest(manifest_path, ecosystem, context.repo_id)
                extracted.extend(deps)
            except Exception as e:
                msg = f"Failed to parse {manifest_name}: {e}"
                logger.error(msg)
                errors.append(msg)

        return AnalysisResult(
            analyzer_name=self.name,
            success=len(errors) == 0,
            metrics={"total_dependencies": len(extracted)},
            errors=errors,
            extracted_entities=extracted,
        )

    def _parse_manifest(self, manifest_path: Path, ecosystem: str, repo_id: int) -> List[dict]:
        content = manifest_path.read_text(encoding="utf-8", errors="replace")
        deps = []
        source = str(manifest_path)

        if ecosystem == "nodejs":
            data = json.loads(content)
            for pkg, version in data.get("dependencies", {}).items():
                deps.append({"repository_id": repo_id, "package_name": pkg, "version": version, "source_file": source, "type": "runtime"})
            for pkg, version in data.get("devDependencies", {}).items():
                deps.append({"repository_id": repo_id, "package_name": pkg, "version": version, "source_file": source, "type": "dev"})
            for pkg, version in data.get("peerDependencies", {}).items():
                deps.append({"repository_id": repo_id, "package_name": pkg, "version": version, "source_file": source, "type": "peer"})

        elif ecosystem in ("python", "python-dev"):
            dep_type = "dev" if "dev" in ecosystem else "runtime"
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Strip version specifiers
                match = re.match(r"([a-zA-Z0-9_\-\.]+)([>=<!~^].*)?", line)
                if match:
                    pkg = match.group(1)
                    version = match.group(2) or None
                    deps.append({"repository_id": repo_id, "package_name": pkg, "version": version, "source_file": source, "type": dep_type})

        elif ecosystem == "rust":
            data = tomllib.loads(content)
            for pkg, version in data.get("dependencies", {}).items():
                v = version if isinstance(version, str) else version.get("version")
                deps.append({"repository_id": repo_id, "package_name": pkg, "version": v, "source_file": source, "type": "runtime"})
            for pkg, version in data.get("dev-dependencies", {}).items():
                v = version if isinstance(version, str) else version.get("version")
                deps.append({"repository_id": repo_id, "package_name": pkg, "version": v, "source_file": source, "type": "dev"})

        elif ecosystem == "go":
            for line in content.splitlines():
                match = re.match(r"\s+([^\s]+)\s+([^\s]+)", line)
                if match:
                    deps.append({"repository_id": repo_id, "package_name": match.group(1), "version": match.group(2), "source_file": source, "type": "runtime"})

        return deps
