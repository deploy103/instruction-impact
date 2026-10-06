# instruction-impact

**An `AGENTS.md` edit can change the instructions for hundreds of files without changing a single line of code. Make that blast radius reviewable.**

[![Tests](https://github.com/deploy103/instruction-impact/actions/workflows/test.yml/badge.svg)](https://github.com/deploy103/instruction-impact/actions/workflows/test.yml)
[한국어 안내](README.ko.md) · [Research and related tools](docs/research.md) · MIT

`instruction-impact` compares the root-to-directory `AGENTS.md` instruction sources for every tracked file in two Git commits. It highlights **unchanged files with changed instruction context**, along with the before/after source chains and instruction text diffs.

- No API keys, LLMs, network calls, or runtime Python dependencies.
- Reads Git objects only: no checkout, repository code execution, or worktree changes.
- Text, JSON, and fenced Markdown reports for local review and CI.
- Nested scopes, added/deleted instructions, and file additions/deletions.

## Install

Requires **Python 3.10+ and Git 2.20+**. Install from GitHub (not published to PyPI):

```sh
pip install "git+https://github.com/deploy103/instruction-impact.git"
```

Or clone and install locally:

```sh
git clone https://github.com/deploy103/instruction-impact.git
cd instruction-impact
python -m pip install .
python examples/demo.py
```

## Use

Run inside the repository you want to review:

```sh
instruction-impact HEAD~1                   # compare to HEAD
instruction-impact main feature-branch
instruction-impact main HEAD --format json
instruction-impact main HEAD --format markdown > impact.md
instruction-impact main HEAD --fail-on-change
instruction-impact main HEAD --repo /path/to/repo
```

For a PR, compare **merge-base to head**, not necessarily the current tip of main:

```sh
BASE=$(git merge-base origin/main HEAD)
instruction-impact "$BASE" HEAD --format markdown
```

Both commits must be available locally. Shallow clones may require fetching additional history. Revision arguments resolve to commits; uncommitted or staged edits are intentionally ignored.

## Example

Given:

```text
AGENTS.md                 Run unit tests.
api/AGENTS.md             Use transactions.
api/auth.py
api/deep/model.py
apiary/sibling.py
```

Changing only `api/AGENTS.md` to “Use transactions and audit logs.” affects `api/auth.py` and `api/deep/model.py`, **not** `apiary/sibling.py`. The unchanged source files are visible even though a normal code diff only lists the instruction file.

The reproducible demo creates two commits in a temporary repository, analyzes them, then deletes the fixture:

```sh
python examples/demo.py
python examples/demo.py --format json
python examples/demo.py --format markdown
```

Example text output (object IDs omitted here):

```text
1 instruction change(s); 2 affected file(s); 2 with unchanged file content/mode.
  [unchanged] "api/auth.py"
    before: "AGENTS.md"@… -> "api/AGENTS.md"@…
    after: "AGENTS.md"@… -> "api/AGENTS.md"@…
  [unchanged] "api/deep/model.py"
    before: "AGENTS.md"@… -> "api/AGENTS.md"@…
    after: "AGENTS.md"@… -> "api/AGENTS.md"@…
```

## Precise scope and limitations

This is a **source-scope change detector**, not a simulation of an agent's behavior or a security verdict.

- Only tracked files named exactly `AGENTS.md` are instruction sources. Root-to-parent sources accumulate; nested instructions do not erase parent sources. Conflicts are not interpreted.
- `AGENTS.md` files themselves appear under `instruction_changes`, not `affected_files`. Other tracked blob entries, including ordinary symlinks, are analyzed by their repository path. Submodule contents are not traversed.
- `AGENTS.override.md`, `CLAUDE.md`, custom fallback filenames, home-directory guidance, includes, agent settings, and token/truncation limits are **not modeled**. The report is not a claim about the exact prompt Codex or another agent receives.
- Instruction symlinks are rejected with exit 2 rather than followed or misread as text.
- Instruction content is compared by Git blob ID. Mode-only changes to instruction files do not change context. Source files compare both mode and blob ID.
- Added/deleted files with instructions have a context transition to/from an empty chain. Renames are deliberately reported as deletion plus addition, not guessed. Files changing content but keeping the same chain are omitted.
- Empty instruction sources still count. Text diffs normalize line endings and omit end-of-file newline markers; the blob IDs remain authoritative for byte-level changes. Non-UTF-8 instruction text uses replacement characters for display. Filenames are JSON-escaped in reports.
- Markdown source text is fenced, not interpreted. Reports can contain sensitive instruction content: review before publishing. No instruction command is executed.
- Output is deterministic for the same commits and includes resolved commit IDs. JSON has `schema_version: 1`, instruction changes, affected files, and summary counts.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Report generated; default even when context changes |
| 1 | With `--fail-on-change`, at least one instruction source/content changed |
| 2 | Invalid arguments, unavailable revision, unsupported instruction entry, or Git/OS error |

`--fail-on-change` also catches instruction edits in empty directories. Moving a source file between unchanged scopes is reported but does not trigger this instruction-edit gate.

## CI integration

Install a reviewed, pinned revision of this tool in your CI environment. Fetch both target commits, then:

```sh
instruction-impact "$BASE_SHA" "$HEAD_SHA" --format markdown > instruction-impact.md
```

The command only generates a report; it does not post comments or request write permissions. Store the file as your CI artifact. Add `--fail-on-change` if your policy requires explicit review of instruction edits. Avoid `pull_request_target` workflows that execute untrusted PR code.

## Development

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

The tests create real temporary Git repositories and check nested boundaries, unchanged affected files, root inheritance, empty instructions, file moves, dirty worktree isolation, symlink rejection, unusual filenames, report fencing, and CLI exit codes. See [CONTRIBUTING.md](CONTRIBUTING.md).
