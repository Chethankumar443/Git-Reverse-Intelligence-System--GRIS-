"""
Language & framework detector.

Determines the primary programming language of a repository (and any
secondary languages) purely from the file manifest produced in Phase 1.
Also detects common frameworks by scanning for framework-specific
indicator files and import statements.

No I/O beyond reading file extensions and small content samples.
Detection is intentionally fast: < 10 ms on any repo.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from git_reverse.core.logging import get_logger
from git_reverse.ingestion.validator import FileManifest

log = get_logger(__name__)

# ── Extension → Language map ──────────────────────────────────────────────────
_EXT_TO_LANGUAGE: dict[str, str] = {
    # Python
    ".py": "python",
    ".pyi": "python",
    ".pyx": "python",
    # JavaScript / TypeScript
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    # Rust
    ".rs": "rust",
    # Go
    ".go": "go",
    # Ruby
    ".rb": "ruby",
    ".erb": "ruby",
    # Java / Kotlin
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    # C / C++
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    # C#
    ".cs": "csharp",
    # PHP
    ".php": "php",
    # Swift
    ".swift": "swift",
    # Shell
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
}

# ── Framework indicators ──────────────────────────────────────────────────────
# Each entry: (language, framework, list_of_indicator_filenames_or_patterns)
_FRAMEWORK_INDICATORS: list[tuple[str, str, list[str]]] = [
    # Python frameworks
    ("python", "fastapi", ["fastapi", "from fastapi"]),
    ("python", "django", ["django", "DJANGO_SETTINGS_MODULE", "manage.py"]),
    ("python", "flask", ["flask", "from flask"]),
    ("python", "sqlalchemy", ["sqlalchemy", "from sqlalchemy"]),
    ("python", "pydantic", ["pydantic", "from pydantic"]),
    ("python", "pytorch", ["torch", "import torch"]),
    ("python", "tensorflow", ["tensorflow", "import tensorflow"]),
    # JavaScript / TypeScript
    ("javascript", "react", ["react", "from 'react'", 'from "react"']),
    ("typescript", "react", ["react", "from 'react'", 'from "react"']),
    ("javascript", "nextjs", ["next/", "next.config"]),
    ("typescript", "nextjs", ["next/", "next.config"]),
    ("javascript", "express", ["express", "require('express')"]),
    ("javascript", "vue", ["vue", "from 'vue'"]),
    ("typescript", "angular", ["@angular/", "@Component"]),
    # Rust
    ("rust", "tokio", ["tokio", "[dependencies]\ntokio"]),
    ("rust", "actix-web", ["actix-web", "actix_web"]),
    ("rust", "axum", ["axum"]),
    # Go
    ("go", "gin", ["gin-gonic/gin", "github.com/gin-gonic"]),
    ("go", "echo", ["labstack/echo"]),
    ("go", "fiber", ["gofiber/fiber"]),
]

# ── Config-file → Framework map ───────────────────────────────────────────────
_CONFIG_FILE_FRAMEWORKS: dict[str, tuple[str, str]] = {
    "next.config.js": ("javascript", "nextjs"),
    "next.config.ts": ("typescript", "nextjs"),
    "nuxt.config.ts": ("javascript", "nuxt"),
    "angular.json": ("typescript", "angular"),
    "vue.config.js": ("javascript", "vue"),
    "svelte.config.js": ("javascript", "svelte"),
    "cargo.toml": ("rust", "cargo"),
    "go.mod": ("go", "go-modules"),
    "manage.py": ("python", "django"),
    "settings.py": ("python", "django"),
}


# ── Result types ──────────────────────────────────────────────────────────────
@dataclass
class LanguageProfile:
    """
    Language composition of a repository.

    Attributes:
        primary:    The dominant programming language (most source files).
        secondary:  Other languages found (sorted by file count, descending).
        file_counts: Raw counts per language.
        frameworks: Detected frameworks, keyed by language.
    """

    primary: str
    secondary: list[str] = field(default_factory=list)
    file_counts: dict[str, int] = field(default_factory=dict)
    frameworks: dict[str, list[str]] = field(default_factory=dict)

    @property
    def all_languages(self) -> list[str]:
        return [self.primary, *self.secondary]


# ── Detector ──────────────────────────────────────────────────────────────────
class LanguageDetector:
    """
    Detects the primary language and frameworks in a repository.

    Uses a three-pass strategy:
      1. Extension counting over the file manifest.
      2. Config-file scanning for framework signals.
      3. Shallow content sampling (first 4 KB of key files) for imports.
    """

    def detect(self, manifest: FileManifest, repo_root: Path) -> LanguageProfile:
        """
        Analyse the manifest and return a LanguageProfile.

        Args:
            manifest:  The FileManifest from RepositoryValidator.
            repo_root: The repository root (for config file scanning).

        Returns:
            A LanguageProfile with primary language and detected frameworks.
        """
        file_counts = self._count_by_extension(manifest.source_files)

        if not file_counts:
            log.warning("language_detection_no_source_files")
            return LanguageProfile(primary="unknown")

        sorted_langs = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_langs[0][0]
        secondary = [lang for lang, _ in sorted_langs[1:] if lang != primary]

        frameworks: dict[str, list[str]] = {}
        frameworks.update(self._detect_from_config_files(manifest.config_files))
        frameworks.update(self._detect_from_content(manifest.source_files, file_counts))

        profile = LanguageProfile(
            primary=primary,
            secondary=secondary,
            file_counts=dict(file_counts),
            frameworks=frameworks,
        )

        log.info(
            "language_detected",
            primary=primary,
            secondary=secondary,
            frameworks={k: v for k, v in frameworks.items() if v},
        )
        return profile

    # ── Private helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _count_by_extension(files: list[Path]) -> Counter[str]:
        counts: Counter[str] = Counter()
        for f in files:
            lang = _EXT_TO_LANGUAGE.get(f.suffix.lower())
            if lang:
                counts[lang] += 1
        return counts

    @staticmethod
    def _detect_from_config_files(
        config_files: list[Path],
    ) -> dict[str, list[str]]:
        """Detect frameworks by the presence of well-known config files."""
        result: dict[str, list[str]] = {}
        config_names = {f.name.lower() for f in config_files}
        for filename, (lang, framework) in _CONFIG_FILE_FRAMEWORKS.items():
            if filename.lower() in config_names:
                result.setdefault(lang, [])
                if framework not in result[lang]:
                    result[lang].append(framework)
        return result

    @staticmethod
    def _detect_from_content(
        source_files: list[Path],
        file_counts: Counter[str],
    ) -> dict[str, list[str]]:
        """
        Sample a few files per language and scan for framework import patterns.

        Only reads the first 4 KB of each sampled file to stay fast.
        Samples at most 20 files per language to bound I/O.
        """
        # Group files by language
        by_lang: dict[str, list[Path]] = {}
        for f in source_files:
            lang = _EXT_TO_LANGUAGE.get(f.suffix.lower())
            if lang:
                by_lang.setdefault(lang, []).append(f)

        result: dict[str, list[str]] = {}
        for lang, files in by_lang.items():
            sample = files[:20]
            combined = _read_sample(sample)
            for indicator_lang, framework, patterns in _FRAMEWORK_INDICATORS:
                if indicator_lang != lang:
                    continue
                if any(p in combined for p in patterns):
                    result.setdefault(lang, [])
                    if framework not in result[lang]:
                        result[lang].append(framework)

        return result


def _read_sample(files: list[Path], max_bytes: int = 4096) -> str:
    """Read the first `max_bytes` of each file and concatenate."""
    parts: list[str] = []
    for f in files:
        try:
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                parts.append(fh.read(max_bytes))
        except OSError:
            continue
    return "\n".join(parts)
