# instruction-impact

### Review the instructions that changed—not just the code that changed.

[![Tests](https://github.com/deploy103/instruction-impact/actions/workflows/test.yml/badge.svg)](https://github.com/deploy103/instruction-impact/actions/workflows/test.yml)
**[한국어](README.ko.md)** · [Discovery model](docs/design.md) · [JSON contract](docs/json.md) · [Related work](docs/research.md)

A pull request changes `services/payments/AGENTS.md` from “run unit tests” to “skip tests for generated changes.” Git shows one Markdown edit. The review question is larger: **which files will now inherit that guidance, including files nobody touched?**

`instruction-impact` answers that question from two committed Git trees. It reports instruction edits, determines which sources contribute in each directory, and identifies every tracked file whose ordered instruction-source chain differs. It needs **Git and Python—not an AI model, API key, database, or session recorder.**

This is a review aid for teams maintaining agent guidance in nested repositories. It is not a linter for prose, an agent framework, or a claim that a particular agent actually read these files.

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

python examples/demo.py
```

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
```

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
      - uses: actions/upload-artifact@v4
        with:
          name: instruction-impact
          path: |
            ${{ steps.impact.outputs.report-path }}
            ${{ steps.impact.outputs.json-path }}
```

The Action also exposes `existing-files-affected` for your review policy. Its inputs are `base`, `head`, `repository` (default `.`), and `profile`; custom fallback lists are currently a CLI-only feature. Keep the tool revision trusted and pinned. Do not run untrusted PR code in a `pull_request_target` job. Reports can disclose instruction content—review the visibility of job summaries and artifacts before enabling them for a private project.

## What this report does not prove

- It **does not reconstruct a Codex prompt**. Home guidance, configured root markers, session CWD, byte truncation, agent settings, includes, and conversation instructions are outside the model.
- It **does not resolve prose conflicts or detect prompt injection**. A changed source is a review signal, not a security finding.
- It **does not follow instruction symlinks or traverse submodules**. Candidate symlinks are rejected rather than read incorrectly or followed outside the snapshot. Ordinary tracked symlinks are analyzed by path.
- It **does not guess renames**. They are deletion/addition transitions. Instruction candidates themselves belong to the edit inventory, not the source-file transition list.
- Its text diff is a **review aid, not an applyable patch**. Line endings are normalized; final-newline-only edits can have an empty diff. Full blob IDs remain authoritative.
- It reads complete tracked-tree metadata and candidate instructions into memory. Display caps are not resource limits. No large-monorepo speed claim is made without measurements.

These boundaries are deliberate. The useful promise is narrower: fixed commits and options produce deterministic, auditable evidence of instruction-source changes without running project code. The [design document](docs/design.md) explains selection, attribution, caching, and the trust boundary; the [JSON guide](docs/json.md) defines downstream integration.

## Development and maintenance

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python tests/check_schema.py
ruff check src tests examples
ruff format --check src tests examples
```

Regression tests use real temporary repositories, including divergent branches, nested prefix boundaries, empty overrides, shadowed edits, dirty indexes, unusual paths, and source changes with unchanged code. Schema checks exercise actual demo subprocess output. CI runs on Python 3.10, 3.12, and 3.14, and tests the composite Action's output paths and counts against an override fixture.

The implementation keeps Git/discovery in `core.py`, presentation in `report.py`, and exit policies in `cli.py`. Runtime dependencies remain zero; optional development tools are not needed by users. Contributions should include a counterexample to a plausible wrong implementation, not just another successful invocation. See [CONTRIBUTING.md](CONTRIBUTING.md).

Version 0.2 is an early, maintained scope auditor—not an established ecosystem standard. [CHANGELOG.md](CHANGELOG.md) records behavior and schema changes. Next work should be driven by real repositories: byte-budget modeling needs an explicit session model; staging/worktree support needs a separate snapshot contract. Neither is claimed today. MIT licensed; independent of OpenAI. Related-work research and program facts are recorded [separately](docs/research.md), without claims of unique invention or guaranteed grants.
