"""Reproduce an instruction-only change without modifying your repository."""

import argparse
import subprocess
import tempfile
from pathlib import Path

from instruction_impact import main


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format", choices=("text", "json", "markdown"), default="text"
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="instruction-impact-demo-") as directory:
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
            target.write_text(text)

        git("init", "-b", "main")
        git("config", "user.name", "Demo")
        git("config", "user.email", "demo@example.invalid")
        git("config", "commit.gpgsign", "false")
        write("AGENTS.md", "Run unit tests.\n")
        write("api/AGENTS.md", "Use transactions.\n")
        write("api/auth.py", "# Authentication\n")
        write("api/deep/model.py", "# Data model\n")
        write("apiary/sibling.py", "# Unrelated sibling\n")
        git("add", ".")
        git("commit", "-m", "Initial guidance")
        base = git("rev-parse", "HEAD")
        write("api/AGENTS.md", "Use transactions and audit logs.\n")
        git("add", ".")
        git("commit", "-m", "Require audit logs")
        return main([base, "HEAD", "--repo", directory, "--format", args.format])


if __name__ == "__main__":
    raise SystemExit(run())
