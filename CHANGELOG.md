# Changelog

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
