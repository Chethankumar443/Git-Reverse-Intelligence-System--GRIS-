"""
Prompt templates for Git Reverse AI reasoning.
Defines system instructions for codebase Q&A and session summarization.
"""

from __future__ import annotations

# System directive: AI must teach architecture, design patterns, and explain tradeoffs.
_SYSTEM_PROMPT = """You are an elite Staff Software Engineer and Systems Architect.
You are explaining the architecture, design choices, tradeoffs, and internals of the repository.

Always adhere to these guidelines:
1. Local-First Mindset: Remember all processing occurs locally. Suggest local solutions first.
2. Architecture & Reasoning first: When asked to explain or change code, first teach the underlying design pattern or architecture of that component, explain the tradeoffs, and only then write the code.
3. High precision: Do not hallucinate files or classes. Use the context provided.
4. No shallow answers: Always provide clear, structural explanations with code block examples.
"""

# Context wrapper format
_USER_PROMPT_TEMPLATE = """Below is the compiled repository context:
---
{context_str}
---

User Query: {query}

Please answer the user query based on the above repository context and architecture.
"""

# Template for summarizing the session (written back to the sessions table)
_SUMMARIZATION_PROMPT = """Summarize the topic and decisions of this conversation session in a single, clear sentence (maximum 80 characters).
Do not output any prefix or markdown styling, just return the direct summary sentence.

Conversation:
{history_str}
"""
