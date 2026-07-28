import traceback
from PySide6.QtCore import QThread, Signal
from app.services.github_client import validate_github_url, GitHubClient
from app.services.analyzer import CodebaseAnalyzer
from app.services.llm_client import LLMClient
from app.services.database import DatabaseManager, ANALYZER_VERSION
from app.services.secrets import SecretsManager
from app.services.secret_scanner import scan_files, format_findings_summary
from app.services.ignore_rules import build_ignore_rules


class AnalysisWorker(QThread):
    """Background worker thread executing repository ingestion, AST/manifest analysis,
    SQLite session persistence, and real-time LLM prompt streaming.
    Ensures INV2: Main UI thread never blocks.

    Extended with:
    - §48 Quantitative progress (files_done / total)
    - §50 Version tracking (commit_sha, branch, tag)
    - §52 Dependency intelligence
    - §53 Secret detection
    - §54 Ignore rules (.gitignore + .gitreverseignore)
    - §59 Prompt type selection
    - §64 Token usage callback
    """

    progress_signal = Signal(str)
    progress_pct_signal = Signal(int, int)    # §48: (files_done, total_files)
    meta_signal = Signal(dict)
    token_signal = Signal(str)
    error_signal = Signal(str)
    finished_signal = Signal(int, str)
    secrets_found_signal = Signal(list)       # §53: list of findings

    def __init__(self, repo_url: str, prompt_type: str = "Clone Prompt", parent=None):
        super().__init__(parent)
        self.repo_url = repo_url
        self.prompt_type = prompt_type
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            # 1. Validate GitHub URL
            self.progress_signal.emit("Validating GitHub repository URL format...")
            parsed = validate_github_url(self.repo_url)
            if not parsed:
                self.error_signal.emit("Invalid GitHub URL. Must be in format: https://github.com/owner/repository")
                return

            owner, repo_name = parsed
            full_repo_name = f"{owner}/{repo_name}"

            # 2. Fetch repo metadata & zipball tree
            self.progress_signal.emit(f"Connecting to GitHub API for {full_repo_name}...")
            gh_token = SecretsManager.get_github_token()
            client = GitHubClient(token=gh_token)

            self.progress_signal.emit("Downloading repository archive and filtering tree...")
            repo_data = client.fetch_repository_data(owner, repo_name)
            files_raw = repo_data["files"]
            source_license = repo_data["detected_license"]
            commit_sha = repo_data.get("commit_sha", "")
            branch = repo_data.get("default_branch", "")
            repo_tag = repo_data.get("repo_tag", "")

            if not files_raw:
                self.error_signal.emit("No valid text source files found in repository.")
                return

            # §54 Ignore Rules — filter out .gitignored and .gitreverseignore paths
            self.progress_signal.emit("Applying .gitignore and .gitreverseignore exclusion rules...")
            ignore_rules = build_ignore_rules(files_raw)
            files = ignore_rules.filter_files(files_raw)
            ignored_count = len(files_raw) - len(files)
            if ignored_count > 0:
                self.progress_signal.emit(f"  Excluded {ignored_count} files per ignore rules ({len(files)} remaining)")

            if self._is_cancelled:
                return

            # §53 Secret Scanner — run before analysis, never transmit results
            self.progress_signal.emit("Scanning for accidentally committed secrets (local-only, never sent to AI)...")
            secret_findings = scan_files(files)
            if secret_findings:
                self.progress_signal.emit(format_findings_summary(secret_findings))
                self.secrets_found_signal.emit(secret_findings)
            else:
                self.progress_signal.emit("  ✓ No potential secrets detected.")

            if self._is_cancelled:
                return

            # 3. §48 Quantitative progress: Codebase Analysis
            total_files = len(files)
            self.progress_signal.emit(f"Analyzing {total_files} files for languages, manifests, and entrypoints...")
            self.progress_pct_signal.emit(0, total_files)

            def on_progress(done, total):
                if total > 0:
                    self.progress_pct_signal.emit(done, total)

            analysis_res = CodebaseAnalyzer.analyze(
                files,
                primary_lang=repo_data["primary_language"],
                progress_callback=on_progress,
            )

            languages = analysis_res["detected_languages"]
            frameworks = analysis_res["detected_frameworks"]
            arch_pattern = analysis_res["architecture_pattern"]
            dependency_details = analysis_res.get("dependency_details", [])

            self.progress_pct_signal.emit(total_files, total_files)

            # 4. Create SQLite Session Record with version tracking (§50)
            db_mgr = DatabaseManager()
            session_rec = db_mgr.create_session(
                repo_url=self.repo_url,
                repo_name=full_repo_name,
                language=languages[0] if languages else "Unknown",
                file_count=len(files),
                source_license=source_license,
                commit_sha=commit_sha,
                branch=branch,
                repo_tag=repo_tag,
                secret_warnings=len([f for f in secret_findings if f["severity"] == "high"]),
            )

            meta_payload = {
                "session_id": session_rec.id,
                "repo_name": full_repo_name,
                "file_count": len(files),
                "source_license": source_license,
                "languages": languages,
                "frameworks": frameworks,
                "arch_pattern": arch_pattern,
                "entrypoints": analysis_res["entrypoints"],
                "commit_sha": commit_sha,
                "branch": branch,
                "repo_tag": repo_tag,
                "dependency_details": dependency_details,
                "secret_count": len(secret_findings),
            }
            self.meta_signal.emit(meta_payload)

            if self._is_cancelled:
                db_mgr.update_session_prompt(session_rec.id, "", status="cancelled")
                return

            # 5. Stream LLM Prompt (§59 prompt type selection)
            self.progress_signal.emit(f"Generating {self.prompt_type} via LLM stream...")
            api_key = SecretsManager.get_api_key()
            config = SecretsManager.load_config()

            if not api_key:
                self.token_signal.emit("\n[Notice: No LLM API Key configured in Settings. Using local analysis only.]\n")
                fallback_prompt = f"""# System Prompt — Recreating {full_repo_name}

## 1. Architecture Overview
- Repository: {full_repo_name}
- Primary Language: {languages[0] if languages else 'Unknown'}
- Frameworks: {', '.join(frameworks)}
- Architecture Pattern: {arch_pattern}
- Commit: {commit_sha or 'N/A'} ({branch or 'default'})
- Tag: {repo_tag or 'N/A'}

## 2. Detected Dependencies
{chr(10).join(f"- {d['name']} {d.get('version','')}" for d in dependency_details[:20]) or '- None detected'}

## 3. Responsible Use & License Attribution
- Source License: {source_license}
- Analyzer Version: {ANALYZER_VERSION}
- Generated by: Git Reverse Desktop
"""
                db_mgr.update_session_prompt(session_rec.id, fallback_prompt, status="complete")
                self.finished_signal.emit(session_rec.id, fallback_prompt)
                return

            llm_client = LLMClient(
                api_key=api_key,
                base_url=config.get("base_url", "https://api.openai.com/v1"),
                model_id=config.get("model_id", "gpt-4o"),
            )

            full_prompt_chunks = []
            file_list = list(files.keys())
            manifest_facts = [f["content"] for f in analysis_res["manifest_facts"]]

            # §64 Token usage tracking callback
            def on_token_usage(tokens: int):
                # Rough cost estimate at $0.01/1k tokens (varies by model)
                estimated_cost = (tokens / 1000) * 0.01
                db_mgr.log_token_usage(
                    tokens=tokens,
                    estimated_cost_usd=estimated_cost,
                    provider=config.get("provider_preset", ""),
                    model_id=config.get("model_id", ""),
                )

            stream = llm_client.stream_recreation_prompt(
                repo_name=full_repo_name,
                repo_url=self.repo_url,
                source_license=source_license,
                languages=languages,
                frameworks=frameworks,
                arch_pattern=arch_pattern,
                manifest_facts=manifest_facts,
                file_list=file_list,
                ast_summaries=analysis_res.get("ast_summaries", []),
                prompt_type=self.prompt_type,
                token_callback=on_token_usage,
            )

            for token in stream:
                if self._is_cancelled:
                    db_mgr.update_session_prompt(session_rec.id, "".join(full_prompt_chunks), status="interrupted")
                    self.error_signal.emit("Analysis stream interrupted by user.")
                    return
                full_prompt_chunks.append(token)
                self.token_signal.emit(token)

            accumulated_prompt = "".join(full_prompt_chunks)
            ast_syms = analysis_res.get("ast_summaries", [])
            db_mgr.update_session_prompt(
                session_rec.id,
                accumulated_prompt,
                status="complete",
                secret_warnings=len([f for f in secret_findings if f["severity"] == "high"]),
                code_symbols="\n".join(ast_syms),
            )
            self.progress_signal.emit("Repository analysis and prompt generation complete.")
            self.finished_signal.emit(session_rec.id, accumulated_prompt)

        except Exception as e:
            tb = traceback.format_exc()
            self.error_signal.emit(f"Error during repository analysis: {str(e)}")
