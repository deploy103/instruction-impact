"""Public analysis and command-line entry points."""

from .cli import main
from .core import GitError, analyze
from .report import render_markdown, render_text

__all__ = ["GitError", "analyze", "main", "render_markdown", "render_text"]
