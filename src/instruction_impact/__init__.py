"""Public analysis and command-line entry points."""

__version__ = "1.0.0"

from .cli import main
from .core import GitError, analyze
from .report import render_markdown, render_text

__all__ = ["GitError", "__version__", "analyze", "main", "render_markdown", "render_text"]
