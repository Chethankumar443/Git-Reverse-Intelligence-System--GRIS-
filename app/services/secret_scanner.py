"""
Secret Scanner — Local-only credential pattern detector (PRD §53).

Scans repository file contents for API keys, tokens, private keys, and
password-shaped patterns. NEVER transmits detected values to any LLM or
external service. Returns only metadata: file path, pattern type, line number.
"""
import re
from typing import List, Dict, Any

# Patterns: (label, regex). Groups must NOT capture the secret value.
SECRET_PATTERNS: List[tuple] = [
    ("AWS Access Key",         r"(?i)AKIA[0-9A-Z]{16}"),
    ("AWS Secret Key",         r"(?i)aws[_\-\s]?secret[_\-\s]?access[_\-\s]?key\s*=\s*['\"]?[A-Za-z0-9/+=]{40}"),
    ("OpenAI API Key",         r"sk-(proj-)?[A-Za-z0-9\-_]{20,}"),
    ("OpenRouter API Key",     r"sk-or-v1-[A-Za-z0-9]{20,}"),
    ("Groq API Key",           r"gsk_[A-Za-z0-9]{20,}"),
    ("Anthropic API Key",      r"sk-ant-[A-Za-z0-9\-]{20,}"),
    ("GitHub Token (PAT)",     r"ghp_[A-Za-z0-9]{36}"),
    ("GitHub Actions Token",   r"ghs_[A-Za-z0-9]{36}"),
    ("GitHub OAuth Token",     r"gho_[A-Za-z0-9]{36}"),
    ("Google API Key",         r"AIza[0-9A-Za-z\-_]{35}"),
    ("Firebase URL",           r"https://[a-zA-Z0-9\-]+\.firebaseio\.com"),
    ("Stripe Secret Key",      r"sk_live_[A-Za-z0-9]{24,}"),
    ("Stripe Publishable Key", r"pk_live_[A-Za-z0-9]{24,}"),
    ("Slack Bot Token",        r"xoxb-[0-9A-Za-z\-]{40,}"),
    ("Slack User Token",       r"xoxp-[0-9A-Za-z\-]{40,}"),
    ("Twilio Account SID",     r"AC[a-zA-Z0-9]{32}"),
    ("SendGrid API Key",       r"SG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}"),
    ("JWT (bare)",             r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
    ("Private Key Block",      r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ("Password in Assignment", r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"](?!your|placeholder|changeme|xxx|<)[^'\"]{6,}['\"]"),
    ("Database URL",           r"(?i)(mysql|postgres|postgresql|mongodb|redis|sqlite)://[^\s'\"]+:[^\s'\"@]+@"),
    ("Connection String",      r"(?i)Server=.{1,60};Database=.{1,60};User"),
    ("Generic Secret Assign",  r"(?i)(secret|api_key|apikey|access_token)\s*[:=]\s*['\"][A-Za-z0-9\-_]{12,}['\"]"),
    ("Potential .env Line",    r"(?m)^[A-Z_]{4,}\s*=\s*['\"]?[^\n'\"]{10,}['\"]?$"),
]

# Files that are commonly expected to contain dummy/placeholder secrets — lower severity
LOW_SEVERITY_INDICATORS = {
    ".env.example", ".env.sample", ".env.template",
    "README.md", "readme.md", "CONTRIBUTING.md",
    "example.env", "sample.env"
}

# Extensions to skip entirely for secret scanning (binary / non-text)
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".gif", ".ico", ".svg", ".woff", ".ttf", ".eot",
    ".mp4", ".zip", ".tar", ".gz", ".pdf", ".exe", ".dll", ".so",
    ".pyc", ".db", ".sqlite", ".bin", ".dat", ".wasm", ".o", ".a"
}

MAX_SCAN_SIZE = 150 * 1024  # 150 KB per file — skip larger files

_COMPILED: List[tuple] = [(label, re.compile(pat)) for label, pat in SECRET_PATTERNS]


def scan_files(files: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Scans a dict of {filepath: content} for credential-shaped patterns.

    Returns a list of findings. Each finding contains:
        - path: str — relative file path
        - pattern_type: str — human-readable pattern label
        - line_number: int — approximate line where match was found
        - is_example_file: bool — True if the file is likely a template/example
        - severity: str — 'high' or 'low'

    IMPORTANT: The actual matched string / secret VALUE is never included.
    """
    findings: List[Dict[str, Any]] = []

    for path, content in files.items():
        if not content:
            continue

        import os
        ext = os.path.splitext(path)[1].lower()
        if ext in SKIP_EXTENSIONS:
            continue

        if len(content) > MAX_SCAN_SIZE:
            continue

        filename = os.path.basename(path).lower()
        is_example = filename in LOW_SEVERITY_INDICATORS or any(
            indicator in filename for indicator in (".example", ".sample", ".template")
        )

        lines = content.split("\n")
        found_in_file = set()  # de-duplicate pattern types per file

        for label, compiled in _COMPILED:
            for line_no, line in enumerate(lines, start=1):
                if len(line) > 2000:
                    continue
                if compiled.search(line):
                    key = (path, label)
                    if key in found_in_file:
                        continue
                    found_in_file.add(key)
                    findings.append({
                        "path": path,
                        "pattern_type": label,
                        "line_number": line_no,
                        "is_example_file": is_example,
                        "severity": "low" if is_example else "high",
                    })

    # Sort: high severity first, then by path
    findings.sort(key=lambda x: (x["severity"] == "low", x["path"]))
    return findings


def format_findings_summary(findings: List[Dict[str, Any]]) -> str:
    """Returns a human-readable summary of secret scan findings.

    NEVER includes the matched secret values.
    """
    if not findings:
        return "No potential secrets detected."

    high = [f for f in findings if f["severity"] == "high"]
    low = [f for f in findings if f["severity"] == "low"]

    lines = [f"⚠ Secret Scanner: {len(findings)} potential issue(s) found."]
    if high:
        lines.append(f"\n  HIGH Severity ({len(high)} issues):")
        for f in high[:8]:
            lines.append(f"    • {f['path']}:{f['line_number']} — {f['pattern_type']}")
    if low:
        lines.append(f"\n  LOW Severity / Example Files ({len(low)} issues):")
        for f in low[:4]:
            lines.append(f"    • {f['path']}:{f['line_number']} — {f['pattern_type']}")

    lines.append("\n  These are NOT sent to any LLM provider. Review recommended.")
    return "\n".join(lines)
