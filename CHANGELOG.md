# Changelog

## 1.0.0 — Unreleased

- Add `--version` and a single source for CLI/API/distribution version metadata.
- Add Action `fail-on: none|change|impact`, `instruction-changes`, and `gate-triggered`. Reports, outputs, and summary survive review failures; execution errors do not masquerade as successful reports.
- Standardize CLI stdout and exported files as UTF-8/LF, including redirected Windows streams.
- Fix Markdown export when instruction diff headers contain non-UTF-8 Git path bytes; JSON retains the original identity.
- Exercise default, triggered, shadowed, and invalid Action policies; test I/O failure and legacy stdout encodings.
- Expand compatibility CI to Windows and macOS, retaining the Ubuntu Python matrix. Construct symlink and non-UTF-8 path entries without requiring filesystem support; separate the POSIX-only control-character filename test. Keep Action arguments compatible with macOS's Bash 3.2.
- Check wheel/sdist metadata with strict Twine validation, verify installed version agreement, rerun installed-wheel schema checks, and retain distribution artifacts without publishing them.
- Document stable compatibility, release acceptance, Python integration, Windows setup, and troubleshooting. Update artifact uploads to Node-24-era `actions/upload-artifact@v7`.

JSON schema version remains **2**, and default CLI discovery/Action report-only behavior are unchanged. This source version has not been published as a release or uploaded to PyPI.

## 0.3.0 — Unreleased

- Add `--output-dir` to save complete JSON and capped Markdown from one analysis, including when a review gate returns exit 1. Existing destinations are never overwritten; I/O failures return exit 2 and may leave partial new bundles.
- Generate GitHub Action artifacts in a single analysis instead of comparing the repository twice.
- Add Action `fallback` (ordered newline-separated basenames) and `max-files` inputs. Blank lines and CRLF input are supported; filenames are passed literally, not evaluated as shell code.
- Test paired export, overwrite refusal, failed revisions, and the actual Action Bash block with default and custom discovery, including import isolation from target code.
- Expand both READMEs with the real technology stack, processing architecture, project layout, integration examples, and explicit future-work boundaries.

JSON schema version remains **2**. Existing CLI defaults and Action outputs are unchanged. No package publication is implied by this development version.

## 0.2.0 — 2026-10-06

### Behavior

- Add explicit `agents` and `codex` discovery profiles. Codex mode selects overrides before regular files, supports ordered fallback names, and distinguishes selection from blank-content skipping.
- Add per-file source deltas and directory-selection attribution, including empty overrides that block an unchanged regular file.
- Separate instruction-edit gates from existing-file context-impact gates.
- Add merge-base comparisons and bounded human file lists; JSON remains complete.
- Read each unique instruction blob once and cache ancestor chains per directory.

### Integration and maintenance

- Add a read-only composite GitHub Action with Markdown/JSON outputs, a job summary, and an existing-file impact count. It does not execute target repository code.
- Add five reproducible demo scenarios, including optional retained Git fixtures.
- Define and validate the versioned JSON contract; expand real-repository regression and CI integration coverage.
- Replace the introductory README with worked review workflows, profile semantics, failure-policy choices, security boundaries, and substantive Korean documentation.

### Compatibility

JSON `schema_version` changes from 1 to **2**. New fields include profile/candidate names, source selection states, per-file causes, attributed paths, and existing-file totals. Existing CLI default remains the `agents` profile. Human output is intentionally reformatted and capped at 20 file entries by default; use JSON for parsing.

## 0.1.0 — 2026-10-06

Initial Git-snapshot prototype: `AGENTS.md` ancestor chains, text/JSON/Markdown output, an instruction-edit gate, a nested-scope demo, and 12 real-repository tests.
