"""
Git Reverse — Async Analysis Runner
Replaces PySide6 QThread AnalysisWorker with a pure asyncio coroutine
that can be driven by FastAPI WebSocket endpoints.
"""
import asyncio
import logging
import traceback
from typing import AsyncGenerator, Dict, Any

from app.services.github_client import validate_github_url, GitHubClient
from app.services.analyzer import CodebaseAnalyzer
from app.services.llm_client import LLMClient
from app.services.database import DatabaseManager
from app.services.secrets import SecretsManager
from app.services.secret_scanner import scan_files, format_findings_summary
from app.services.ignore_rules import build_ignore_rules

logger = logging.getLogger("gris.runner")


async def run_analysis(
    repo_url: str,
    prompt_type: str = "Clone Prompt",
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Async generator that yields structured event dicts during repo analysis.

    Event shapes:
      {"type": "progress", "msg": str}
      {"type": "progress_pct", "done": int, "total": int}
      {"type": "meta", "data": dict}
      {"type": "token", "text": str}
      {"type": "secrets", "findings": list}
      {"type": "error", "msg": str}
      {"type": "done", "session_id": int, "prompt": str}
    """
    try:
        # ── 1. Validate URL ───────────────────────────────────────────────────
        yield {"type": "progress", "msg": "Validating GitHub repository URL format..."}
        parsed = validate_github_url(repo_url)
        if not parsed:
            yield {"type": "error", "msg": "Invalid GitHub URL. Expected: https://github.com/owner/repository"}
            return

        owner, repo_name = parsed
        full_repo_name = f"{owner}/{repo_name}"

        # ── 2. Fetch GitHub metadata & zipball ────────────────────────────────
        yield {"type": "progress", "msg": f"Connecting to GitHub API for {full_repo_name}..."}
        gh_token = await asyncio.to_thread(SecretsManager.get_github_token)
        client = GitHubClient(token=gh_token)

        yield {"type": "progress", "msg": "Downloading repository archive and filtering tree..."}
        repo_data = await asyncio.to_thread(client.fetch_repository_data, owner, repo_name)
        files_raw = repo_data["files"]
        source_license = repo_data["detected_license"]
        commit_sha = repo_data.get("commit_sha", "")
        branch = repo_data.get("default_branch", "")
        repo_tag = repo_data.get("repo_tag", "")

        if not files_raw:
            yield {"type": "error", "msg": "No valid text source files found in repository."}
            return

        # ── 3. Apply ignore rules ─────────────────────────────────────────────
        yield {"type": "progress", "msg": "Applying .gitignore and .gitreverseignore exclusion rules..."}
        ignore_rules = await asyncio.to_thread(build_ignore_rules, files_raw)
        files = await asyncio.to_thread(ignore_rules.filter_files, files_raw)
        ignored_count = len(files_raw) - len(files)
        if ignored_count > 0:
            yield {"type": "progress", "msg": f"  Excluded {ignored_count} files ({len(files)} remaining)"}

        # ── 4. Secret scanner ─────────────────────────────────────────────────
        yield {"type": "progress", "msg": "Scanning for accidentally committed secrets (local-only)..."}
        secret_findings = await asyncio.to_thread(scan_files, files)
        if secret_findings:
            yield {"type": "progress", "msg": format_findings_summary(secret_findings)}
            yield {"type": "secrets", "findings": secret_findings}
        else:
            yield {"type": "progress", "msg": "  No potential secrets detected."}

        # ── 5. Codebase analysis ──────────────────────────────────────────────
        total_files = len(files)
        yield {"type": "progress", "msg": f"Analyzing {total_files} files for languages, manifests, and entrypoints..."}
        yield {"type": "progress_pct", "done": 0, "total": total_files}

        # Progress callback — synchronous, called inside to_thread
        progress_results: Dict[str, Any] = {}

        def do_analysis():
            def on_progress(done, total):
                progress_results["done"] = done
                progress_results["total"] = total

            return CodebaseAnalyzer.analyze(
                files,
                primary_lang=repo_data["primary_language"],
                progress_callback=on_progress,
            )

        analysis_res = await asyncio.to_thread(do_analysis)
        yield {"type": "progress_pct", "done": total_files, "total": total_files}

        languages = analysis_res["detected_languages"]
        frameworks = analysis_res["detected_frameworks"]
        arch_pattern = analysis_res["architecture_pattern"]
        dependency_details = analysis_res.get("dependency_details", [])

        # ── 6. Create SQLite session ──────────────────────────────────────────
        api_key = await asyncio.to_thread(SecretsManager.get_api_key)
        config = await asyncio.to_thread(SecretsManager.load_config)
        db_mgr = DatabaseManager()
        configured_model = config.get("model_id", "gpt-4o")

        session_rec = await asyncio.to_thread(
            db_mgr.create_session,
            repo_url,
            full_repo_name,
            languages[0] if languages else "Unknown",
            len(files),
            source_license,
            configured_model,
            commit_sha,
            branch,
            repo_tag,
            len([f for f in secret_findings if f.get("severity") == "high"]),
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
            "stars": repo_data.get("stars", 0),
        }
        yield {"type": "meta", "data": meta_payload}

        # ── 7. LLM stream ─────────────────────────────────────────────────────
        yield {"type": "progress", "msg": f"Generating {prompt_type} via LLM stream..."}
        api_key = await asyncio.to_thread(SecretsManager.get_api_key)
        config = await asyncio.to_thread(SecretsManager.load_config)

        if not api_key:
            fallback = (
                f"# System Prompt — Recreating {full_repo_name}\n\n"
                f"## 1. Architecture Overview\n"
                f"- Repository: {full_repo_name}\n"
                f"- Primary Language: {languages[0] if languages else 'Unknown'}\n"
                f"- Frameworks: {', '.join(frameworks) or 'None detected'}\n"
                f"- Architecture Pattern: {arch_pattern}\n"
                f"- Commit: {commit_sha or 'N/A'} ({branch or 'default'})\n\n"
                f"## 2. Detected Dependencies\n"
                + "\n".join(f"- {d['name']} {d.get('version','')}" for d in dependency_details[:20])
                + f"\n\n## 3. Responsible Use & License Attribution\n"
                f"- Source License: {source_license}\n"
                f"- Generated by: Git Reverse Intelligence System\n"
            )
            yield {"type": "token", "text": "\n[Notice: No LLM API Key configured. Using local analysis only.]\n"}
            yield {"type": "token", "text": fallback}
            await asyncio.to_thread(
                db_mgr.update_session_prompt, session_rec.id, fallback, "complete"
            )
            yield {"type": "done", "session_id": session_rec.id, "prompt": fallback}
            return

        llm_client = LLMClient(
            api_key=api_key,
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            model_id=config.get("model_id", "gpt-4o"),
        )

        file_list = list(files.keys())
        manifest_facts = [f["content"] for f in analysis_res["manifest_facts"]]
        full_chunks = []

        def on_token_usage(tokens: int):
            estimated = (tokens / 1000) * 0.01
            try:
                db_mgr.log_token_usage(
                    tokens=tokens,
                    estimated_cost_usd=estimated,
                    provider=config.get("provider_preset", ""),
                    model_id=config.get("model_id", ""),
                )
            except Exception:
                pass

        # Stream tokens synchronously in thread, yield them async
        token_queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def stream_in_thread():
            stream = llm_client.stream_recreation_prompt(
                repo_name=full_repo_name,
                repo_url=repo_url,
                source_license=source_license,
                languages=languages,
                frameworks=frameworks,
                arch_pattern=arch_pattern,
                manifest_facts=manifest_facts,
                file_list=file_list,
                ast_summaries=analysis_res.get("ast_summaries", []),
                prompt_type=prompt_type,
                token_callback=on_token_usage,
            )
            for tok in stream:
                full_chunks.append(tok)
                loop.call_soon_threadsafe(token_queue.put_nowait, tok)
            loop.call_soon_threadsafe(token_queue.put_nowait, None)  # sentinel

        task = asyncio.get_event_loop().run_in_executor(None, stream_in_thread)

        while True:
            tok = await token_queue.get()
            if tok is None:
                break
            yield {"type": "token", "text": tok}

        await task

        accumulated = "".join(full_chunks)
        ast_syms = analysis_res.get("ast_summaries", [])
        await asyncio.to_thread(
            db_mgr.update_session_prompt,
            session_rec.id,
            accumulated,
            "complete",
            len([f for f in secret_findings if f.get("severity") == "high"]),
            "\n".join(ast_syms),
        )
        yield {"type": "progress", "msg": "Repository analysis and prompt generation complete."}
        yield {"type": "done", "session_id": session_rec.id, "prompt": accumulated}

    except Exception as e:
        logger.error(traceback.format_exc())
        yield {"type": "error", "msg": f"Error during repository analysis: {str(e)}"}
