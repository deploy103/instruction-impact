# 1.0 release readiness and maintenance contract

The source package targets **1.0.0**. A package version in this repository is not proof of a published GitHub release or a PyPI upload. Publishing is a separate maintainer decision; there is no automatic publication workflow.

## Product boundary

The finished product is a local CLI, Python API, and read-only GitHub Action for **committed instruction-source impact review**. It is not a hosted service, prose linter, exact agent prompt simulator, or security certification. Worktree analysis and other agent profiles are not unfinished requirements for this product: they need separate contracts before being added.

## Acceptance criteria

Before publishing a release, verify all of these on its exact commit:

| Area | Required evidence |
| --- | --- |
| Analysis | Real-Git tests for nested boundaries, override selection, blank and shadowed instructions, attribution, merge-base, dirty worktree isolation, and object identity |
| Interfaces | Version command outside Git, CLI exit codes 0/1/2, complete schema-v2 JSON, capped human reports, paired export before review failure, refusal to overwrite, and I/O failure diagnostics |
| Encoding | UTF-8/LF export and redirected stdout; human escaping of non-UTF-8 Git path bytes without destroying JSON identity |
| CI policy | Actual composite Action tests for report-only and failed-gate outputs; Bash tests for invalid settings, ordered fallbacks, and target import isolation |
| Platforms | Ubuntu on Python 3.10/3.12/3.14; Windows and macOS on Python 3.12; POSIX-only filename tests explicitly separated |
| Distribution | Wheel and sdist build, strict Twine metadata check, no scratch artifacts, version agreement, and installed-wheel regressions/schema checks |
| Documentation | English and Korean usage, trust boundary, compatibility, troubleshooting, and contribution instructions match tested behavior |

The Action requires Bash and Python 3.11+ because `-P` keeps target code off Python's import path. The CLI and analysis API continue to support Python 3.10+. On Windows, three byte/control-character filename tests are inapplicable to its filesystem; symlink rejection is still tested by constructing a Git index entry, without requiring symlink privileges.

## Local release verification

Run from a clean checkout of the candidate:

```sh
python -m venv .venv
# POSIX activation; on Windows use .venv\Scripts\Activate.ps1.
. .venv/bin/activate
python -m pip install -e '.[dev]' build twine
python -m unittest discover -s tests -v
python tests/check_schema.py
ruff check src tests examples
ruff format --check src tests examples
git diff --check

python -m build
python -m twine check --strict dist/*
python -m pip install --force-reinstall dist/*.whl
python -I -c 'import importlib.metadata as m; import instruction_impact as i; assert m.version("instruction-impact") == i.__version__; print(i.__version__)'
python -m unittest discover -s tests -v
python tests/check_schema.py
instruction-impact --version
```

Use a fresh build directory for each candidate so old distributions are not mixed into the check. The CI `package` job also validates that `.amp/in` scratch files do not ship and stores the tested wheel/sdist as `instruction-impact-distributions`. Downloading that artifact does not publish it. Do not rebuild a different commit and label it as the verified candidate.

## Compatibility policy

- JSON schema version **2** remains the parsing interface in 1.0. Schema-breaking changes require an explicit schema-version bump and migration guide. Consumers must check `schema_version`.
- CLI arguments and default `agents` discovery remain compatible. New opt-in arguments can be added; removing arguments or changing selection/gate defaults requires a major package version.
- `analyze`, `render_text`, `render_markdown`, `GitError`, `main`, and `__version__` are the public Python exports. `core` and `report` helper functions are implementation details. `main` follows argparse conventions: argument errors, help, and version may raise `SystemExit`; normal analysis returns 0/1/2.
- Text and Markdown are human presentation, not stable parsing interfaces. Paths, selection states, counts, source identity, and exit policies are semantic contracts.
- Support CI covers the listed Python/OS combinations, not every Python, Git distribution, shell, or self-hosted runner. A Git supporting `rev-parse --end-of-options` is required; fixture tests also use Git 2.28+ `git init -b` and SHA-256 object support.

Version is defined once in `src/instruction_impact/__init__.py`; Hatchling reads it for distribution metadata and the CLI reads it for `--version`.

## Publication gate

Publishing a tag, GitHub release, or PyPI package changes shared state and needs maintainer authorization. Before that decision, review the exact CI run, release notes, package names/version, visibility of artifacts, and rollback limitations. Pin the Action to the reviewed full commit, not a moving branch. No upload token or credential belongs in the repository.
