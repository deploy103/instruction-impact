import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from instruction_impact import GitError, analyze, main, render_markdown, render_text


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
            subprocess.check_output(
                ["git", "-C", str(self.repo), *args], stderr=subprocess.PIPE
            )
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
            },
        )
        auth, model = report["affected_files"]
        self.assertEqual(
            [auth["path"], model["path"]], ["api/auth.py", "api/deep/model.py"]
        )
        self.assertTrue(auth["file_changed"])
        self.assertFalse(model["file_changed"])
        self.assertEqual(
            [x["path"] for x in model["after"]], ["AGENTS.md", "api/AGENTS.md"]
        )
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
        self.assertEqual(
            [x["path"] for x in report["affected_files"]], ["api/deep/model.py"]
        )
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
        self.assertEqual(
            [x["path"] for x in deleted["before"]], ["AGENTS.md", "api/AGENTS.md"]
        )
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
        with self.assertRaisesRegex(GitError, "Unsupported AGENTS.md"):
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
            self.assertEqual(
                main([head, head, "--repo", str(self.repo), "--fail-on-change"]), 0
            )
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            self.assertEqual(main(["does-not-exist", "--repo", str(self.repo)]), 2)
        self.assertIn("instruction-impact:", errors.getvalue())

    def test_option_like_revision_is_not_interpreted_as_git_flag(self):
        self.fixture()
        with self.assertRaises(GitError):
            analyze(self.repo, "--help", "HEAD")


if __name__ == "__main__":
    unittest.main()
