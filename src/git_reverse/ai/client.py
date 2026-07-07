"""
OpenRouter API Client.

Manages async chat completion requests, handles streaming tokens, and performs
rate limit/error mitigation.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

from git_reverse.core.exceptions import LLMError
from git_reverse.core.logging import get_logger

log = get_logger(__name__)

_OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterClient:
    """Async API Client for OpenRouter."""

    def __init__(self, api_key: str, default_model: str = "openai/gpt-4o-mini") -> None:
        self._api_key = api_key
        self._default_model = default_model

    async def stream_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[tuple[str, int, int], None]:
        """
        Stream a completion from OpenRouter.

        Yields:
            A tuple of (chunk_text, prompt_tokens, completion_tokens).
            Usage statistics are usually populated on the final chunk.
        """
        if not self._api_key:
            raise LLMError("API key is missing or not configured.")

        selected_model = model or self._default_model
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Chethankumar443/Git-Reverse-CLI",
            "X-Title": "Git Reverse Platform",
        }
        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        log.info("ai_completion_requested", model=selected_model, temp=temperature)

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST", _OPENROUTER_API_URL, headers=headers, json=payload
                ) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        error_msg = error_body.decode("utf-8", errors="replace")
                        log.error("ai_api_error_response", status=response.status_code, body=error_msg)
                        raise LLMError(f"OpenRouter API error (HTTP {response.status_code}): {error_msg}")

                    prompt_tokens = 0
                    completion_tokens = 0

                    async for line_bytes in response.iter_lines():
                        if not line_bytes:
                            continue
                        line = line_bytes.decode("utf-8", errors="replace")
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    
                                    # Try to extract token metrics if available on chunks
                                    usage = data.get("usage")
                                    if usage:
                                        prompt_tokens = usage.get("prompt_tokens", 0)
                                        completion_tokens = usage.get("completion_tokens", 0)
                                        
                                    if content:
                                        yield content, prompt_tokens, completion_tokens
                            except (json.JSONDecodeError, KeyError) as exc:
                                # Non-blocking decode error (e.g., partial chunks)
                                log.debug("ai_chunk_decode_failed", error=str(exc))
                                continue

            except httpx.RequestError as exc:
                log.error("ai_request_failed", error=str(exc))
                raise LLMError(f"Connection to OpenRouter failed: {exc}") from exc
