import unittest
from pathlib import Path

from tests._cli import run, scratch

RETIRE = "skills/retire/scripts/retire_rule.py"
RULE = """---
title: "Require PR approval"
created: 2026-10-02T00:00:00Z
modified: 2026-10-02T00:00:00Z
audience: [human]
verification:
  method: ci-checked
  via: ""
---

**002**: PRs MUST have one approval.
"""


class RetireRuleTests(unittest.TestCase):
    def setup_repo(self, d):
        policy = Path(d) / ".policy"
        (policy / "rule" / "ci").mkdir(parents=True)
        (policy / "rule" / "ci" / "002.md").write_text(RULE)
        return policy

    def retire(self, policy, *extra):
        return run(RETIRE, "--id", "2", "--reason", "covered by branch protection",
                   "--rule-dir", str(policy / "rule"), "--retired-dir", str(policy / "retired"), *extra)

    def test_writes_tombstone_then_removes_rule(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            code, _, err = self.retire(policy)
            self.assertEqual(code, 0, err)
            tomb = (policy / "retired" / "002.md").read_text()
            self.assertIn("title: Require PR approval", tomb)
            self.assertIn("reason: covered by branch protection", tomb)
            self.assertFalse((policy / "rule" / "ci" / "002.md").exists())

    def test_missing_rule_exits_1_and_writes_nothing(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            code, _, _ = run(RETIRE, "--id", "9", "--reason", "x",
                             "--rule-dir", str(policy / "rule"), "--retired-dir", str(policy / "retired"))
            self.assertEqual(code, 1)
            self.assertFalse((policy / "retired").exists())

    def test_existing_tombstone_refuses(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            (policy / "retired").mkdir()
            (policy / "retired" / "002.md").write_text("---\ntitle: x\nretired: 2026-10-02\nreason: y\n---\n")
            code, _, _ = self.retire(policy)
            self.assertEqual(code, 1)
            self.assertTrue((policy / "rule" / "ci" / "002.md").exists())

    def test_empty_reason_exits_2(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            code, _, _ = run(RETIRE, "--id", "2", "--reason", "  ",
                             "--rule-dir", str(policy / "rule"), "--retired-dir", str(policy / "retired"))
            self.assertEqual(code, 2)

    def test_retired_id_is_not_reissued(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            self.retire(policy)
            from tests._cli import load
            code, out, _ = run("skills/add/scripts/add_rule.py", "--statement", "Tags MUST exist.",
                               "--title", "Tags", "--audience", "human", "--verification-method", "written-only",
                               "--policy-dir", str(policy))
            self.assertEqual(code, 0)
            self.assertEqual(load(out)["id"], 3)


if __name__ == "__main__":
    unittest.main()
