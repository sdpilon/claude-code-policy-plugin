import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT = ROOT / "skills" / "init" / "scripts" / "init_policy.py"
UPDATE = ROOT / "skills" / "update" / "scripts" / "update_policy.py"
sys.path.insert(0, str(ROOT / "scripts"))
import policy_manifest as pm  # noqa: E402

README = ".policy/README.md"


def run(script, cwd):
    return subprocess.run([sys.executable, str(script)], cwd=cwd, capture_output=True, text=True)


def tree_hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


class UpdateTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.assertEqual(run(INIT, self.repo).returncode, 0)
        self.manifest_path = self.repo / ".policy" / "manifest.json"

    def tearDown(self):
        self._tmp.cleanup()

    def manifest(self):
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def save(self, data):
        self.manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def readme(self):
        return self.repo / README


class UpdateTableTests(UpdateTestCase):
    def test_row1_stale_unmodified_file_is_overwritten_with_template(self):
        old = b"old shipped text\n"
        (self.repo / README).write_bytes(old)
        data = self.manifest()
        data["files"][README] = {"shipped_version": "0.1.0", "sha256": hashlib.sha256(old).hexdigest()}
        self.save(data)

        result = run(UPDATE, self.repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"updated: {README}", result.stdout)
        self.assertEqual(self.readme().read_bytes(), (ROOT / "templates" / "policy-readme.md").read_bytes())
        entry = self.manifest()["files"][README]
        self.assertEqual(entry["sha256"], pm.fingerprint(self.readme()))
        self.assertEqual(entry["shipped_version"], pm.plugin_version())

    def test_row2_customized_file_is_left_alone_and_diffed(self):
        self.readme().write_text(self.readme().read_text(encoding="utf-8") + "my local line\n", encoding="utf-8")
        before = self.readme().read_bytes()

        result = run(UPDATE, self.repo)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f"customized: {README}", result.stdout)
        self.assertIn("my local line", result.stdout)
        self.assertEqual(self.readme().read_bytes(), before)

    def test_row3_deleted_tracked_file_is_not_recreated(self):
        self.readme().unlink()

        result = run(UPDATE, self.repo)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f"missing: {README}", result.stdout)
        self.assertFalse(self.readme().exists())

    def test_row4_entry_without_template_is_kept_and_reported(self):
        (self.repo / ".policy" / "old-file.md").write_text("retired content\n", encoding="utf-8")
        data = self.manifest()
        data["files"][".policy/old-file.md"] = {
            "shipped_version": "0.1.0",
            "sha256": pm.fingerprint(self.repo / ".policy" / "old-file.md"),
        }
        self.save(data)

        result = run(UPDATE, self.repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no-longer-shipped: .policy/old-file.md", result.stdout)
        self.assertTrue((self.repo / ".policy" / "old-file.md").exists())

    def test_row5_new_shipped_file_absent_is_created_and_recorded(self):
        self.readme().unlink()
        data = self.manifest()
        del data["files"][README]
        self.save(data)

        result = run(UPDATE, self.repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.readme().exists())
        self.assertIn(README, self.manifest()["files"])

    def test_row5_new_shipped_file_present_is_user_owned(self):
        self.readme().write_text("my own readme\n", encoding="utf-8")
        data = self.manifest()
        del data["files"][README]
        self.save(data)

        result = run(UPDATE, self.repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"user-owned: {README}", result.stdout)
        self.assertEqual(self.readme().read_text(encoding="utf-8"), "my own readme\n")
        self.assertNotIn(README, self.manifest()["files"])


class UpdateEdgeTests(UpdateTestCase):
    def test_crlf_copy_of_unmodified_file_is_current_not_customized(self):
        text = self.readme().read_text(encoding="utf-8")
        self.readme().write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

        result = run(UPDATE, self.repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"current: {README}", result.stdout)
        self.assertNotIn("customized: ", result.stdout)

    def test_second_run_with_no_change_writes_nothing(self):
        self.assertEqual(run(UPDATE, self.repo).returncode, 0)
        before = tree_hashes(self.repo)

        result = run(UPDATE, self.repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(tree_hashes(self.repo), before)
        self.assertNotIn("updated:", result.stdout)

    def test_summary_names_customized_count_and_exits_1(self):
        self.readme().write_text("changed\n", encoding="utf-8")

        result = run(UPDATE, self.repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn("summary:", result.stdout)
        self.assertIn("1 customized", result.stdout)


if __name__ == "__main__":
    unittest.main()
