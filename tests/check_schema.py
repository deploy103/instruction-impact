"""Validate subprocess output and documented demo expectations independently."""

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parents[1]
schema = json.loads((root / "docs/report.schema.json").read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema)
for scenario in ("nested", "override", "shadowed", "empty-override", "fallback"):
    report = json.loads(
        subprocess.check_output(
            [
                sys.executable,
                str(root / "examples/demo.py"),
                "--scenario",
                scenario,
                "--format",
                "json",
            ]
        )
    )
    validator.validate(report)
    expected_files = [] if scenario == "shadowed" else ["api/auth.py", "api/deep/model.py"]
    assert [item["path"] for item in report["affected_files"]] == expected_files
    assert report["summary"] == {
        "instruction_changes": 1,
        "affected_files": len(expected_files),
        "unchanged_files_affected": len(expected_files),
        "existing_files_affected": len(expected_files),
    }
    assert report["instruction_changes"][0]["affected_files"] == expected_files
    print(f"{scenario}: JSON schema and independent expectations verified")
