"""Reproduce an instruction-only change without modifying your repository."""

import argparse
import contextlib
import subprocess
import tempfile
from pathlib import Path

from instruction_impact import main


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument(
        "--scenario",
        choices=("nested", "override", "shadowed", "empty-override", "fallback"),
        default="nested",
    )
    parser.add_argument(
        "--write-repo", type=Path, help="keep the fixture in a NEW directory instead of deleting it"
    )
    args = parser.parse_args()
    if args.write_repo:
        args.write_repo.mkdir(parents=True, exist_ok=False)
        fixture = contextlib.nullcontext(str(args.write_repo.resolve()))
    else:
        fixture = tempfile.TemporaryDirectory(prefix="instruction-impact-demo-")
    with fixture as directory:
        repo = Path(directory)

        def git(*arguments):
            return (
                subprocess.check_output(
                    ["git", "-C", directory, *arguments],
                    stderr=subprocess.PIPE,
                )
                .decode()
                .strip()
            )

        def write(path, text):
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")

        git("init", "-b", "main")
        git("config", "user.name", "Demo")
        git("config", "user.email", "demo@example.invalid")
        git("config", "commit.gpgsign", "false")
        git("config", "core.autocrlf", "false")
        write("AGENTS.md", "Run unit tests.\n")
        instruction = "api/TEAM.md" if args.scenario == "fallback" else "api/AGENTS.md"
        write(instruction, "Use transactions.\n")
        if args.scenario == "shadowed":
            write("api/AGENTS.override.md", "Use service-specific tests.\n")
        write("api/auth.py", "# Authentication\n")
        write("api/deep/model.py", "# Data model\n")
        write("apiary/sibling.py", "# Unrelated sibling\n")
        git("add", ".")
        git("commit", "-m", "Initial guidance")
        base = git("rev-parse", "HEAD")
        if args.scenario == "override":
            write("api/AGENTS.override.md", "Use service-specific tests.\n")
        elif args.scenario == "empty-override":
            write("api/AGENTS.override.md", "")
        else:
            write(instruction, "Use transactions and audit logs.\n")
        git("add", ".")
        git("commit", "-m", "Change instruction selection or content")
        options = [] if args.scenario == "nested" else ["--profile", "codex"]
        if args.scenario == "fallback":
            options += ["--fallback", "TEAM.md"]
        return main([base, "HEAD", "--repo", directory, "--format", args.format, *options])


if __name__ == "__main__":
    raise SystemExit(run())
