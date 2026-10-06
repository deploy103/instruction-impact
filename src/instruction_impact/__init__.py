"""Git-only, deterministic analysis of inherited AGENTS.md changes."""

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import PurePosixPath


class GitError(Exception):
    """A repository or revision could not be read."""


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", os.fspath(repo), *args],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise GitError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def resolve(repo, revision):
    return (
        git(repo, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}")
        .decode()
        .strip()
    )


def snapshot(repo, commit):
    entries = {}
    for record in git(repo, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not record:
            continue
        header, name = record.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split()
        path = name.decode("utf-8", errors="surrogateescape")
        if PurePosixPath(path).name == "AGENTS.md" and mode not in ("100644", "100755"):
            raise GitError(
                f"Unsupported AGENTS.md entry (symlink or submodule): {path!r}"
            )
        if kind == "blob":
            entries[path] = (mode, oid)
    return entries


def instruction_chain(path, entries):
    """Root-to-parent instruction sources; no natural-language interpretation."""
    parents = list(reversed(PurePosixPath(path).parent.parents)) + [
        PurePosixPath(path).parent
    ]
    chain = []
    for parent in parents:
        candidate = str(parent / "AGENTS.md")
        if candidate in entries:
            chain.append({"path": candidate, "blob": entries[candidate][1]})
    return chain


def analyze(repo, base, head):
    base_sha, head_sha = resolve(repo, base), resolve(repo, head)
    before, after = snapshot(repo, base_sha), snapshot(repo, head_sha)
    paths = sorted(before.keys() | after.keys())
    affected = []
    instructions = []
    for path in paths:
        if PurePosixPath(path).name == "AGENTS.md":
            old_oid = before[path][1] if path in before else None
            new_oid = after[path][1] if path in after else None
            if old_oid == new_oid:
                continue
            old = (
                git(repo, "cat-file", "blob", old_oid).decode("utf-8", errors="replace")
                if old_oid
                else ""
            )
            new = (
                git(repo, "cat-file", "blob", new_oid).decode("utf-8", errors="replace")
                if new_oid
                else ""
            )
            diff = "\n".join(
                difflib.unified_diff(
                    old.splitlines(),
                    new.splitlines(),
                    fromfile=f"base/{path}",
                    tofile=f"head/{path}",
                    lineterm="",
                )
            )
            instructions.append(
                {
                    "path": path,
                    "before_blob": old_oid,
                    "after_blob": new_oid,
                    "diff": diff,
                }
            )
            continue
        old_chain = instruction_chain(path, before) if path in before else []
        new_chain = instruction_chain(path, after) if path in after else []
        if old_chain == new_chain:
            continue
        status = (
            "added"
            if path not in before
            else "deleted"
            if path not in after
            else "existing"
        )
        affected.append(
            {
                "path": path,
                "status": status,
                "file_changed": before.get(path) != after.get(path),
                "before": old_chain,
                "after": new_chain,
            }
        )
    return {
        "schema_version": 1,
        "base": base_sha,
        "head": head_sha,
        "instruction_changes": instructions,
        "affected_files": affected,
        "summary": {
            "instruction_changes": len(instructions),
            "affected_files": len(affected),
            "unchanged_files_affected": sum(
                not item["file_changed"] for item in affected
            ),
        },
    }


def quoted(value):
    # JSON quoting keeps tabs/newlines and arbitrary filenames on one output line.
    return json.dumps(value, ensure_ascii=True)


def render_text(report):
    summary = report["summary"]
    lines = [
        f"Instruction impact: {report['base'][:12]} -> {report['head'][:12]}",
        (
            f"{summary['instruction_changes']} instruction change(s); "
            f"{summary['affected_files']} affected file(s); "
            f"{summary['unchanged_files_affected']} with unchanged file content/mode."
        ),
    ]
    for item in report["affected_files"]:
        state = (
            item["status"]
            if item["status"] != "existing"
            else "modified"
            if item["file_changed"]
            else "unchanged"
        )
        lines.append(f"  [{state}] {quoted(item['path'])}")
        for label in ("before", "after"):
            sources = " -> ".join(
                quoted(source["path"]) + "@" + source["blob"][:8]
                for source in item[label]
            )
            lines.append(f"    {label}: {sources or '(none)'}")
    return "\n".join(lines) + "\n"


def fenced(value, language=""):
    # Instructions are untrusted text; embedded fences must not escape the report.
    longest = max((len(match) for match in re.findall(r"`+", value)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{value.rstrip(chr(10))}\n{fence}\n"


def render_markdown(report):
    output = "# Instruction impact\n\n" + fenced(render_text(report), "text")
    for item in report["instruction_changes"]:
        output += "\n## Instruction source\n\n" + fenced(quoted(item["path"]), "text")
        output += "\n" + fenced(
            item["diff"] or "(source changed; no normalized text difference)", "diff"
        )
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="base commit/ref (use a merge-base for PRs)")
    parser.add_argument(
        "head", nargs="?", default="HEAD", help="head commit/ref (default: HEAD)"
    )
    parser.add_argument("--repo", default=".", help="Git repository path")
    parser.add_argument(
        "--format", choices=("text", "json", "markdown"), default="text"
    )
    parser.add_argument(
        "--fail-on-change",
        action="store_true",
        help="exit 1 when any AGENTS.md content/source changed",
    )
    args = parser.parse_args(argv)
    try:
        report = analyze(args.repo, args.base, args.head)
    except (GitError, OSError) as error:
        print(f"instruction-impact: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=True))
    elif args.format == "markdown":
        print(render_markdown(report), end="")
    else:
        print(render_text(report), end="")
    return int(args.fail_on_change and bool(report["instruction_changes"]))
