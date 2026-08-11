import datetime
import time
import requests
from typing import Generator, Optional, Dict, Any, List, Tuple
from openai import OpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError

SYSTEM_PROMPT_TEMPLATE = """You are Git Reverse — an elite AI systems architect.
Your task is to analyze the provided repository file manifest, structure, and facts, and generate a standardized, highly detailed AI "Recreation Prompt".

Target Output Structure:
1. # System Prompt — Recreating {repo_name}
2. ## 1. Architecture Overview & Stack
3. ## 2. Core Modules & Data Models
4. ## 3. Implementation Workflow & Key Algorithms
5. ## 4. Security & Error Handling Requirements
6. ## 5. Responsible Use & License Attribution

CRITICAL RESPONSIBLE USE REQUIREMENT:
Source License Detected: {source_license}
You MUST include a dedicated section on source license compliance and attribution.
Do not omit attribution or offer to strip license notices.
"""

RESPONSIBLE_USE_FOOTER = """

---
### Responsible Use & Attribution Notice
- **Analyzed Repository**: {repo_name} ({repo_url})
- **Detected Source License**: {source_license}
- **Generated Date**: {date_str}
- **Compliance Advisory**: Recreated prompt structures are derived from public codebase analysis for educational and reverse-engineering purposes. Ensure compliance with the original repository license.
"""

# Known free-tier model IDs across providers
KNOWN_FREE_MODELS = {
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "google/gemini-flash-1.5-exp:free",
    "google/gemma-3-27b-it:free",
    "deepseek/deepseek-r1:free",
    "deepseek/deepseek-chat:free",
    "qwen/qwen-2.5-coder-32b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free",
    "openchat/openchat-7b:free",
    "gryphe/mythomax-l2-13b:free",
    "nousresearch/nous-capybara-7b:free",
}

# §58 AI Assistant Modes — specialized system prompt templates for KB Chat Console
AI_MODES: dict = {
    "General": (
        "You are Git Reverse AI — an evidence-grounded technical assistant for repository intelligence.\n"
        "Analyze repository architectures, code structures, and dependency trees.\n"
        "Be concise, precise, and cite provided evidence explicitly (including file paths, symbol names, and exact line numbers) when applicable."
    ),
    "Explain": (
        "You are Git Reverse AI in EXPLAIN MODE — a patient and clear engineering educator.\n"
        "Explain repository concepts, initialization flows, and code logic as if the user is encountering this codebase for the first time.\n"
        "Use step-by-step breakdowns, clear analogies, and simple language. Define any technical terms and highlight key entrypoint symbols and line numbers."
    ),
    "Architect": (
        "You are Git Reverse AI in ARCHITECT MODE — an elite software systems architect.\n"
        "Focus on high-level system design: component boundaries, design patterns, data flow boundaries, scalability bottlenecks, "
        "modularity, IPC protocols, and engineering trade-offs. Evaluate how the repository modules interact and cite exact line numbers."
    ),
    "Developer": (
        "You are Git Reverse AI in DEVELOPER MODE — a senior hands-on software engineer.\n"
        "Focus on practical implementation detail: API contracts, data models, error handling, function signatures, line numbers, "
        "and concrete instructions on how to extend, modify, debug, or refactor specific modules in the codebase."
    ),
    "Documentation": (
        "You are Git Reverse AI in DOCUMENTATION MODE — a technical documentation specialist.\n"
        "Generate comprehensive, professional engineering documentation suitable for inclusion in a README, wiki, or technical specification.\n"
        "Use structured Markdown with headers, bulleted lists, comparative tables, and code snippets referencing exact symbol line numbers."
    ),
}

# §59 Prompt type system prompt templates
PROMPT_TYPE_TEMPLATES: dict = {
    "Clone Prompt": SYSTEM_PROMPT_TEMPLATE,  # Default recreation prompt
    "Architecture Prompt": """You are Git Reverse — an elite AI systems architect.
Generate a detailed ARCHITECTURE ANALYSIS prompt for {repo_name}.

Target Output Structure:
1. # Architecture Analysis — {repo_name}
2. ## System Design Overview
3. ## Component Boundaries & Responsibilities
4. ## Data Flow Diagram (textual)
5. ## Design Patterns Identified
6. ## Scalability & Trade-off Notes
7. ## Responsible Use & Attribution (License: {source_license})
""",
    "Migration Prompt": """You are Git Reverse — an expert migration architect.
Generate a MIGRATION GUIDE prompt for {repo_name}.

Target Output Structure:
1. # Migration Guide — {repo_name}
2. ## Current Stack Summary
3. ## Migration Targets (e.g., framework/language alternatives)
4. ## Step-by-Step Migration Roadmap
5. ## Risks & Compatibility Concerns
6. ## Testing & Validation Strategy
7. ## Attribution (License: {source_license})
""",
    "Documentation Prompt": """You are Git Reverse — a technical documentation specialist.
Generate comprehensive ENGINEERING DOCUMENTATION for {repo_name}.

Target Output Structure:
1. # Engineering Documentation — {repo_name}
2. ## Overview & Purpose
3. ## Getting Started
4. ## Architecture & Module Reference
5. ## API Reference
6. ## Configuration
7. ## Contributing
8. ## License & Attribution (License: {source_license})
""",
}

# Groq free models
GROQ_FREE_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "llama-guard-3-8b",
}


def detect_provider_from_key(api_key: str) -> Tuple[str, str]:
    """Detects LLM provider name and default base_url from API Key prefix."""
    key = api_key.strip()
    if key.startswith("sk-or-v1-"):
        return "OpenRouter", "https://openrouter.ai/api/v1"
    elif key.startswith("gsk_"):
        return "Groq", "https://api.groq.com/openai/v1"
    elif key.startswith("sk-0") or key.lower().startswith("ds-"):
        return "DeepSeek", "https://api.deepseek.com/v1"
    elif key.startswith("sk-"):
        return "OpenAI", "https://api.openai.com/v1"
    return "Custom", "https://api.openai.com/v1"


def estimate_token_count(text: str) -> int:
    """Accurately calculates or estimates token count for spending log precision."""
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        words = len(text.split())
        return max(1, words) if words > 0 else 0


def _is_model_free(model_id: str, provider: str) -> bool:
    """Returns True if the model appears to be on a free tier."""
    if model_id in KNOWN_FREE_MODELS:
        return True
    if provider == "Groq" and model_id in GROQ_FREE_MODELS:
        return True
    if ":free" in model_id.lower():
        return True
    return False


def fetch_provider_models(api_key: str, base_url: str, provider_name: str = "") -> List[Dict[str, Any]]:
    """Queries provider models endpoint. Returns list with display_name and is_free flag.
    Runs synchronously — MUST be called from a background thread."""
    target_key = api_key.strip() or "ollama"
    if not provider_name:
        provider_name, _ = detect_provider_from_key(target_key)

    try:
        # OpenRouter requires HTTP-Referer + X-Title even for model listing
        extra_headers = {}
        if "openrouter" in base_url.lower():
            extra_headers = {
                "HTTP-Referer": "https://github.com/git-reverse/desktop",
                "X-Title": "Git Reverse Desktop",
            }

        client = OpenAI(
            api_key=target_key,
            base_url=base_url.rstrip("/"),
            timeout=10.0,
            default_headers=extra_headers if extra_headers else None,
        )
        res = client.models.list()
        models_result: List[Dict[str, Any]] = []
        for item in res.data:
            model_id = item.id
            is_free = _is_model_free(model_id, provider_name)
            display_name = f"[FREE] {model_id}" if is_free else model_id
            models_result.append({
                "id": model_id,
                "display_name": display_name,
                "is_free": is_free,
            })
        # Free models sorted to top, then alphabetical
        models_result.sort(key=lambda x: (not x["is_free"], x["id"].lower()))
        return models_result

    except Exception:
        # Fallback preset models per provider
        if "openrouter" in base_url.lower():
            return [
                {"id": "meta-llama/llama-3.3-70b-instruct:free", "display_name": "[FREE] meta-llama/llama-3.3-70b-instruct:free", "is_free": True},
                {"id": "google/gemini-2.0-flash-exp:free", "display_name": "[FREE] google/gemini-2.0-flash-exp:free", "is_free": True},
                {"id": "deepseek/deepseek-r1:free", "display_name": "[FREE] deepseek/deepseek-r1:free", "is_free": True},
                {"id": "qwen/qwen-2.5-coder-32b-instruct:free", "display_name": "[FREE] qwen/qwen-2.5-coder-32b-instruct:free", "is_free": True},
                {"id": "openai/gpt-4o", "display_name": "openai/gpt-4o", "is_free": False},
                {"id": "anthropic/claude-3.5-sonnet", "display_name": "anthropic/claude-3.5-sonnet", "is_free": False},
            ]
        elif "groq" in base_url.lower():
            return [
                {"id": "llama-3.3-70b-versatile", "display_name": "[FREE] llama-3.3-70b-versatile", "is_free": True},
                {"id": "llama-3.1-8b-instant", "display_name": "[FREE] llama-3.1-8b-instant", "is_free": True},
                {"id": "mixtral-8x7b-32768", "display_name": "[FREE] mixtral-8x7b-32768", "is_free": True},
                {"id": "gemma2-9b-it", "display_name": "[FREE] gemma2-9b-it", "is_free": True},
            ]
        elif "deepseek" in base_url.lower():
            return [
                {"id": "deepseek-chat", "display_name": "deepseek-chat", "is_free": False},
                {"id": "deepseek-coder", "display_name": "deepseek-coder", "is_free": False},
                {"id": "deepseek-reasoner", "display_name": "deepseek-reasoner", "is_free": False},
            ]
        elif "localhost" in base_url.lower() or "ollama" in base_url.lower():
            return [
                {"id": "codellama", "display_name": "[FREE] codellama", "is_free": True},
                {"id": "llama3", "display_name": "[FREE] llama3", "is_free": True},
                {"id": "mistral", "display_name": "[FREE] mistral", "is_free": True},
            ]
        else:
            return [
                {"id": "gpt-4o", "display_name": "gpt-4o", "is_free": False},
                {"id": "gpt-4o-mini", "display_name": "gpt-4o-mini", "is_free": False},
                {"id": "gpt-3.5-turbo", "display_name": "gpt-3.5-turbo", "is_free": False},
            ]


class LLMClient:
    """Production OpenAI-compatible streaming LLM client with exponential backoff,
    multi-provider BYOK support, and mandatory attribution footers."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model_id: str = "gpt-4o"):
        self.api_key = (api_key or "ollama").strip()

        # Auto-correct mismatched base_url and model_id based on API Key prefix if mismatched
        if self.api_key and self.api_key != "ollama":
            detected_provider, auto_url = detect_provider_from_key(self.api_key)
            if detected_provider != "Custom" and auto_url and (not base_url or base_url == "https://api.openai.com/v1"):
                base_url = auto_url
            elif self.api_key.startswith("sk-or-v1-") and "openrouter" not in (base_url or "").lower():
                base_url = "https://openrouter.ai/api/v1"
            elif self.api_key.startswith("gsk_") and "groq" not in (base_url or "").lower():
                base_url = "https://api.groq.com/openai/v1"

        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        raw_model = (model_id or "").replace("[FREE] ", "").strip()

        # Auto-assign provider-compatible model if current model_id is empty or mismatched
        if "openrouter" in self.base_url.lower():
            self.model_id = raw_model if raw_model and raw_model != "gpt-4o" else "openrouter/auto"
        elif "groq" in self.base_url.lower():
            self.model_id = raw_model if raw_model and raw_model != "gpt-4o" else "llama-3.3-70b-versatile"
        elif "deepseek" in self.base_url.lower():
            self.model_id = raw_model if raw_model and raw_model != "gpt-4o" else "deepseek-chat"
        else:
            self.model_id = raw_model if raw_model else "gpt-4o"

        # ── Provider-specific required headers ────────────────────────────────
        extra_headers = {}
        if "openrouter" in self.base_url.lower() or self.api_key.startswith("sk-or-v1-"):
            extra_headers = {
                "HTTP-Referer": "https://github.com/git-reverse/desktop",
                "X-Title": "Git Reverse Desktop",
            }

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=120.0,
            default_headers=extra_headers if extra_headers else None,
        )

    def stream_recreation_prompt(
        self,
        repo_name: str,
        repo_url: str,
        source_license: str,
        languages: list,
        frameworks: list,
        arch_pattern: str,
        manifest_facts: list,
        file_list: list,
        ast_summaries: list = None,
        prompt_type: str = "Clone Prompt",
        token_callback=None,
    ) -> Generator[str, None, None]:
        """Streams recreation prompt tokens with exponential backoff retry (trd.md §7).

        Args:
            prompt_type: One of 'Clone Prompt', 'Architecture Prompt',
                         'Migration Prompt', 'Documentation Prompt' (§59).
            token_callback: Optional callable(tokens_used: int) for spending tracking (§64).
        """
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        ast_section = f"\nExtracted AST Symbols & Definitions:\n{chr(10).join(ast_summaries)}" if ast_summaries else ""
        user_content = f"""
Repository Details:
- Name: {repo_name}
- URL: {repo_url}
- Source License: {source_license}
- Primary Languages: {', '.join(languages)}
- Frameworks: {', '.join(frameworks) if frameworks else 'None detected'}
- Architecture Pattern: {arch_pattern}

Manifest Facts:
{chr(10).join(manifest_facts) if manifest_facts else 'None detected'}
{ast_section}

File Tree Sample ({len(file_list)} files total):
{chr(10).join(file_list[:40])}
"""
        # §59: select system template based on prompt type
        template = PROMPT_TYPE_TEMPLATES.get(prompt_type, SYSTEM_PROMPT_TEMPLATE)
        sys_prompt = template.format(repo_name=repo_name, source_license=source_license)

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content},
        ]

        max_retries = 3
        backoff = 2.0
        tokens_total = 0

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    stream=True,
                    temperature=0.2,
                    max_tokens=4096,
                )
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token_text = chunk.choices[0].delta.content
                        tokens_total += estimate_token_count(token_text)
                        yield token_text

                # §64 Token usage callback
                if token_callback:
                    token_callback(tokens_total)

                yield RESPONSIBLE_USE_FOOTER.format(
                    repo_name=repo_name,
                    repo_url=repo_url,
                    source_license=source_license,
                    date_str=date_str,
                )
                return

            except RateLimitError:
                if attempt < max_retries:
                    yield f"\n[Rate limit hit. Retrying in {backoff:.0f}s (attempt {attempt}/{max_retries})...]\n"
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    yield "\n\n[Error: Rate limit exceeded after all retries. Try a free model or wait before retrying.]"

            except APITimeoutError:
                yield (
                    f"\n\n[Read Timeout Error]\n"
                    f"The provider stream timed out while receiving output.\n"
                    f"• Cause: Provider network latency or slow model queue.\n"
                    f"• Fix: Click 'Ingest Repository' to retry, or switch to a fast model in Settings (e.g., meta-llama/llama-3.3-70b-instruct:free or google/gemini-2.0-flash-exp:free)."
                )
                return

            except APIConnectionError as e:
                yield f"\n\n[Connection error: {str(e)}\nCheck your internet connection and Base URL in Settings.]"
                return

            except APIError as e:
                status = getattr(e, 'status_code', None)
                err_str = str(e)
                if status == 402 or "402" in err_str:
                    yield (
                        f"\n\n[API Error (HTTP 402 — Insufficient Provider Credits)]\n"
                        f"• Account Balance: Your provider account has insufficient credits for model '{self.model_id}'.\n"
                        f"• Quick Solution: Open Settings and switch to a FREE-tier model, e.g.:\n"
                        f"    - meta-llama/llama-3.3-70b-instruct:free\n"
                        f"    - google/gemini-2.0-flash-exp:free\n"
                        f"    - deepseek/deepseek-r1:free\n"
                        f"• Or add credits at https://openrouter.ai/settings/credits"
                    )
                elif status == 401 or "401" in err_str:
                    key_configured = "Yes (Saved in Keyring)" if self.api_key else "No"
                    yield (
                        f"\n\n[API Error (HTTP 401 — Unauthorized / Invalid API Key)]\n"
                        f"• Base URL: {self.base_url}\n"
                        f"• Model ID: {self.model_id}\n"
                        f"• API Key Configured: {key_configured}\n\n"
                        f"Troubleshooting Instructions:\n"
                        f"1. Open Settings -> check Provider & API Key match:\n"
                        f"   - For OpenRouter ({self.base_url}): Key MUST start with 'sk-or-v1-'.\n"
                        f"   - For OpenAI: Switch Provider to 'OpenAI' (https://api.openai.com/v1) if using an OpenAI key ('sk-proj-...' or 'sk-...').\n"
                        f"   - For Groq: Switch Provider to 'Groq' if using 'gsk_...'.\n"
                        f"2. Ensure model ID '{self.model_id}' is available under your active provider."
                    )
                else:
                    yield f"\n\n[API Error (HTTP {status or '?'}): {e.message}\nVerify your API key and model ID in Settings.]"
                return

            except Exception as e:
                yield f"\n\n[Unexpected error: {str(e)}]"
                return

    def stream_chat(
        self,
        system_context: str,
        user_message: str,
        history: list,
        ai_mode: str = "General",
        token_callback=None,
    ) -> Generator[str, None, None]:
        """Streams a conversational KB chat response.

        Args:
            ai_mode: AI Assistant Mode from AI_MODES dict (§58).
                     One of 'General', 'Explain', 'Architect', 'Developer', 'Documentation'.
            token_callback: Optional callable(tokens_used: int) for token usage tracking (§64).
        """
        # §58: inject AI mode modifier into system context
        mode_addendum = AI_MODES.get(ai_mode, "")
        full_context = system_context + mode_addendum

        messages = [{"role": "system", "content": full_context}]
        for turn in history:
            messages.append(turn)
        messages.append({"role": "user", "content": user_message})

        tokens_total = 0
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                stream=True,
                temperature=0.3,
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token_text = chunk.choices[0].delta.content
                    tokens_total += estimate_token_count(token_text)
                    yield token_text

            if token_callback:
                token_callback(tokens_total)
        except Exception as e:
            yield f"\n[Chat error: {str(e)}]"

    def test_connection(self) -> Tuple[bool, str]:
        """Tests API key and model connectivity with a minimal completion request."""
        if not self.api_key:
            return False, "No API key configured."
        try:
            res = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            if res and res.choices:
                return True, f"Successfully connected to {self.model_id} via {self.base_url}"
            return False, "API responded, but returned empty output."
        except APIError as e:
            status = getattr(e, 'status_code', None)
            err_str = str(e)
            if status == 402 or "402" in err_str:
                return False, f"HTTP 402 Insufficient Credits: Your account balance is low for model '{self.model_id}'. Try a free-tier model (e.g. meta-llama/llama-3.3-70b-instruct:free)."
            if status == 401 or "401" in err_str:
                return False, f"HTTP 401 Unauthorized: Invalid API key or model '{self.model_id}' not accessible."
            return False, f"API Error (HTTP {status or '?'}): {e.message}"
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"
