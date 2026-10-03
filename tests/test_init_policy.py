import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT = ROOT / "skills" / "init" / "scripts" / "init_policy.py"
ADD = ROOT / "skills" / "add" / "scripts" / "add_rule.py"
sys.path.insert(0, str(ROOT / "scripts"))
import policy_manifest as pm  # noqa: E402


def run(script, cwd, *args):
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def tree_hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


class InitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_fresh_init_creates_skeleton_and_manifest(self):
        result = run(INIT, self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        policy = self.repo / ".policy"
        self.assertTrue((policy / "rule").is_dir())
        self.assertTrue((policy / "retired").is_dir())
        self.assertTrue((policy / "README.md").is_file())
        manifest = json.loads((policy / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["format_version"], 1)
        self.assertEqual(manifest["plugin_version"], pm.plugin_version())
        entry = manifest["files"][".policy/README.md"]
        self.assertEqual(entry["sha256"], pm.fingerprint(policy / "README.md"))

    def test_init_then_add_creates_rule_001(self):
        self.assertEqual(run(INIT, self.repo).returncode, 0)
        result = run(
            ADD,
            self.repo,
            "--statement", "Commits MUST be signed.",
            "--title", "Signed commits",
            "--audience", "human,agent",
            "--verification-method", "written-only",
            "--verification-via", "review",
            "--rationale", "Attribution matters.",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.repo / ".policy" / "rule" / "001.md").is_file())

    def test_second_init_changes_nothing(self):
        self.assertEqual(run(INIT, self.repo).returncode, 0)
        before = tree_hashes(self.repo)
        result = run(INIT, self.repo)
        self.assertEqual(result.returncode, 0)
        self.assertIn("already initialized", result.stdout)
        self.assertEqual(tree_hashes(self.repo), before)

    def test_existing_readme_without_manifest_is_user_owned(self):
        (self.repo / ".policy").mkdir()
        readme = self.repo / ".policy" / "README.md"
        readme.write_text("my own notes\n", encoding="utf-8")
        result = run(INIT, self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("user-owned: .policy/README.md (not tracked)", result.stdout)
        self.assertEqual(readme.read_text(encoding="utf-8"), "my own notes\n")
        manifest = json.loads((self.repo / ".policy" / "manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn(".policy/README.md", manifest["files"])


if __name__ == "__main__":
    unittest.main()
