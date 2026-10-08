"""Review the blast radius of committed instruction changes."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import GitError, analyze
from .report import render_markdown, render_text


def main(argv=None):
    # Redirected Windows streams may otherwise use a legacy encoding.
    # Embedders can still supply StringIO or another text stream.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser(prog="instruction-impact", description=__doc__)
    parser.add_argument("--version", action="version", version=f"instruction-impact {__version__}")
    parser.add_argument("base", help="base commit/ref")
    parser.add_argument("head", nargs="?", default="HEAD", help="head commit/ref (default: HEAD)")
    parser.add_argument("--repo", default=".", help="Git repository path")
    parser.add_argument(
        "--profile",
        choices=("agents", "codex"),
        default="agents",
        help="instruction discovery rules (default: agents)",
    )
    parser.add_argument(
        "--fallback",
        action="append",
        default=[],
        metavar="NAME",
        help="Codex fallback filename; repeat in precedence order",
    )
    parser.add_argument(
        "--merge-base", action="store_true", help="compare the merge-base of base/head to head"
    )
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="create a new directory with report.json and report.md from the same analysis",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=20,
        help="file display cap; JSON always contains all files (default: 20)",
    )
    gate = parser.add_mutually_exclusive_group()
    gate.add_argument(
        "--fail-on-change",
        action="store_true",
        help="exit 1 for any instruction edit, including shadowed files",
    )
    gate.add_argument(
        "--fail-on-impact",
        action="store_true",
        help="exit 1 when an existing file's contributing instruction chain changes",
    )
    args = parser.parse_args(argv)
    if args.max_files < 0:
        parser.error("--max-files must be non-negative")
    try:
        report = analyze(
            args.repo,
            args.base,
            args.head,
            profile=args.profile,
            fallback=args.fallback,
            merge_base=args.merge_base,
        )
        if args.output_dir is not None:
            # Render before creating the directory; never replace an existing report bundle.
            json_report = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
            markdown_report = render_markdown(report, args.max_files)
            args.output_dir.mkdir(parents=True, exist_ok=False)
            (args.output_dir / "report.json").write_text(
                json_report, encoding="utf-8", newline="\n"
            )
            (args.output_dir / "report.md").write_text(
                markdown_report, encoding="utf-8", newline="\n"
            )
    except (GitError, OSError, ValueError) as error:
        print(f"instruction-impact: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=True))
    elif args.format == "markdown":
        print(render_markdown(report, args.max_files), end="")
    else:
        print(render_text(report, args.max_files), end="")
    return int(
        (args.fail_on_change and bool(report["instruction_changes"]))
        or (args.fail_on_impact and bool(report["summary"]["existing_files_affected"]))
    )
