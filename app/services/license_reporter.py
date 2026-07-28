"""
License Reporter — Generates License Compliance Reports (PRD §62).

Builds a structured compliance report from repository analysis data:
detected licenses per file/dependency, copyleft flags, SPDX breakdown.
"""
import datetime
from typing import Dict, Any, List, Optional

# SPDX copyleft families (strong / weak)
STRONG_COPYLEFT = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "EUPL-1.1", "EUPL-1.2", "CDDL-1.0"}
WEAK_COPYLEFT = {"LGPL-2.1", "LGPL-3.0", "MPL-2.0", "EPL-1.0", "EPL-2.0", "EUPL-1.1"}
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense", "0BSD", "CC0-1.0"}

COPYLEFT_ADVISORIES: Dict[str, str] = {
    "GPL-2.0": "GPL-2.0: Derivative works that distribute compiled binaries must also distribute source under GPL-2.0.",
    "GPL-3.0": "GPL-3.0: Derivative works must be released under GPL-3.0. Includes patent retaliation clause.",
    "AGPL-3.0": "AGPL-3.0: Network use counts as distribution. SaaS products using this code must open-source their modifications.",
    "LGPL-2.1": "LGPL-2.1: Weak copyleft — libraries may be linked without relicensing, but modifications to the library itself must be shared.",
    "LGPL-3.0": "LGPL-3.0: Similar to LGPL-2.1 with additional patent protection.",
    "MPL-2.0": "MPL-2.0: File-level copyleft — modified files must remain MPL-2.0, but can be combined with proprietary code.",
}


def classify_license(spdx_id: str) -> str:
    """Returns 'permissive', 'weak-copyleft', 'strong-copyleft', or 'unknown'."""
    if spdx_id in STRONG_COPYLEFT:
        return "strong-copyleft"
    if spdx_id in WEAK_COPYLEFT:
        return "weak-copyleft"
    if spdx_id in PERMISSIVE:
        return "permissive"
    return "unknown"


def generate_license_report(
    repo_name: str,
    repo_url: str,
    detected_license: str,
    dependency_details: Optional[List[Dict[str, Any]]] = None,
    commit_sha: str = "",
    branch: str = "",
) -> Dict[str, Any]:
    """Generates a structured License Compliance Report.

    Args:
        repo_name: Full repo name (owner/repo).
        repo_url: GitHub URL.
        detected_license: SPDX license ID detected from the license file.
        dependency_details: Optional list of {name, version, license} dicts.
        commit_sha: Repository commit SHA for traceability.
        branch: Repository branch.

    Returns:
        A structured report dict including copyleft flags, advisories,
        and a human-readable text summary.
    """
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dep_details = dependency_details or []

    # Collect all unique licenses
    all_licenses = set()
    if detected_license and detected_license not in ("none", "custom", "unknown"):
        all_licenses.add(detected_license)
    for dep in dep_details:
        lic = dep.get("license", "")
        if lic and lic not in ("none", "unknown", ""):
            all_licenses.add(lic)

    # Classify licenses
    classifications: Dict[str, str] = {lic: classify_license(lic) for lic in all_licenses}
    has_strong_copyleft = any(c == "strong-copyleft" for c in classifications.values())
    has_weak_copyleft = any(c == "weak-copyleft" for c in classifications.values())
    has_copyleft = has_strong_copyleft or has_weak_copyleft

    # Collect applicable advisories
    advisories = []
    for lic in all_licenses:
        if lic in COPYLEFT_ADVISORIES:
            advisories.append(COPYLEFT_ADVISORIES[lic])

    # Build human-readable summary text
    main_class = classify_license(detected_license) if detected_license else "unknown"
    lines = [
        f"# License Compliance Report — {repo_name}",
        f"",
        f"**Repository**: {repo_url}",
        f"**Commit**: {commit_sha or 'N/A'} ({branch or 'default branch'})",
        f"**Generated**: {date_str}",
        f"",
        f"## Primary License",
        f"- **Detected**: {detected_license or 'Not detected'}",
        f"- **Classification**: {main_class}",
        f"- **Copyleft Obligations**: {'YES' if has_copyleft else 'NO'}",
        f"",
    ]

    if dep_details:
        lines.append("## Dependency Licenses")
        for dep in dep_details[:30]:
            name = dep.get("name", "unknown")
            ver = dep.get("version", "")
            lic = dep.get("license", "unknown")
            cls = classify_license(lic)
            ver_str = f" v{ver}" if ver else ""
            lines.append(f"- **{name}**{ver_str}: `{lic}` ({cls})")
        lines.append("")

    if advisories:
        lines.append("## Copyleft Obligations & Advisories")
        for adv in advisories:
            lines.append(f"\n> ⚠ {adv}")
        lines.append("")

    lines.extend([
        "## Compliance Summary",
        f"| License | Classification | Copyleft |",
        f"|---------|---------------|---------|",
    ])
    for lic, cls in sorted(classifications.items()):
        copyleft_flag = "✓ YES" if "copyleft" in cls else "— No"
        lines.append(f"| {lic} | {cls} | {copyleft_flag} |")

    lines.extend([
        "",
        "---",
        "*Generated by Git Reverse. This report is informational only and is not legal advice.*",
        "*Consult a qualified attorney for licensing compliance decisions.*",
    ])

    return {
        "repo_name": repo_name,
        "repo_url": repo_url,
        "detected_license": detected_license,
        "all_licenses": sorted(all_licenses),
        "classifications": classifications,
        "has_copyleft": has_copyleft,
        "has_strong_copyleft": has_strong_copyleft,
        "has_weak_copyleft": has_weak_copyleft,
        "advisories": advisories,
        "dependency_details": dep_details,
        "generated_at": date_str,
        "report_text": "\n".join(lines),
    }


def export_license_report_markdown(report: Dict[str, Any], filepath: str) -> bool:
    """Exports the license compliance report to a Markdown file."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report.get("report_text", "No report content."))
        return True
    except Exception:
        return False
