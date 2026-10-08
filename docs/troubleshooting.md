# Troubleshooting

Start with `instruction-impact --version`, `python --version`, and `git --version`. Include these, the exact command/profile, and a minimal two-commit fixture in bug reports. Do not attach private instruction text or raw reports to public issues.

## Exit status is part of the interface

| Status | Meaning | Next step |
| --- | --- | --- |
| 0 | Analysis and requested export succeeded; no enabled review policy was triggered | Inspect the report; 0 without a policy does not mean no impact |
| 1 | An enabled instruction-edit or existing-file-impact policy requires review | Read the saved report; this is not an execution error |
| 2 | Invalid input, Git/OS error, unsupported instruction entry, or export failure | Read stderr; do not interpret missing evidence as no impact |

The Action mirrors this behavior through `fail-on: none`, `change`, or `impact`. With a triggered policy, report outputs and the job summary are generated before failure; `gate-triggered` is `true`. Syntax/Git/export errors do not produce successful-report outputs. Use `if: always()` with an output-path check on your artifact upload step so evidence survives a review gate.

## A revision or merge-base cannot be found

Both revisions and their common ancestry must be in the local object database. A shallow PR checkout often lacks them. Configure `actions/checkout` with `fetch-depth: 0`, or explicitly fetch the relevant refs and sufficient history. Confirm with:

```sh
git rev-parse --verify 'origin/main^{commit}'
git rev-parse --verify 'HEAD^{commit}'
git merge-base origin/main HEAD
```

Unrelated histories have no merge-base. Compare the two trees without `--merge-base` only if that is the review you intend. The tool does not fetch refs, create ancestry, or fall back silently.

## The output directory already exists

`--output-dir` deliberately refuses an existing directory, even an empty one or a symlink. Give each run a new destination. Do not delete previous evidence automatically. An I/O failure can leave a partial new bundle: fix permissions/disk capacity and use another destination; the bundle is not transactional.

## Instruction edits appear, but impact is zero

Check `before_state` and `after_state`. An override can shadow the edited regular file. An instruction in a directory with no covered tracked files can also have zero impact. `--fail-on-change` intentionally differs from `--fail-on-impact`; use the gate that matches your policy. New/deleted code paths alone do not trigger the existing-file gate.

## An empty override removed regular guidance

That is expected in the `codex` profile. Filename selection happens before blank-content skipping. An empty override blocks the same directory's regular/fallback files, without removing ancestors. Removing the override can reactivate regular guidance. See [the analysis contract](design.md).

## Fallback input was rejected

CLI fallbacks are repeated `--fallback NAME` arguments; the Action accepts one basename per line. Nonempty fallback input requires `codex`. Do not pass paths, an empty CLI name, `.` or `..`, or names containing `/`, `\`, `:`, or NUL. For a name beginning with a dash, use `--fallback=--guide.md`. The Action quotes values literally; it never runs commands embedded in names.

## An instruction symlink was rejected

This is the safety contract, not a missing target file error. Candidate symlinks are rejected even when shadowed. Store instruction content as a regular tracked file if you want it analyzed. Submodules are not traversed and their instruction contents are not claimed in results.

## Unicode text looks wrong in a terminal or redirected file

CLI output and paired artifacts use UTF-8; artifact files use LF line endings. A terminal or shell can still decode/re-encode a native command's stream differently. Prefer `--output-dir` when saving reports, especially in older Windows PowerShell. Read the resulting files explicitly as UTF-8. Non-UTF-8 Git path bytes are escaped in human output; schema-v2 JSON preserves them through surrogate escapes.

## A large report is expensive

`--max-files` caps human lists only. It does not cap JSON, instruction diffs, tracked-tree metadata, or memory use. Run on appropriately sized trusted infrastructure. This release has no quantified monorepo performance/SLA claim; include measured repository size and resource usage in a performance report rather than assuming display caps are resource limits.
