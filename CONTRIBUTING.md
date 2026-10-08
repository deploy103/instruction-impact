# Contributing

The project is intentionally narrow: make committed instruction-source changes understandable without running repository code. Bug reports, real repository examples, clearer compatibility documentation, and pointers to closer related work are welcome.

## Reproduce before changing

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python tests/check_schema.py
ruff check src tests examples
ruff format --check src tests examples
```

Python 3.10+ is supported. Git is required; tests use disposable repositories and `git init -b`. Use `ruff format src tests examples` to apply formatting. Development tooling is optional for users and must not become a runtime dependency.

CI covers Ubuntu on Python 3.10/3.12/3.14 and Windows/macOS on Python 3.12. The Action's Bash execution test requires Python 3.11+; three tests of POSIX-only byte/control-character filenames do not run on Windows. These platform exclusions must not hide general analysis or gate regressions. Write fixture text as UTF-8/LF and keep symlink tests in Git's index so they do not require filesystem privileges. See [release readiness](docs/release.md) for distribution and compatibility checks.

## A useful bug report

Include Python/Git versions, the exact command and profile, expected and actual affected paths, and a minimal two-commit fixture. `examples/demo.py --write-repo NEW_DIRECTORY` can help. Explain whether the discrepancy is an instruction edit, selection state, chain transition, or gate decision. These are separate contracts.

Do not upload private instructions, credentials, session logs, or a private repository's raw report. Redact content and preserve the scope structure. For sensitive vulnerabilities, use GitHub private vulnerability reporting if available, or contact the maintainer before publishing exploit details.

## Test a plausible mistake

A regression test should fail an implementation a competent developer might accidentally write:

| Mistake | Counterexample |
| --- | --- |
| Use a string prefix as a directory boundary | `api/file.py` vs `apiary/file.py` |
| Nested override erases all ancestors | Root + API regular + API override |
| Empty override retries the regular filename | Empty override plus nonempty regular guidance |
| Any instruction edit means actual impact | Changed shadowed regular file |
| Compare PR branch to target tip | Divergent branches with an unrelated root change |
| Display caps truncate analysis | Four affected paths, `--max-files 1`, full JSON |
| Add up per-instruction totals | Root and nested edits affect the same file |

Use temporary real Git repositories for discovery semantics. Mock only measurable I/O invariants, such as unique blob reads; do not mock away the behavior under test. Derive expected paths and counts independently of analysis helpers. For output changes, test both data correctness and escaping of arbitrary paths/instruction text.

## Ownership and compatibility

- `core.py` owns Git snapshots, discovery, chain comparison, attribution, and the report data model.
- `report.py` owns human presentation and untrusted-text escaping/fencing.
- `cli.py` owns arguments and exit policies.
- `action.yml` must keep untrusted target code out of Python's import path. Inputs must pass through environment variables/quoted arguments, never interpolation into shell source.

Update [design.md](docs/design.md) for semantic changes. Update [json.md](docs/json.md), the formal schema, and schema validation for report changes. Breaking changes require a schema version bump and changelog entry; human reports are not a parsing interface. Documentation commands and demo expectations are part of the deliverable.

Do not add new agent profiles based on name similarity alone. Cite the authoritative discovery implementation, distinguish selected files from contributing content, and document what cannot be represented by a Git snapshot. Byte limits, working-tree/index snapshots, and symlink resolution require explicit contracts, not silent approximation.
