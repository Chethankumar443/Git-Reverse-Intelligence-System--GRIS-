"""Tests for OpenRouterClient."""

from __future__ import annotations

import json
import pytest
from typing import Any

from git_reverse.ai.client import OpenRouterClient
from git_reverse.core.exceptions import LLMError


# Simple mock response lines
_MOCK_STREAM_LINES = [
    b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
    b'data: {"choices": [{"delta": {"content": " world"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}',
    b"data: [DONE]",
]


@pytest.mark.asyncio
async def test_stream_completion_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockResponse:
        def __init__(self) -> None:
            self.status_code = 200

        async def __aenter__(self) -> MockResponse:
            return self

        async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass

        async def aiter_lines(self) -> Any:
            for line in _MOCK_STREAM_LINES:
                yield line

    def mock_stream(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        return MockResponse()

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "stream", mock_stream)

    client = OpenRouterClient(api_key="mock_key")
    chunks = []
    prompt_tokens = 0
    completion_tokens = 0

    async for chunk, p_tokens, c_tokens in client.stream_completion(
        messages=[{"role": "user", "content": "hi"}]
    ):
        chunks.append(chunk)
        if p_tokens > 0:
            prompt_tokens = p_tokens
        if c_tokens > 0:
            completion_tokens = c_tokens

    assert "".join(chunks) == "Hello world"
    assert prompt_tokens == 10
    assert completion_tokens == 5


@pytest.mark.asyncio
async def test_stream_completion_missing_key() -> None:
    client = OpenRouterClient(api_key="")
    with pytest.raises(LLMError, match="API key is missing"):
        async for _ in client.stream_completion(messages=[]):
            pass
