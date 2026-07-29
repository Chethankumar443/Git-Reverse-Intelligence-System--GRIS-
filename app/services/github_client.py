import re
import os
import zipfile
import io
from typing import Dict, Any, List, Optional, Tuple
import requests

# Valid GitHub repo URL patterns (HTTPS, SSH, git://)
GITHUB_URL_REGEX = re.compile(
    r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)(?:\.git)?/?$"
)

IGNORED_DIRS = {
    ".git", ".github", "node_modules", "vendor", "venv", ".venv",
    "__pycache__", "dist", "build", "target", ".idea", ".vscode",
    ".next", ".nuxt", "bin", "obj", ".cargo"
}

IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".webm", ".zip", ".tar", ".gz", ".7z",
    ".pdf", ".exe", ".dll", ".so", ".dylib", ".pyc", ".db", ".sqlite",
    ".bin", ".dat", ".wasm", ".o", ".a", ".class", ".psd", ".ai"
}

MAX_FILE_SIZE_BYTES = 300 * 1024  # 300 KB limit per file

# SPDX / Common License Patterns
LICENSE_PATTERNS = [
    ("AGPL-3.0", [r"GNU AFFERO GENERAL PUBLIC LICENSE", r"AGPLv3", r"AGPL-3\.0"]),
    ("GPL-3.0", [r"GNU GENERAL PUBLIC LICENSE", r"GPLv3", r"GPL-3\.0"]),
    ("GPL-2.0", [r"GNU GENERAL PUBLIC LICENSE", r"GPLv2", r"GPL-2\.0"]),
    ("LGPL-3.0", [r"GNU LESSER GENERAL PUBLIC LICENSE", r"LGPLv3"]),
    ("Apache-2.0", [r"APACHE LICENSE", r"HTTP://WWW\.APACHE\.ORG/LICENSES/LICENSE-2\.0"]),
    ("MIT", [r"MIT LICENSE", r"PERMISSION IS HEREBY GRANTED, FREE OF CHARGE"]),
    ("BSD-3-Clause", [r"BSD 3-CLAUSE", r"REDISTRIBUTION AND USE IN SOURCE AND BINARY FORMS"]),
    ("BSD-2-Clause", [r"BSD 2-CLAUSE"]),
    ("MPL-2.0", [r"MOZILLA PUBLIC LICENSE", r"MPL 2\.0"]),
    ("Unlicense", [r"THIS IS FREE AND UNENCUMBERED SOFTWARE RELEASED INTO THE PUBLIC DOMAIN"]),
    ("ISC", [r"ISC LICENSE", r"PERMISSION TO USE, COPY, MODIFY, AND/OR DISTRIBUTE THIS SOFTWARE"]),
    ("CC-BY-4.0", [r"CREATIVE COMMONS ATTRIBUTION 4\.0"]),
]


def validate_github_url(url: str) -> Optional[Tuple[str, str]]:
    """Validates GitHub URL and returns (owner, repo_name) tuple."""
    if not url:
        return None
    match = GITHUB_URL_REGEX.match(url.strip())
    if match:
        owner, repo = match.group(1), match.group(2)
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo
    return None


def detect_license_type(content: str) -> str:
    """Detects license type from text content using regex pattern matching."""
    text = content.upper()
    for lic_id, patterns in LICENSE_PATTERNS:
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return lic_id
    return "Custom / Proprietary"


class GitHubClient:
    """Production GitHub client supporting URL validation, shallow zipball fetching,

    fallback tree API fetching, file size filtering, and license classification.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "GitReverseApp/1.0"}
        if token and token.strip():
            self.headers["Authorization"] = f"token {token.strip()}"

    def fetch_repository_data(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetches repository metadata and files using Zipball with REST API fallback."""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                resp = requests.get(url, headers=self.headers, timeout=12)
            except requests.RequestException as e:
                raise ValueError(f"Network error connecting to GitHub: {str(e)}")

            if resp.status_code == 200:
                break
            elif resp.status_code in (403, 429):
                reset_header = resp.headers.get("X-RateLimit-Reset")
                remaining = resp.headers.get("X-RateLimit-Remaining", "0")
                if remaining == "0" or "rate limit" in resp.text.lower():
                    wait_str = ""
                    if reset_header:
                        try:
                            import time
                            reset_ts = int(reset_header)
                            now_ts = int(time.time())
                            mins = max(1, (reset_ts - now_ts) // 60)
                            wait_str = f" Reset in ~{mins} minutes."
                        except Exception:
                            pass
                    raise ValueError(
                        f"GitHub API rate limit reached.{wait_str} "
                        f"Add a GitHub Personal Access Token in Settings to raise your limit to 5,000 requests/hr."
                    )
                elif attempt < max_retries:
                    import time
                    time.sleep(1.5 * (attempt + 1))
                    continue
            elif resp.status_code == 404:
                raise ValueError(f"Repository '{owner}/{repo}' not found on GitHub. Check owner and repository name.")
            elif resp.status_code == 401:
                raise ValueError("GitHub API 401 Unauthorized. Check your GitHub Token in Settings.")
            else:
                raise ValueError(f"GitHub API returned HTTP {resp.status_code}")

        meta = resp.json()
        primary_lang = meta.get("language") or "Unknown"
        default_branch = meta.get("default_branch", "main")

        # §50 Version Tracking: fetch latest commit SHA for the default branch
        commit_sha = ""
        repo_tag = ""
        try:
            branch_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{default_branch}"
            branch_resp = requests.get(branch_url, headers=self.headers, timeout=8)
            if branch_resp.status_code == 200:
                commit_sha = branch_resp.json().get("commit", {}).get("sha", "")[:12]
        except Exception:
            pass
        # Also try to get latest tag
        try:
            tags_url = f"https://api.github.com/repos/{owner}/{repo}/tags"
            tags_resp = requests.get(tags_url, headers=self.headers, timeout=6)
            if tags_resp.status_code == 200:
                tags = tags_resp.json()
                if tags:
                    repo_tag = tags[0].get("name", "")
        except Exception:
            pass

        # Attempt Zipball Download
        zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{default_branch}"
        files_map: Dict[str, str] = {}
        detected_license = "none"

        try:
            zip_resp = requests.get(zip_url, headers=self.headers, timeout=25)
            if zip_resp.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
                    namelist = zf.namelist()
                    root_prefix = namelist[0].split("/")[0] + "/" if namelist else ""

                    for full_name in namelist:
                        if full_name.endswith("/") or not full_name.startswith(root_prefix):
                            continue

                        rel_path = full_name[len(root_prefix):]
                        parts = rel_path.split("/")

                        if any(part in IGNORED_DIRS for part in parts[:-1]):
                            continue

                        filename = parts[-1]
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in IGNORED_EXTENSIONS:
                            continue

                        info = zf.getinfo(full_name)
                        if info.file_size > MAX_FILE_SIZE_BYTES:
                            continue

                        try:
                            raw_bytes = zf.read(full_name)
                            content = raw_bytes.decode("utf-8", errors="replace")

                            # License detection on root license files
                            if filename.upper() in ("LICENSE", "LICENSE.MD", "LICENSE.TXT", "COPYING"):
                                detected_license = detect_license_type(content)

                            files_map[rel_path] = content
                        except Exception:
                            continue
        except Exception:
            pass

        # License fallback from GitHub metadata if not detected in files
        if detected_license == "none" and meta.get("license"):
            detected_license = meta["license"].get("spdx_id") or meta["license"].get("name") or "custom"

        # Fallback to GitHub Git Trees REST API if Zipball returned no files
        if not files_map:
            files_map, tree_license = self._fetch_via_tree_api(owner, repo, default_branch)
            if detected_license == "none" and tree_license != "none":
                detected_license = tree_license

        return {
            "owner": owner,
            "repo_name": f"{owner}/{repo}",
            "primary_language": primary_lang,
            "file_count": len(files_map),
            "files": files_map,
            "detected_license": detected_license,
            "default_branch": default_branch,
            "stars": meta.get("stargazers_count", 0),
            "commit_sha": commit_sha,
            "repo_tag": repo_tag,
        }

    def _fetch_via_tree_api(self, owner: str, repo: str, default_branch: str) -> Tuple[Dict[str, str], str]:
        """Fallback method fetching repository files via GitHub recursive Git Trees REST API."""
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        files_map: Dict[str, str] = {}
        detected_license = "none"

        try:
            resp = requests.get(tree_url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                return files_map, detected_license

            tree_data = resp.json().get("tree", [])
            max_files = 80  # Limit fallback tree API downloads to top 80 source files

            for item in tree_data:
                if len(files_map) >= max_files:
                    break

                if item.get("type") != "blob":
                    continue

                path = item.get("path", "")
                size = item.get("size", 0)

                parts = path.split("/")
                if any(part in IGNORED_DIRS for part in parts[:-1]):
                    continue

                filename = parts[-1]
                ext = os.path.splitext(filename)[1].lower()
                if ext in IGNORED_EXTENSIONS:
                    continue

                if size > MAX_FILE_SIZE_BYTES:
                    continue

                # Fetch raw content of blob
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{path}"
                try:
                    raw_resp = requests.get(raw_url, headers=self.headers, timeout=6)
                    if raw_resp.status_code == 200:
                        content = raw_resp.text
                        if filename.upper() in ("LICENSE", "LICENSE.MD", "LICENSE.TXT", "COPYING"):
                            detected_license = detect_license_type(content)
                        files_map[path] = content
                except Exception:
                    continue

        except Exception:
            pass

        return files_map, detected_license

