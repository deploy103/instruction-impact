# JSON report contract — schema version 2

The machine-readable contract is [report.schema.json](report.schema.json), using JSON Schema Draft 2020-12. CI validates actual demo subprocess output against it. CLI versions 0.2 and 0.3 emit version 2; consumers of the original version 1 must explicitly migrate. Human report formatting is not a stable parsing interface.

`--output-dir NEW_DIRECTORY` saves this same complete contract as UTF-8 `report.json`, together with `report.md` from the same analysis. Only Markdown respects `--max-files`; stdout still follows `--format`. The directory must be new. Artifacts are written before an enabled review gate returns exit 1; I/O errors return exit 2 and may leave partial files. The Action uses this export path internally.

## Top level

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `2` |
| `base`, `head` | Resolved commit object IDs; base is the ancestor when `--merge-base` is used |
| `profile` | `agents` or `codex` |
| `instruction_names` | Deduplicated candidate names in selection order |
| `instruction_changes` | Candidate source paths whose blob or presence changed, including shadowed edits |
| `affected_files` | Unique tracked non-candidate paths with different contributing source chains |
| `summary` | Inventory counts, unique transition count, unchanged-file and existing-file counts |

Object IDs are opaque lowercase hex strings (40 or 64 characters). Compare full IDs; shortened human-report IDs are only labels. Paths are root-relative POSIX Git paths, not filesystem-normalized display names. JSON escapes preserve non-UTF-8 filename bytes through Python surrogate escapes; consumers that cannot round-trip these paths should use Git object IDs rather than rewriting paths.

## Instruction edit

Each edit includes `path`, `kind` (`added`, `removed`, `modified`), nullable `before_blob`/`after_blob`, `diff`, `before_state`/`after_state`, and `affected_files` (a list of root-relative paths).

Selection states:

| State | Meaning |
| --- | --- |
| `missing` | Candidate path absent |
| `shadowed` | Higher-priority candidate in the same directory won |
| `empty` | Codex selected this candidate, but its decoded text is blank; lower-priority sources remain blocked |
| `selected` | Contributes a `(path, blob)` entry to descendant chains |

`diff` is a normalized-text review aid, **not an applyable Git patch**: line endings are normalized and final-newline-only changes may have an empty diff. Blob IDs preserve byte-level identity. An empty diff does not imply there was no edit.

## File transition

Each transition contains:

- `path`: tracked path, excluding candidate instruction files.
- `status`: `existing`, `added`, or `deleted` (not inferred rename status).
- `file_changed`: whether the path's `(Git mode, blob ID)` changed.
- `before`, `after`: ordered arrays of `{path, blob}` sources from root to parent.
- `causes`: source deltas with `path`, `kind` (`added`, `removed`, `modified`) and nullable before/after blob IDs.

The cause list is sorted by source path; the chains retain inheritance order. One unchanged file can have multiple causes. An empty override can cause removal of an unchanged regular instruction from the chain; attribution semantics are detailed in [design.md](design.md).

## CI policy examples

To require review only when existing file scope changes:

```python
import json

with open("impact.json") as file:
    report = json.load(file)
if report["schema_version"] != 2:
    raise RuntimeError("Unsupported instruction-impact report schema")
if report["summary"]["existing_files_affected"]:
    raise SystemExit("Instruction scope changed; review the Markdown report.")
```

To enumerate only untouched files that need instruction review:

```python
untouched = [
    item["path"] for item in report["affected_files"]
    if item["status"] == "existing" and not item["file_changed"]
]
```

`--max-files` never truncates JSON, including nested per-edit path lists. File totals are deduplicated; per-edit totals can overlap. There is no timestamp or absolute checkout path in the report, so fixed snapshots and options produce equal JSON regardless of where the checkout resides.
