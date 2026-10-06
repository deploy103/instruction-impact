"""Read committed trees and compare directory-scoped instruction sources."""

import difflib
import os
import subprocess
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


def snapshot(repo, commit, names):
    entries = {}
    for record in git(repo, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not record:
            continue
        header, name = record.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split()
        path = name.decode("utf-8", errors="surrogateescape")
        if PurePosixPath(path).name in names and mode not in ("100644", "100755"):
            raise GitError(f"Unsupported instruction entry (symlink or submodule): {path!r}")
        if kind == "blob":
            entries[path] = (mode, oid)
    return entries


def instruction_chain(path, sources):
    """Accumulate contributing sources without interpreting their prose."""
    parents = list(reversed(PurePosixPath(path).parent.parents)) + [PurePosixPath(path).parent]
    chain = []
    for parent in parents:
        source = sources.get(str(parent))
        if source:
            chain.append(source)
    return chain


def discover(entries, names, profile, blobs):
    """Select by filename first, then skip blank Codex content (no retry)."""
    candidates = {}
    for path in entries:
        if PurePosixPath(path).name in names:
            candidates.setdefault(str(PurePosixPath(path).parent), {})[PurePosixPath(path).name] = (
                path
            )
    sources, states = {}, {}
    for directory, choices in candidates.items():
        selected = next(choices[name] for name in names if name in choices)
        for path in choices.values():
            oid = entries[path][1]
            if path != selected:
                states[path] = "shadowed"
            elif profile == "codex" and not blobs[oid].decode("utf-8", errors="replace").strip():
                states[path] = "empty"
            else:
                states[path] = "selected"
                sources[directory] = {"path": path, "blob": oid}
    return sources, states


def source_changes(before, after):
    old = {source["path"]: source["blob"] for source in before}
    new = {source["path"]: source["blob"] for source in after}
    return [
        {
            "path": path,
            "kind": "added" if path not in old else "removed" if path not in new else "modified",
            "before_blob": old.get(path),
            "after_blob": new.get(path),
        }
        for path in sorted(old.keys() | new.keys())
        if old.get(path) != new.get(path)
    ]


def analyze(repo, base, head, *, profile="agents", fallback=(), merge_base=False):
    if profile not in ("agents", "codex"):
        raise ValueError(f"Unknown profile: {profile}")
    if fallback and profile != "codex":
        raise ValueError("Fallback filenames require --profile codex")
    for name in fallback:
        if not name or name in (".", "..") or any(char in name for char in ("/", "\\", "\0", ":")):
            raise ValueError("Fallback must be a portable filename, not a path")
    names = tuple(
        dict.fromkeys(
            ("AGENTS.override.md", "AGENTS.md", *fallback) if profile == "codex" else ("AGENTS.md",)
        )
    )
    base_sha, head_sha = resolve(repo, base), resolve(repo, head)
    if merge_base:
        base_sha = git(repo, "merge-base", base_sha, head_sha).decode().strip()
    before, after = snapshot(repo, base_sha, names), snapshot(repo, head_sha, names)
    # Only instruction blobs are loaded; each unique blob is read once.
    blobs = {}
    for entries in (before, after):
        for path, (_, oid) in entries.items():
            if PurePosixPath(path).name in names and oid not in blobs:
                blobs[oid] = git(repo, "cat-file", "blob", oid)
    old_sources, old_states = discover(before, names, profile, blobs)
    new_sources, new_states = discover(after, names, profile, blobs)
    old_chains, new_chains = {}, {}
    paths = sorted(before.keys() | after.keys())
    affected = []
    instructions = []
    for path in paths:
        if PurePosixPath(path).name in names:
            old_oid = before[path][1] if path in before else None
            new_oid = after[path][1] if path in after else None
            if old_oid == new_oid:
                continue
            old = blobs[old_oid].decode("utf-8", errors="replace") if old_oid else ""
            new = blobs[new_oid].decode("utf-8", errors="replace") if new_oid else ""
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
                    "kind": "added"
                    if old_oid is None
                    else "removed"
                    if new_oid is None
                    else "modified",
                    "before_state": old_states.get(path, "missing"),
                    "after_state": new_states.get(path, "missing"),
                    "diff": diff,
                }
            )
            continue
        directory = str(PurePosixPath(path).parent)
        if directory not in old_chains:
            old_chains[directory] = instruction_chain(path, old_sources)
            new_chains[directory] = instruction_chain(path, new_sources)
        old_chain = old_chains[directory] if path in before else []
        new_chain = new_chains[directory] if path in after else []
        if old_chain == new_chain:
            continue
        status = "added" if path not in before else "deleted" if path not in after else "existing"
        affected.append(
            {
                "path": path,
                "status": status,
                "file_changed": before.get(path) != after.get(path),
                "before": old_chain,
                "after": new_chain,
                "causes": source_changes(old_chain, new_chain),
            }
        )
    # Attribute selection changes to edits in the same directory, including a
    # blank override that blocks an unchanged regular file from contributing.
    impacts = {}
    for item in affected:
        directories = {str(PurePosixPath(cause["path"]).parent) for cause in item["causes"]}
        for directory in directories:
            impacts.setdefault(directory, []).append(item["path"])
    for instruction in instructions:
        contributes = any(
            instruction[state] in ("selected", "empty") for state in ("before_state", "after_state")
        )
        instruction["affected_files"] = (
            impacts.get(str(PurePosixPath(instruction["path"]).parent), []) if contributes else []
        )
    return {
        "schema_version": 2,
        "base": base_sha,
        "head": head_sha,
        "profile": profile,
        "instruction_names": list(names),
        "instruction_changes": instructions,
        "affected_files": affected,
        "summary": {
            "instruction_changes": len(instructions),
            "affected_files": len(affected),
            "unchanged_files_affected": sum(not item["file_changed"] for item in affected),
            "existing_files_affected": sum(item["status"] == "existing" for item in affected),
        },
    }
