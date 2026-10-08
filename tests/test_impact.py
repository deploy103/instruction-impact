import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from instruction_impact import GitError, analyze, core, main, render_markdown, render_text


class ImpactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args):
        return (
            subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.PIPE)
            .decode()
            .strip()
        )

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "--allow-empty", "-m", "fixture")
        return self.git("rev-parse", "HEAD")

    def fixture(self):
        self.write("AGENTS.md", "Run unit tests.\n")
        self.write("api/AGENTS.md", "Use transactions.\n")
        self.write("api/auth.py", "old\n")
        self.write("api/deep/model.py", "stable\n")
        self.write("apiary/sibling.py", "not in api\n")
        self.write("README.md", "hello\n")
        return self.commit()

    def test_nested_change_affects_unchanged_descendants_not_sibling_prefix(self):
        base = self.fixture()
        self.write("api/AGENTS.md", "Use transactions and audit logs.\n")
        self.write("api/auth.py", "new\n")
        report = analyze(self.repo, base, self.commit())
        self.assertEqual(
            report["summary"],
            {
                "instruction_changes": 1,
                "affected_files": 2,
                "unchanged_files_affected": 1,
                "existing_files_affected": 2,
            },
        )
        auth, model = report["affected_files"]
        self.assertEqual([auth["path"], model["path"]], ["api/auth.py", "api/deep/model.py"])
        self.assertTrue(auth["file_changed"])
        self.assertFalse(model["file_changed"])
        self.assertEqual([x["path"] for x in model["after"]], ["AGENTS.md", "api/AGENTS.md"])
        self.assertEqual(model["before"][0], model["after"][0])
        self.assertNotEqual(model["before"][1]["blob"], model["after"][1]["blob"])
        self.assertIn(
            "-Use transactions.\n+Use transactions and audit logs.",
            report["instruction_changes"][0]["diff"],
        )

    def test_root_change_still_reaches_files_with_nested_instructions(self):
        base = self.fixture()
        self.write("AGENTS.md", "Run integration tests.\n")
        report = analyze(self.repo, base, self.commit())
        self.assertEqual(
            [x["path"] for x in report["affected_files"]],
            ["README.md", "api/auth.py", "api/deep/model.py", "apiary/sibling.py"],
        )
        self.assertEqual(report["summary"]["unchanged_files_affected"], 4)

    def test_empty_instruction_addition_and_deletion_change_scope(self):
        base = self.fixture()
        self.write("api/deep/AGENTS.md", "")
        added = self.commit()
        report = analyze(self.repo, base, added)
        self.assertEqual([x["path"] for x in report["affected_files"]], ["api/deep/model.py"])
        self.assertIsNone(report["instruction_changes"][0]["before_blob"])
        self.assertEqual(len(report["affected_files"][0]["after"]), 3)
        (self.repo / "api/deep/AGENTS.md").unlink()
        report = analyze(self.repo, added, self.commit())
        self.assertIsNone(report["instruction_changes"][0]["after_blob"])
        self.assertEqual(len(report["affected_files"][0]["after"]), 2)

    def test_code_only_changes_do_not_count_as_instruction_changes(self):
        base = self.fixture()
        self.write("api/auth.py", "changed code\n")
        report = analyze(self.repo, base, self.commit())
        self.assertEqual(report["affected_files"], [])
        self.assertEqual(report["instruction_changes"], [])

    def test_file_moves_and_deletions_have_old_and_new_scope(self):
        base = self.fixture()
        (self.repo / "api/auth.py").rename(self.repo / "apiary/auth.py")
        report = analyze(self.repo, base, self.commit())
        deleted, added = report["affected_files"]
        self.assertEqual(
            (deleted["path"], deleted["status"], deleted["after"]),
            ("api/auth.py", "deleted", []),
        )
        self.assertEqual(
            (added["path"], added["status"], added["before"]),
            ("apiary/auth.py", "added", []),
        )
        self.assertEqual([x["path"] for x in deleted["before"]], ["AGENTS.md", "api/AGENTS.md"])
        self.assertEqual([x["path"] for x in added["after"]], ["AGENTS.md"])
        self.assertEqual(report["instruction_changes"], [])

    def test_reads_committed_snapshots_not_dirty_worktree_or_index(self):
        base = self.fixture()
        self.write("AGENTS.md", "committed\n")
        head = self.commit()
        expected = analyze(self.repo, base, head)
        self.write("AGENTS.md", "uncommitted\n")
        self.git("add", "AGENTS.md")
        self.assertEqual(analyze(self.repo, base, head), expected)
        self.assertEqual(analyze(self.repo / "api", base, head), expected)

    def test_arbitrary_filenames_and_fences_are_safe_in_reports(self):
        base = self.fixture()
        name = "api/한글\t`name\n.py"
        self.write(name, "code\n")
        base = self.commit()
        self.write("api/AGENTS.md", "````\n# injected heading\n````\n")
        report = analyze(self.repo, base, self.commit())
        self.assertIn(name, [x["path"] for x in report["affected_files"]])
        self.assertIn('\\t`name\\n.py"', render_text(report))
        self.assertIn("`````diff\n", render_markdown(report))
        self.assertEqual(json.loads(json.dumps(report)), report)

    def test_no_newline_diff_keeps_old_and_new_lines_separate(self):
        self.write("AGENTS.md", "old")
        base = self.commit()
        self.write("AGENTS.md", "new")
        report = analyze(self.repo, base, self.commit())
        self.assertIn("-old\n+new", report["instruction_changes"][0]["diff"])

    def test_instruction_mode_only_change_has_no_context_impact(self):
        base = self.fixture()
        self.git("update-index", "--chmod=+x", "AGENTS.md")
        self.git("commit", "-m", "mode only")
        report = analyze(self.repo, base, "HEAD")
        self.assertEqual(report["instruction_changes"], [])
        self.assertEqual(report["affected_files"], [])

    def test_symlink_instruction_rejected_without_reading_target(self):
        base = self.fixture()
        (self.repo / "AGENTS.md").unlink()
        os.symlink("/nonexistent/private-file", self.repo / "AGENTS.md")
        with self.assertRaisesRegex(GitError, "Unsupported instruction entry"):
            analyze(self.repo, base, self.commit())

    def test_cli_json_and_exit_codes(self):
        base = self.fixture()
        self.write("AGENTS.md", "new rules\n")
        head = self.commit()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(
                [
                    base,
                    head,
                    "--repo",
                    str(self.repo),
                    "--format",
                    "json",
                    "--fail-on-change",
                ]
            )
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["summary"]["affected_files"], 4)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([head, head, "--repo", str(self.repo), "--fail-on-change"]), 0)
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            self.assertEqual(main(["does-not-exist", "--repo", str(self.repo)]), 2)
        self.assertIn("instruction-impact:", errors.getvalue())

    def test_option_like_revision_is_not_interpreted_as_git_flag(self):
        self.fixture()
        with self.assertRaises(GitError):
            analyze(self.repo, "--help", "HEAD")

    def test_codex_override_replaces_only_same_directory_source(self):
        base = self.fixture()
        self.write("api/AGENTS.override.md", "Payments-specific review.\n")
        report = analyze(self.repo, base, self.commit(), profile="codex")
        self.assertEqual(
            [x["path"] for x in report["affected_files"]], ["api/auth.py", "api/deep/model.py"]
        )
        model = report["affected_files"][1]
        self.assertEqual(
            [x["path"] for x in model["after"]], ["AGENTS.md", "api/AGENTS.override.md"]
        )
        self.assertEqual(
            [(x["path"], x["kind"]) for x in model["causes"]],
            [("api/AGENTS.md", "removed"), ("api/AGENTS.override.md", "added")],
        )
        self.assertEqual(
            report["instruction_changes"][0]["affected_files"], ["api/auth.py", "api/deep/model.py"]
        )

    def test_codex_blank_override_blocks_regular_but_not_parent(self):
        base = self.fixture()
        self.write("api/AGENTS.override.md", " \n\t\u2003")
        head = self.commit()
        report = analyze(self.repo, base, head, profile="codex")
        self.assertEqual(report["instruction_changes"][0]["after_state"], "empty")
        self.assertEqual(len(report["instruction_changes"][0]["affected_files"]), 2)
        self.assertEqual([x["path"] for x in report["affected_files"][0]["after"]], ["AGENTS.md"])
        (self.repo / "api/AGENTS.override.md").unlink()
        restored = analyze(self.repo, head, self.commit(), profile="codex")
        self.assertEqual(
            [x["path"] for x in restored["affected_files"][0]["after"]],
            ["AGENTS.md", "api/AGENTS.md"],
        )

    def test_codex_shadowed_edit_is_visible_but_has_no_impact(self):
        self.fixture()
        self.write("api/AGENTS.override.md", "Override\n")
        base = self.commit()
        self.write("api/AGENTS.md", "Changed but shadowed\n")
        head = self.commit()
        report = analyze(self.repo, base, head, profile="codex")
        self.assertEqual(report["affected_files"], [])
        edit = report["instruction_changes"][0]
        self.assertEqual(
            (edit["before_state"], edit["after_state"], edit["affected_files"]),
            ("shadowed", "shadowed", []),
        )
        with contextlib.redirect_stdout(io.StringIO()):
            args = [base, head, "--repo", str(self.repo), "--profile", "codex"]
            self.assertEqual(main([*args, "--fail-on-change"]), 1)
            self.assertEqual(main([*args, "--fail-on-impact"]), 0)

    def test_agents_profile_does_not_treat_override_as_instruction(self):
        base = self.fixture()
        self.write("api/AGENTS.override.md", "Override\n")
        report = analyze(self.repo, base, self.commit())
        self.assertEqual(report["instruction_changes"], [])
        self.assertEqual([x["path"] for x in report["affected_files"]], ["api/AGENTS.override.md"])

    def test_fallback_order_and_empty_primary_blocking(self):
        self.write("TEAM.md", "Team guidance\n")
        self.write("OTHER.md", "Other guidance\n")
        self.write("code.py", "unchanged\n")
        base = self.commit()
        self.write("TEAM.md", "Updated team guidance\n")
        head = self.commit()
        report = analyze(
            self.repo, base, head, profile="codex", fallback=("TEAM.md", "OTHER.md", "TEAM.md")
        )
        self.assertEqual(
            report["instruction_names"], ["AGENTS.override.md", "AGENTS.md", "TEAM.md", "OTHER.md"]
        )
        self.assertEqual([x["path"] for x in report["affected_files"][0]["after"]], ["TEAM.md"])
        self.write("AGENTS.md", "")
        report = analyze(
            self.repo, head, self.commit(), profile="codex", fallback=("TEAM.md", "OTHER.md")
        )
        self.assertEqual(report["affected_files"][0]["after"], [])
        self.assertEqual(report["instruction_changes"][0]["affected_files"], ["code.py"])

    def test_two_edits_attributed_without_double_counting_global_total(self):
        base = self.fixture()
        self.write("AGENTS.md", "Updated root\n")
        self.write("api/AGENTS.md", "Updated API\n")
        report = analyze(self.repo, base, self.commit())
        self.assertEqual(report["summary"]["affected_files"], 4)
        root, api = report["instruction_changes"]
        self.assertEqual(len(root["affected_files"]), 4)
        self.assertEqual(api["affected_files"], ["api/auth.py", "api/deep/model.py"])
        self.assertEqual(len(report["affected_files"][1]["causes"]), 2)

    def test_display_caps_do_not_truncate_analysis_or_json(self):
        base = self.fixture()
        self.write("AGENTS.md", "Updated root\n")
        head = self.commit()
        report = analyze(self.repo, base, head)
        text = render_text(report, max_files=1)
        self.assertIn('"README.md"', text)
        self.assertNotIn('"api/auth.py"', text)
        self.assertIn("3 more", text)
        self.assertIn("3 more", render_markdown(report, max_files=1))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main([base, head, "--repo", str(self.repo), "--max-files", "0", "--format", "json"])
        self.assertEqual(len(json.loads(output.getvalue())["affected_files"]), 4)

    def test_merge_base_ignores_unrelated_target_branch_changes(self):
        common = self.fixture()
        self.git("checkout", "-b", "feature")
        self.write("api/AGENTS.md", "Feature rules\n")
        feature = self.commit()
        self.git("checkout", "main")
        self.write("AGENTS.md", "New main rules\n")
        target = self.commit()
        report = analyze(self.repo, target, feature, merge_base=True)
        self.assertEqual(report["base"], common)
        self.assertEqual(
            [x["path"] for x in report["affected_files"]], ["api/auth.py", "api/deep/model.py"]
        )

    def test_only_instruction_blobs_are_read_and_shared_blobs_cached(self):
        base = self.fixture()
        self.write("api/AGENTS.md", "Updated\n")
        head = self.commit()
        with patch.object(core, "git", wraps=core.git) as calls:
            analyze(self.repo, base, head)
        reads = [call.args for call in calls.call_args_list if call.args[1] == "cat-file"]
        self.assertEqual(len(reads), 3)  # root, old API, new API; never source code
        self.assertEqual(len({args[-1] for args in reads}), 3)

    def test_invalid_fallbacks_fail_before_git_probes(self):
        for filename in ("", "..", "a/b.md", "a\\b.md", "bad\0name", "C:guide.md"):
            with self.subTest(filename=filename), patch.object(core, "git") as calls:
                with self.assertRaises(ValueError):
                    analyze(self.repo, "base", "head", profile="codex", fallback=(filename,))
                calls.assert_not_called()
        with self.assertRaises(ValueError):
            analyze(self.repo, "base", "head", fallback=("TEAM.md",))

    def test_added_file_does_not_trigger_existing_file_impact_gate(self):
        base = self.fixture()
        self.write("api/new.py", "new code\n")
        head = self.commit()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([base, head, "--repo", str(self.repo), "--fail-on-impact"]), 0)
        self.write("api/AGENTS.md", "Updated\n")
        head = self.commit()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([base, head, "--repo", str(self.repo), "--fail-on-impact"]), 1)

    def test_report_bundle_uses_one_analysis_and_survives_impact_gate(self):
        base = self.fixture()
        self.write("api/AGENTS.md", "Review changes in Korean: 검토하세요.\n")
        head = self.commit()
        destination = self.repo / "artifacts" / "review"
        stdout = io.StringIO()
        with patch("instruction_impact.cli.analyze", wraps=analyze) as calls:
            with contextlib.redirect_stdout(stdout):
                result = main(
                    [
                        base,
                        head,
                        "--repo",
                        str(self.repo),
                        "--output-dir",
                        str(destination),
                        "--format",
                        "json",
                        "--max-files",
                        "0",
                        "--fail-on-impact",
                    ]
                )
        calls.assert_called_once()
        self.assertEqual(result, 1)
        report = json.loads((destination / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report, json.loads(stdout.getvalue()))
        self.assertEqual(
            [item["path"] for item in report["affected_files"]],
            ["api/auth.py", "api/deep/model.py"],
        )
        markdown = (destination / "report.md").read_text(encoding="utf-8")
        self.assertEqual(markdown, render_markdown(report, 0))
        self.assertIn("검토하세요", markdown)
        self.assertNotIn('"api/auth.py"', markdown)

    def test_report_bundle_refuses_existing_directory_without_modifying_files(self):
        base = self.fixture()
        destination = self.repo / "review"
        destination.mkdir()
        (destination / "report.json").write_bytes(b"keep private report\n")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main([base, "--repo", str(self.repo), "--output-dir", str(destination)])
        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("instruction-impact:", stderr.getvalue())
        self.assertEqual((destination / "report.json").read_bytes(), b"keep private report\n")
        self.assertFalse((destination / "report.md").exists())

    def test_invalid_revision_does_not_create_report_bundle(self):
        self.fixture()
        destination = self.repo / "review"
        with contextlib.redirect_stderr(io.StringIO()):
            result = main(
                ["missing-ref", "--repo", str(self.repo), "--output-dir", str(destination)]
            )
        self.assertEqual(result, 2)
        self.assertFalse(destination.exists())

    def test_action_script_writes_outputs_with_defaults_and_ordered_fallbacks(self):
        project = Path(__file__).resolve().parents[1]
        # Execute the actual single Bash block, without a YAML runtime dependency.
        script = textwrap.dedent((project / "action.yml").read_text().split("      run: |\n", 1)[1])
        self.fixture()
        (self.repo / "api/AGENTS.md").unlink()
        self.write("api/TEAM GUIDE.md", "First fallback\n")
        self.write("api/--lower.md", "Lower priority\n")
        self.write("instruction_impact.py", "raise RuntimeError('target code executed')\n")
        base = self.commit()
        self.write("api/TEAM GUIDE.md", "Updated fallback\n")
        self.write("api/--lower.md", "Shadowed edit\n")
        head = self.commit()
        for profile, fallback, expected in (
            ("agents", "", []),
            ("codex", "\r\nTEAM GUIDE.md\r\n\r\n--lower.md", ["api/auth.py", "api/deep/model.py"]),
        ):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as runner:
                output = Path(runner) / "outputs"
                summary = Path(runner) / "summary"
                env = {
                    **os.environ,
                    "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
                    "GITHUB_ACTION_PATH": str(project),
                    "RUNNER_TEMP": runner,
                    "GITHUB_OUTPUT": str(output),
                    "GITHUB_STEP_SUMMARY": str(summary),
                    "INPUT_BASE": base,
                    "INPUT_HEAD": head,
                    "INPUT_REPOSITORY": str(self.repo),
                    "INPUT_PROFILE": profile,
                    "INPUT_FALLBACK": fallback,
                    "INPUT_MAX_FILES": "0",
                }
                subprocess.run(
                    ["bash", "-c", script], cwd=self.repo, env=env, check=True, capture_output=True
                )
                outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
                report = json.loads(Path(outputs["json-path"]).read_text())
                self.assertEqual([item["path"] for item in report["affected_files"]], expected)
                self.assertEqual(outputs["existing-files-affected"], str(len(expected)))
                markdown = Path(outputs["report-path"]).read_text()
                self.assertEqual(summary.read_text(), markdown)
                self.assertEqual(markdown, render_markdown(report, 0))
                if profile == "codex":
                    self.assertEqual(
                        report["instruction_names"],
                        ["AGENTS.override.md", "AGENTS.md", "TEAM GUIDE.md", "--lower.md"],
                    )
                    self.assertEqual(
                        report["affected_files"][0]["after"][-1]["path"], "api/TEAM GUIDE.md"
                    )

    def test_lossy_text_display_does_not_hide_byte_level_instruction_changes(self):
        self.fixture()
        instruction = self.repo / "api/AGENTS.md"
        instruction.write_bytes(b"Review \xff\n")
        base = self.commit()
        instruction.write_bytes(b"Review \xfe\n")
        report = analyze(self.repo, base, self.commit(), profile="codex")
        self.assertEqual(report["instruction_changes"][0]["diff"], "")
        self.assertEqual(
            [x["path"] for x in report["affected_files"]], ["api/auth.py", "api/deep/model.py"]
        )
        self.assertNotEqual(
            report["affected_files"][0]["before"], report["affected_files"][0]["after"]
        )

    def test_non_utf8_filenames_round_trip_through_json(self):
        self.fixture()
        raw = os.fsencode(self.repo) + b"/api/\xff.py"
        with open(raw, "wb") as file:
            file.write(b"unchanged\n")
        base = self.commit()
        self.write("api/AGENTS.md", "Updated\n")
        report = analyze(self.repo, base, self.commit())
        decoded = json.loads(json.dumps(report))
        paths = [os.fsencode(item["path"]) for item in decoded["affected_files"]]
        self.assertIn(b"api/\xff.py", paths)
        self.assertIn(r"\udcff.py", render_markdown(report))

    def test_sha256_repository_uses_full_object_ids(self):
        self.repo = self.repo / "sha256"
        self.repo.mkdir()
        self.git("init", "-b", "main", "--object-format=sha256")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        base = self.fixture()
        self.write("api/AGENTS.md", "Updated\n")
        report = analyze(self.repo, base, self.commit())
        self.assertEqual(len(report["base"]), 64)
        self.assertEqual(len(report["affected_files"][0]["after"][1]["blob"]), 64)
        self.assertEqual(
            [x["path"] for x in report["affected_files"]], ["api/auth.py", "api/deep/model.py"]
        )


if __name__ == "__main__":
    unittest.main()
