import unittest
from pathlib import Path

from tests._cli import load, run, scratch

MIGRATE = "skills/migrate/scripts/migrate_rules.py"

SHARED = """# Security

## Secrets

**SEC-7**: Secrets MUST NOT be committed.
**SEC-8**: Secrets MUST be rotated within 90 days.

Rationale: a leaked secret is only as contained as how fast it is rotated.

## Access

**SEC-9**: Access MUST be least-privilege. <!-- tier: ci-checked; via: review job -->

Rationale: broad access multiplies blast radius.
"""


class MigrateRulesTests(unittest.TestCase):
    def setup_repo(self, d, text=SHARED):
        policy = Path(d) / ".policy"
        policy.mkdir()
        (policy / "security.md").write_text(text)
        return policy

    def test_each_obligation_becomes_one_rule_with_fresh_id(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            result = load(
                run(MIGRATE, "--source-dir", str(policy), "--dest-dir", str(policy / "rule"))[1]
            )
            self.assertEqual([m["new_id"] for m in result["migrated"]], [1, 2, 3])
            self.assertEqual(len(list((policy / "rule").glob("*.md"))), 3)

    def test_shared_rationale_is_flagged_not_duplicated(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            result = load(
                run(MIGRATE, "--source-dir", str(policy), "--dest-dir", str(policy / "rule"))[1]
            )
            shared = [m for m in result["migrated"] if m["shared_rationale_group"]]
            self.assertEqual(len(shared), 2)
            self.assertEqual(
                shared[0]["shared_rationale_group"], shared[1]["shared_rationale_group"]
            )
            text = (policy / "rule" / "001.md").read_text()
            self.assertIn("TODO: see migration report", text)
            self.assertNotIn("leaked secret", text)

    def test_unshared_rationale_is_carried_over(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            run(MIGRATE, "--source-dir", str(policy), "--dest-dir", str(policy / "rule"))
            text = (policy / "rule" / "003.md").read_text()
            self.assertIn("Rationale: broad access multiplies blast radius.", text)

    def test_every_migrated_rule_needs_audience_review(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            result = load(
                run(MIGRATE, "--source-dir", str(policy), "--dest-dir", str(policy / "rule"))[1]
            )
            for n in (1, 2, 3):
                self.assertIn({"new_id": n, "reason": "audience not set"}, result["needs_review"])

    def test_dry_run_writes_nothing(self):
        with scratch() as d:
            policy = self.setup_repo(d)
            result = load(
                run(
                    MIGRATE,
                    "--source-dir",
                    str(policy),
                    "--dest-dir",
                    str(policy / "rule"),
                    "--dry-run",
                )[1]
            )
            self.assertEqual(len(result["migrated"]), 3)
            self.assertFalse((policy / "rule").exists())

    def test_file_without_section_headings_adds_reason(self):
        with scratch() as d:
            policy = self.setup_repo(d, "**SEC-1**: Flat MUST hold.\n")
            result = load(
                run(MIGRATE, "--source-dir", str(policy), "--dest-dir", str(policy / "rule"))[1]
            )
            reasons = [r["reason"] for r in result["needs_review"]]
            self.assertIn(
                "could not determine section boundaries — check rationale manually", reasons
            )


if __name__ == "__main__":
    unittest.main()
