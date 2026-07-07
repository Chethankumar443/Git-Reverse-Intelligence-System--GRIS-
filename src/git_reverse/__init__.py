"""
Git Reverse — Repository Intelligence Platform.

A local-first platform that transforms any Git repository into
structured knowledge: AST graphs, dependency maps, architecture
diagrams, and LLM-powered interactive analysis.
"""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("git-reverse")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
