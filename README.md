# instruction-impact · Agent Instruction Change Intelligence

### Turn an instruction diff into an auditable, file-level impact report.

[![Tests](https://github.com/deploy103/instruction-impact/actions/workflows/test.yml/badge.svg)](https://github.com/deploy103/instruction-impact/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-blue)](pyproject.toml)

**[한국어](README.ko.md)** · [Discovery model](docs/design.md) · [JSON contract](docs/json.md) · [Troubleshooting](docs/troubleshooting.md) · [Release readiness](docs/release.md)

**Git-native analysis · Codex-aware discovery · Source attribution · CI review gates · Versioned JSON**

A pull request changes `services/payments/AGENTS.md` from “run unit tests” to “skip tests for generated changes.” Git shows one Markdown edit. The review question is larger: **which files will now inherit that guidance, including files nobody touched?**

`instruction-impact` answers that question from two committed Git trees. It reports instruction edits, determines which sources contribute in each directory, and identifies every tracked file whose ordered instruction-source chain differs. It needs **Git and Python—not an AI model, API key, database, or session recorder.**

This is a review aid for teams maintaining agent guidance in nested repositories. It is not a linter for prose, an agent framework, or a claim that a particular agent actually read these files.

## Built for instruction-aware code review

| Workflow | What you get |
| --- | --- |
| Review a monorepo guidance change | Exact descendant paths, including unchanged code, with root-to-directory provenance |
| Audit an override rollout | Selected, shadowed, and empty-source states—not just filename matches |
| Integrate with a PR pipeline | Merge-base comparison, Markdown job summary, complete JSON, and a count for your policy |
| Build downstream tooling | Schema-versioned data and full Git object IDs without an AI service |
| Retain review evidence | A paired JSON/Markdown bundle generated from one analysis |

## Technology stack

The architecture is a local analysis pipeline, not a hosted application. There is no frontend framework, database, queue, or model provider to deploy.

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Runtime | Python 3.10+, standard library | CLI, source selection, chain comparison, report rendering |
| Repository access | Git CLI (`rev-parse`, `merge-base`, `ls-tree`, `cat-file`) | Read committed metadata and instruction blobs without checkout |
| Interfaces | `argparse`, Python API, JSON, Markdown | Interactive use, automation, and review artifacts |
| Data contract | JSON Schema Draft 2020-12 | Validate schema-version-2 reports; no schema-library runtime dependency |
| CI integration | GitHub Actions composite action, Bash | Read-only PR reports and job summaries |
| Packaging | `pyproject.toml`, Hatchling | Installable CLI, wheel, and source distribution |
| Regression testing | `unittest`, real temporary Git repositories, `jsonschema` | Discovery semantics, CLI behavior, Action script, and report contracts |
| Code quality | Ruff | Linting and formatting |
| Compatibility CI | Ubuntu: Python 3.10 / 3.12 / 3.14; Windows and macOS: Python 3.12 | Regression tests, demo contracts, Action integration, packaging checks |

### Processing architecture

```text
 Base ref + Head ref + Discovery profile
                    |
                    v
     Resolve commits / optional merge-base
                    |
                    v
     Read Git trees + unique instruction blobs
                    |
                    v
     Select contributing sources per directory
                    |
                    v
     Compare ordered chains + attribute changes
                    |
          +---------+---------+
          |                   |
          v                   v
   Text / Markdown     Schema-versioned JSON
          |                   |
          +---------+---------+
                    v
       CLI gates / paired artifacts / CI summary
```

Both snapshots are resolved once per analysis. Blob reads and ancestor chains are cached; ordinary source-code contents are not loaded or executed. Full object IDs—not rendered text—determine identity. The human report can be capped without losing machine-readable evidence.

## What an ordinary diff misses

```text
repository/
├── AGENTS.md                         repository-wide guidance
├── services/
│   ├── payments/
│   │   ├── AGENTS.md                 payment-service guidance
│   │   ├── checkout.py               unchanged code
│   │   └── ledger/
│   │       └── reconcile.py          unchanged code
│   └── search/
│       └── query.py                  outside the changed scope
└── README.md
```

An edit to `services/payments/AGENTS.md` changes the source chain for both `checkout.py` and `reconcile.py`. It does not change the chain for `query.py`. Adding an override can be more subtle: in Codex mode, `AGENTS.override.md` replaces the regular instruction **in its directory**, not the root guidance.

The report preserves that distinction:

| Review question | Report evidence |
| --- | --- |
| What text or source presence changed? | Instruction inventory, blob IDs, normalized text diff |
| Was that file actually selected? | `selected`, `shadowed`, `empty`, or `missing` on each side |
| Which existing files have new instruction provenance? | Before/after source chains and per-file causes |
| Which affected files are absent from the code diff? | `unchanged_files_affected` and `[unchanged]` labels |
| Did several instruction edits affect the same file? | Per-edit attribution plus deduplicated global totals |

## Try it with a real Git fixture

Requires **Python 3.10+ and a modern Git installation**. The demo and tests use `git init -b`, available since Git 2.28. The GitHub Action requires Bash and Python 3.11+; the example provisions Python 3.12.

```sh
git clone https://github.com/deploy103/instruction-impact.git
cd instruction-impact
python -m venv .venv
. .venv/bin/activate
python -m pip install .

instruction-impact --version
python examples/demo.py
```

On Windows PowerShell, activation is `.venv\Scripts\Activate.ps1`. You can also run `.venv\Scripts\python -m pip install .` and `.venv\Scripts\python examples/demo.py` without activation. Prefer `--output-dir` to save UTF-8 artifacts without shell re-encoding.

The demo creates two commits in a temporary repository. Only the nested instruction changes; both source files stay unchanged. It cleans up the fixture afterward. Its text report includes:

```text
1 instruction change(s); 2 affected file(s); 2 with unchanged file content/mode.

INSTRUCTION EDITS
  [modified] "api/AGENTS.md" — 2 affected file(s)
    selection: selected -> selected

CONTEXT TRANSITIONS
  [unchanged] "api/auth.py"
    modified: "api/AGENTS.md"
    before: "AGENTS.md"@fa088e0d -> "api/AGENTS.md"@3de1b019
    after: "AGENTS.md"@fa088e0d -> "api/AGENTS.md"@07a33fe8
  [unchanged] "api/deep/model.py"
    modified: "api/AGENTS.md"
    before: "AGENTS.md"@fa088e0d -> "api/AGENTS.md"@3de1b019
    after: "AGENTS.md"@fa088e0d -> "api/AGENTS.md"@07a33fe8
```

These are the fixture's real instruction blob IDs; only its variable commit header is omitted. Want to inspect the commits yourself?

```sh
python examples/demo.py --scenario override --write-repo /tmp/my-instruction-fixture
git -C /tmp/my-instruction-fixture diff HEAD~1 HEAD
instruction-impact HEAD~1 HEAD --repo /tmp/my-instruction-fixture --profile codex
```

`--write-repo` requires a new directory and never overwrites an existing fixture. Five scenarios are executable, and CI checks their JSON against independently stated expected paths and a formal schema:

| Scenario | Command suffix | Expected result |
| --- | --- | --- |
| Nested text edit | `--scenario nested` | Two unchanged descendants affected; sibling excluded |
| New override | `--scenario override` | Two descendants switch from regular guidance to override |
| Shadowed regular edit | `--scenario shadowed` | One visible instruction edit, zero file transitions |
| Empty override | `--scenario empty-override` | Regular guidance disappears; root remains |
| Custom fallback | `--scenario fallback` | Two descendants inherit a changed `TEAM.md` |

## Use it on your repository

Install directly from GitHub if you do not need the examples. **There is no PyPI publication yet.** Pin a reviewed commit for automation; an unpinned Git URL follows a moving branch.

```sh
python -m pip install "git+https://github.com/deploy103/instruction-impact.git"

# Last committed change; HEAD is the default head argument.
instruction-impact HEAD~1

# A feature branch relative to its common ancestor with main.
instruction-impact origin/main HEAD --merge-base --profile codex

# Complete machine-readable data, even for large impact lists.
instruction-impact origin/main HEAD --merge-base --format json > impact.json

# Source-grouped review report with expandable before/after chains.
instruction-impact origin/main HEAD --merge-base --format markdown > impact.md

# Paired artifacts from one analysis; the destination must not already exist.
instruction-impact origin/main HEAD --merge-base --profile codex \
  --output-dir review-artifacts/pr-123 --fail-on-impact
```

`--output-dir` writes UTF-8 `report.json` and `report.md`, while `--format` still controls stdout. The bundle is saved before an instruction/impact gate returns exit 1, so a blocked review retains its evidence. Existing directories are refused with exit 2 rather than overwritten. Parent directories are created as needed. Writes are not transactional: an I/O failure can leave a partial new bundle; use a fresh destination after resolving the error. Reports may contain private instruction text.

Analysis never checks out either revision. Dirty worktrees and staged edits do not change the result; both revisions must already be in the local object database. Use `fetch-depth: 0` in CI, or explicitly fetch enough ancestry. `--merge-base` avoids misattributing unrelated target-branch changes to a PR. Comparing two tips without it is a deliberate tree-to-tree comparison.

Text lists at most 20 file transitions by default. Markdown also caps each instruction's file list at 20 and labels omissions. `--max-files 100` increases the display cap; `--max-files 0` keeps summaries and instruction edits. **JSON is never truncated by this option.**

### Choose the discovery profile deliberately

| Behavior | `--profile agents` (default) | `--profile codex` |
| --- | --- | --- |
| Candidate names | `AGENTS.md` | `AGENTS.override.md`, `AGENTS.md`, then explicit fallbacks |
| Files per directory | At most one `AGENTS.md` | First existing candidate only |
| Empty source | Retained as source presence | Selected but contributes no text; no retry |
| Parent guidance | Accumulates root-to-parent | Accumulates root-to-parent |
| Override file under agents profile | Ordinary tracked file | Instruction candidate |

For repositories configured with Codex fallback names:

```sh
instruction-impact main HEAD --profile codex \
  --fallback TEAM_GUIDE.md --fallback .agents.md
```

Fallback order matters. Names are deduplicated and must be portable basenames, not paths. The tool does not read your home-directory Codex configuration; the command records its explicit candidate names in JSON.

**An empty override is not equivalent to no override.** Codex selects filenames before skipping blank content. An empty `api/AGENTS.override.md` blocks `api/AGENTS.md` but leaves root instructions intact. This rule was checked against the upstream implementation, not inferred from the filename. See the [compatibility boundaries](docs/design.md#codex-compatibility-is-bounded).

### Separate “an instruction was edited” from “existing scope changed”

Both gates print the report before returning a nonzero result:

```sh
# Review every candidate edit, even if an override shadows it.
instruction-impact main HEAD --profile codex --fail-on-change

# Gate only when an existing file's contributing source chain changes.
instruction-impact main HEAD --profile codex --fail-on-impact
```

| Situation | `--fail-on-change` | `--fail-on-impact` |
| --- | --- | --- |
| Edit selected guidance covering existing files | 1 | 1 |
| Edit guidance shadowed by an unchanged override | 1 | 0 |
| Add guidance in a directory with no covered files | 1 | 0 |
| Add only a code file under unchanged guidance | 0 | 0 |
| Delete an override and reactivate regular guidance | 1 | 1, if existing descendants change |

The gates are mutually exclusive. Without a gate, successfully generated reports exit 0. Invalid arguments, missing revisions, unsupported instruction entries, and Git/OS errors exit 2. See `instruction-impact --help` for the full command surface.

### Use the Python API

```python
from instruction_impact import analyze, render_markdown

report = analyze("/path/to/repo", "origin/main", "HEAD", profile="codex", merge_base=True)
assert report["schema_version"] == 2
print(render_markdown(report, max_files=30))
```

`analyze` returns the same report contract as CLI JSON; it does not enforce a gate or write files. Callers choose policy from the summary and handle `GitError`, `OSError`, or invalid-option `ValueError`. Human formatting is not a parsing API. See the [compatibility policy](docs/release.md#compatibility-policy).

## GitHub Action: a report, not privileged PR automation

The repository includes a composite Action that reads Git objects, creates Markdown and JSON reports, and appends the Markdown to the job summary. It does not install or execute the target repository, post comments, or require write permissions. It compares **merge-base to head** automatically.

```yaml
name: Review instruction impact
on: pull_request
permissions:
  contents: read
jobs:
  impact:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'
      - uses: deploy103/instruction-impact@main # Replace main with a reviewed full commit SHA.
        id: impact
        with:
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}
          profile: codex
          fail-on: impact # Omit or use none for report-only behavior.
          max-files: '30'
          # Optional: match your repository's configured fallback precedence.
          fallback: |
            TEAM_GUIDE.md
            .agents.md
      - uses: actions/upload-artifact@v7
        if: ${{ always() && steps.impact.outputs.report-path != '' }}
        with:
          name: instruction-impact
          path: |
            ${{ steps.impact.outputs.report-path }}
            ${{ steps.impact.outputs.json-path }}
```

The Action generates both artifacts from a single analysis. `fail-on` defaults to `none`; `change` requires review for any candidate instruction edit, and `impact` requires review only when existing file scope changes. A triggered gate fails the step **after** saving reports, outputs, and the job summary. The `always()` upload condition above retains evidence without converting a failed review into a successful job.

Outputs are `report-path`, `json-path`, `existing-files-affected`, `instruction-changes`, and `gate-triggered` (`true`/`false`). Execution/configuration errors do not emit successful-report outputs. Other inputs are `base`, `head`, `repository` (default `.`), `profile`, `max-files` (default `20`), and `fallback` (one basename per line, in precedence order). Blank fallback lines are ignored; names are passed literally, including spaces. Nonempty fallbacks require the `codex` profile. Keep the tool revision trusted and pinned. Do not run untrusted PR code in a `pull_request_target` job. Reports can disclose instruction content—review the visibility of job summaries and artifacts before enabling them for a private project.

## What this report does not prove

- It **does not reconstruct a Codex prompt**. Home guidance, configured root markers, session CWD, byte truncation, agent settings, includes, and conversation instructions are outside the model.
- It **does not resolve prose conflicts or detect prompt injection**. A changed source is a review signal, not a security finding.
- It **does not follow instruction symlinks or traverse submodules**. Candidate symlinks are rejected rather than read incorrectly or followed outside the snapshot. Ordinary tracked symlinks are analyzed by path.
- It **does not guess renames**. They are deletion/addition transitions. Instruction candidates themselves belong to the edit inventory, not the source-file transition list.
- Its text diff is a **review aid, not an applyable patch**. Line endings are normalized; final-newline-only edits can have an empty diff. Full blob IDs remain authoritative.
- It reads complete tracked-tree metadata and candidate instructions into memory. Display caps are not resource limits. No large-monorepo speed claim is made without measurements.

These boundaries are deliberate. The useful promise is narrower: fixed commits and options produce deterministic, auditable evidence of instruction-source changes without running project code. The [design document](docs/design.md) explains selection, attribution, caching, and the trust boundary; the [JSON guide](docs/json.md) defines downstream integration.

## Development and maintenance

### Project layout

```text
src/instruction_impact/
  core.py                 Git snapshots, discovery, transitions, attribution
  report.py               Safe text and Markdown presentation
  cli.py                  Arguments, paired report export, exit policies
action.yml                Read-only GitHub Actions integration
tests/test_impact.py       Real-Git regressions and actual Action Bash execution
tests/check_schema.py     Demo output schema and independent path assertions
examples/demo.py          Five reproducible two-commit scenarios
docs/                     Design, JSON contract/schema, related-work research
.github/workflows/        Compatibility, lint, Action, distribution checks
```

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python tests/check_schema.py
ruff check src tests examples
ruff format --check src tests examples
```

Regression tests use real temporary repositories, including divergent branches, nested prefix boundaries, empty overrides, shadowed edits, dirty indexes, unusual paths, and source changes with unchanged code. Schema checks exercise actual demo subprocess output. CI covers Ubuntu on Python 3.10, 3.12, and 3.14, plus Windows/macOS on Python 3.12. The Action requires Python 3.11+; its integration tests verify outputs even when a review gate fails. POSIX-only path tests are explicitly separated from Windows; symlink rejection needs no filesystem symlink privileges.

The implementation keeps Git/discovery in `core.py`, presentation in `report.py`, and exit policies in `cli.py`. Runtime dependencies remain zero; optional development tools are not needed by users. Contributions should include a counterexample to a plausible wrong implementation, not just another successful invocation. See [CONTRIBUTING.md](CONTRIBUTING.md).

### Direction and non-goals

The source package targets **1.0.0**, with JSON schema version **2** unchanged. This is a bounded CLI/API/Action product, not an established ecosystem standard or a promise of exact agent behavior. [Release readiness](docs/release.md) defines acceptance and compatibility; [CHANGELOG.md](CHANGELOG.md) records changes. A source version is not a published release: no GitHub release or PyPI publication is implied.

Future work should be driven by real repositories: byte-budget modeling needs an explicit session model; staging/worktree support needs a separate snapshot contract; monorepo performance claims need reproducible measurements. These are directions, not shipped capabilities. New discovery profiles require authoritative semantics and counterexample fixtures.

MIT licensed; independent of OpenAI. Related-work research and program facts are recorded [separately](docs/research.md), without claims of unique invention or guaranteed grants.
