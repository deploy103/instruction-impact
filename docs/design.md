# Analysis model and trust boundary

This document is the behavior contract for 0.2. It separates **instruction edits**, **selection**, and **file context transitions**. These are different facts; treating them as synonyms creates misleading CI results.

## Three questions, three answers

1. **What instruction files changed?** Compare candidate paths and Git blob IDs between trees. An ignored `AGENTS.md` edit still belongs in this inventory. Executable-bit-only changes do not.
2. **What contributes in each directory?** Apply the chosen discovery profile to each committed tree independently. In Codex mode, select the first existing regular file in precedence order; then omit blank text without retrying lower-priority filenames.
3. **What changed for each tracked path?** Accumulate contributing sources from root to parent directory. Compare ordered `(path, blob ID)` chains. A transition is not a conclusion that the agent will behave differently; it is evidence that instruction provenance differs.

### Empty overrides are not harmless

```text
Before: root/AGENTS.md → api/AGENTS.md
After:  root/AGENTS.md

Edit: add empty api/AGENTS.override.md
```

The new override contributes no text, but it wins filename selection and blocks `api/AGENTS.md`. The file-level cause is removal of `api/AGENTS.md` from the chain; the edit-level attribution points to the added override. Ancestor guidance stays intact.

Conversely, editing a regular file while a nonempty override exists leaves both chains unchanged. The edit inventory shows `shadowed → shadowed` and zero attributed transitions. This is why the two failure gates exist.

## Attribution and counting

`affected_files[].causes` contains literal changes to contributing source paths: added, removed, or modified blob IDs. Instruction edit attribution links an edit to transitions at its directory's source-selection boundary, provided the edited file was selected or selected-but-empty on at least one side. This handles an empty override blocking another source.

An unchanged source that becomes selected is present in file chains/causes even though it has no text edit and therefore no entry in `instruction_changes`. Attribution is a directory-selection explanation, **not a minimal causal proof** when several candidates in one directory are edited together.

If root and nested instructions change together, one file may appear in both edit-level impact lists. The global file total is deduplicated by path. Do not sum per-edit counts to compute the global total.

`existing_files_affected` counts paths present on both sides with different chains, regardless of their own content changes. `unchanged_files_affected` is the subset whose Git blob **and mode** are unchanged. Added/deleted paths have a chain transition to/from an empty chain, but never trigger `--fail-on-impact` alone. Renames are deletion plus addition; similarity is not inferred.

## Snapshot-only Git access

```text
resolve refs to commits
        ↓
read trees (NUL-delimited paths, mode, object ID)
        ↓
read unique candidate instruction blobs
        ↓
select per-directory sources independently in each tree
        ↓
cache ancestor chains per directory
        ↓
compare chains → attribute edits → render/report
```

No checkout, temporary worktree, index write, Git hook, package install, project test, or instruction command is needed for analysis. Revision strings are passed as arguments to `rev-parse --end-of-options`, not to a shell. Only instruction blobs are loaded; source file contents are compared by object identity. Each instruction blob is read once per analysis, even when it appears at multiple paths or in both snapshots.

For F tracked paths, U unique instruction blobs, and D distinct source directories, Git subprocess calls are bounded by a small fixed setup cost plus U, not one call per affected file. Ancestor-chain construction is cached per directory. Memory retains tree metadata, instruction contents, and the complete report; output caps are a presentation feature, not a repository-size or memory limit. There is no performance claim for unmeasured monorepos.

## Codex compatibility is bounded

The `codex` profile models **project filename selection and unbounded source inheritance**. It does not reconstruct a running Codex session. Each tracked path is evaluated as if guidance discovery walked to its parent directory, which is useful for scope auditing; Codex normally discovers from its current working directory at session startup.

References inspected on 2026-10-06:

- [Official discovery guide](https://developers.openai.com/codex/guides/agents-md).
- [`agents_md.rs`: selection, reading, and filename order](https://github.com/openai/codex/blob/main/codex-rs/core/src/agents_md.rs).
- [`agents_md_tests.rs`: overrides, fallbacks, truncation, and lossy decoding](https://github.com/openai/codex/blob/main/codex-rs/core/src/agents_md_tests.rs).

Selection happens **before** blank-content skipping in the implementation. Blank overrides do not restart selection. The general guide's “skips empty files” wording is not a promise to fall back within the same directory.

Known differences:

| Codex behavior | This auditor |
| --- | --- |
| Reads home-directory and environment-specific guidance | Repository commits only |
| Configurable root markers and session CWD | Git tree root and each file's parent |
| Configured fallback list | Explicit repeated `--fallback`; no config files read |
| Follows instruction symlinks subject to filesystem restrictions | Rejects candidate instruction symlinks, even if shadowed |
| Applies byte limits/truncation | Unbounded chain; does not claim exact prompt text |
| Natural-language precedence in the prompt | Preserves ordered sources; does not resolve contradictions |

Fallbacks must be portable basename strings; `/`, `\`, `:`, NUL, empty names, `.` and `..` are rejected rather than silently ignored. This is intentionally stricter than Codex on POSIX. Instruction bytes are decoded lossily; blank detection uses Python's Unicode whitespace predicate, which differs from Rust for a few control characters. This tool is not a byte-exact reimplementation of Codex.

## Reporting untrusted content

Paths are JSON-escaped in human reports. Markdown diff/content blocks use a fence longer than every backtick run in their input, so instruction text cannot close the block. Raw report JSON preserves full paths; callers must still escape values when rendering them elsewhere. Reports may contain private instructions or secrets. Generating an artifact or job summary is itself a disclosure decision.

Git remains an external executable with the local user's Git configuration and object database. The tool is not a sandbox for malicious Git implementations, hostile global Git settings, arbitrary resource exhaustion, or a compromised runner. The composite Action keeps target repository code off Python's import path and uses `python -P` to prevent current-directory imports; it does not install or execute target code.
