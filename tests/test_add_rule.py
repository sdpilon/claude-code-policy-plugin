import unittest
from pathlib import Path

from tests._cli import load, run, scratch

ADD = "skills/add/scripts/add_rule.py"


class AddRuleTests(unittest.TestCase):
    def common(self, cwd, **overrides):
        args = [
            "--statement",
            "Secrets MUST NOT appear in CI logs.",
            "--title",
            "No secrets in CI logs",
            "--audience",
            "agent",
            "--verification-method",
            "ci-blocking",
            "--verification-via",
            "secret-scan job",
            "--wording",
            "agent=Never print secrets to CI output.",
            "--policy-dir",
            str(Path(cwd) / ".policy"),
        ]
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
            self.assertFalse(
                (Path(d) / ".policy" / "rule").exists()
                and any((Path(d) / ".policy" / "rule").iterdir())
            )

    def test_invalid_verification_method_exits_2(self):
        with scratch() as d:
            code, _, _ = self.common(d, **{"--verification-method": "maybe"})
            self.assertEqual(code, 2)

    def test_statement_with_two_modal_verbs_exits_2_and_writes_nothing(self):
        with scratch() as d:
            code, _, err = self.common(d, **{"--statement": "Builds MUST pass and MAY skip lint."})
            self.assertEqual(code, 2)
            self.assertIn("modal", err)
            rule_dir = Path(d) / ".policy" / "rule"
            self.assertFalse(rule_dir.exists() and any(rule_dir.iterdir()))

    def test_sequential_adds_never_collide(self):
        with scratch() as d:
            first = load(self.common(d)[1])["id"]
            second = load(self.common(d, **{"--title": "Other"})[1])["id"]
            self.assertEqual((first, second), (1, 2))

    def test_subdirectory_option_keeps_id_and_places_file(self):
        with scratch() as d:
            code, _out, _ = run(
                ADD,
                "--statement",
                "Releases MUST be tagged.",
                "--title",
                "Tag releases",
                "--audience",
                "human",
                "--verification-method",
                "written-only",
                "--wording",
                "human=Releases MUST be tagged.",
                "--dir",
                "ci",
                "--policy-dir",
                str(Path(d) / ".policy"),
            )
            self.assertEqual(code, 0)
            self.assertTrue((Path(d) / ".policy" / "rule" / "ci" / "001.md").exists())


class AddRuleWordingTests(unittest.TestCase):
    def common(self, cwd, *wording, audience="human,agent"):
        args = [
            "--statement",
            "Secrets MUST NOT appear in CI logs.",
            "--title",
            "No secrets in CI logs",
            "--audience",
            audience,
            "--verification-method",
            "ci-blocking",
            "--verification-via",
            "secret-scan job",
            "--policy-dir",
            str(Path(cwd) / ".policy"),
        ]
        for item in wording:
            args += ["--wording", item]
        return run(ADD, *args)

    def test_each_audience_wording_is_written_to_frontmatter(self):
        with scratch() as d:
            code, _, err = self.common(
                d, "human=Secrets MUST NOT appear in CI logs.", "agent=Never print secrets."
            )
            self.assertEqual(code, 0, err)
            text = (Path(d) / ".policy" / "rule" / "001.md").read_text()
            self.assertIn("wording:\n  human: Secrets MUST NOT appear in CI logs.\n", text)
            self.assertIn("  agent: Never print secrets.\n", text)
            self.assertNotIn("synced_wording", text)
            self.assertNotIn("synced_hash", text)

    def test_wording_is_normalized_to_one_line(self):
        with scratch() as d:
            code, _, _ = self.common(d, "human=Secrets   MUST\tNOT\nappear.", "agent=Never print.")
            self.assertEqual(code, 0)
            text = (Path(d) / ".policy" / "rule" / "001.md").read_text()
            self.assertIn("  human: Secrets MUST NOT appear.\n", text)

    def test_missing_audience_wording_exits_2_and_writes_nothing(self):
        with scratch() as d:
            code, _, err = self.common(d, "human=Secrets MUST NOT appear.")
            self.assertEqual(code, 2)
            self.assertIn("agent", err)
            self.assertFalse((Path(d) / ".policy" / "rule").exists())

    def test_wording_for_audience_not_in_audience_exits_2(self):
        with scratch() as d:
            code, _, err = self.common(
                d, "human=Secrets MUST NOT appear.", "agent=Never print.", audience="human"
            )
            self.assertEqual(code, 2)
            self.assertIn("agent", err)

    def test_empty_wording_exits_2(self):
        with scratch() as d:
            code, _, err = self.common(d, "human=   ", "agent=Never print.")
            self.assertEqual(code, 2)
            self.assertIn("empty", err)

    def test_wording_without_equals_exits_2(self):
        with scratch() as d:
            code, _, _ = self.common(d, "human Secrets MUST NOT appear.", "agent=Never print.")
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
