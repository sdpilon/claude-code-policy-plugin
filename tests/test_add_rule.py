import unittest
from pathlib import Path

from tests._cli import load, run, scratch

ADD = "skills/add/scripts/add_rule.py"


class AddRuleTests(unittest.TestCase):
    def common(self, cwd, **overrides):
        args = ["--statement", "Secrets MUST NOT appear in CI logs.", "--title", "No secrets in CI logs",
                "--audience", "agent", "--verification-method", "ci-blocking",
                "--verification-via", "secret-scan job", "--policy-dir", str(Path(cwd) / ".policy")]
        for k, v in overrides.items():
            args[args.index(k) + 1] = v
        return run(ADD, *args)

    def test_successful_add_returns_id_and_path(self):
        with scratch() as d:
            code, out, err = self.common(d)
            self.assertEqual(code, 0, err)
            result = load(out)
            self.assertEqual(result["id"], 1)
            self.assertTrue(result["path"].endswith("001.md"))
            text = (Path(d) / ".policy" / "rule" / "001.md").read_text()
            self.assertIn("**001**: Secrets MUST NOT appear in CI logs.", text)
            self.assertIn("audience: [agent]", text)

    def test_missing_or_invalid_audience_exits_2_and_writes_nothing(self):
        with scratch() as d:
            code, _, _ = self.common(d, **{"--audience": "robot"})
            self.assertEqual(code, 2)
            self.assertFalse((Path(d) / ".policy" / "rule").exists() and any((Path(d) / ".policy" / "rule").iterdir()))

    def test_invalid_verification_method_exits_2(self):
        with scratch() as d:
            code, _, _ = self.common(d, **{"--verification-method": "maybe"})
            self.assertEqual(code, 2)

    def test_sequential_adds_never_collide(self):
        with scratch() as d:
            first = load(self.common(d)[1])["id"]
            second = load(self.common(d, **{"--title": "Other"})[1])["id"]
            self.assertEqual((first, second), (1, 2))

    def test_subdirectory_option_keeps_id_and_places_file(self):
        with scratch() as d:
            code, out, _ = run(ADD, "--statement", "Releases MUST be tagged.", "--title", "Tag releases",
                               "--audience", "human", "--verification-method", "written-only",
                               "--dir", "ci", "--policy-dir", str(Path(d) / ".policy"))
            self.assertEqual(code, 0)
            self.assertTrue((Path(d) / ".policy" / "rule" / "ci" / "001.md").exists())


if __name__ == "__main__":
    unittest.main()
