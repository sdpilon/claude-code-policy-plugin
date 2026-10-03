import unittest
from pathlib import Path

from tests._cli import load, run, scratch

STATUS = "skills/status/scripts/policy_status.py"

RULE = """---
title: "{title}"
created: 2026-10-02T00:00:00Z
modified: 2026-10-02T00:00:00Z
audience: [agent]
verification:
  method: ci-blocking
  via: "secret-scan job"
---

**{id}**: Rule {id} MUST hold.

Rationale: because.
"""


class PolicyStatusTests(unittest.TestCase):
    def repo(self, d):
        return Path(d) / ".policy"

    def test_rows_include_title_and_frontmatter_tier(self):
        with scratch() as d:
            rule = self.repo(d) / "rule" / "047.md"
            rule.parent.mkdir(parents=True)
            rule.write_text(RULE.format(title="No secrets in CI logs", id="047"))
            result = load(run(STATUS, d)[1])
            row = result["rules"][0]
            self.assertEqual(row["id"], 47)
            self.assertEqual(row["title"], "No secrets in CI logs")
            self.assertEqual(row["tier"], "ci-blocking")
            self.assertEqual(row["via"], "secret-scan job")

    def test_nested_and_flat_layouts_are_both_found(self):
        with scratch() as d:
            (self.repo(d) / "rule" / "ci").mkdir(parents=True)
            (self.repo(d) / "rule" / "ci" / "001.md").write_text(RULE.format(title="a", id="001"))
            (self.repo(d) / "rule" / "002.md").write_text(RULE.format(title="b", id="002"))
            ids = [r["id"] for r in load(run(STATUS, d)[1])["rules"]]
            self.assertEqual(ids, [1, 2])

    def test_old_format_files_directly_under_policy_are_ignored(self):
        with scratch() as d:
            (self.repo(d)).mkdir(parents=True)
            (self.repo(d) / "security.md").write_text("**SEC-7**: Old MUST hold.\n")
            self.assertEqual(load(run(STATUS, d)[1])["rules"], [])

    def test_unverified_rule_is_unclassified(self):
        with scratch() as d:
            rule = self.repo(d) / "rule" / "001.md"
            rule.parent.mkdir(parents=True)
            rule.write_text(
                "---\ntitle: x\ncreated: 2026-10-02\nmodified: 2026-10-02\naudience: [agent]\n---\n\n**001**: x MUST y.\n"
            )
            row = load(run(STATUS, d)[1])["rules"][0]
            self.assertEqual(row["tier"], "unclassified")

    def test_missing_audience_is_a_defect(self):
        with scratch() as d:
            rule = self.repo(d) / "rule" / "001.md"
            rule.parent.mkdir(parents=True)
            rule.write_text(
                "---\ntitle: x\ncreated: 2026-10-02\nmodified: 2026-10-02\n"
                'verification:\n  method: written-only\n  via: ""\n---\n\n**001**: x MUST y.\n'
            )
            row = load(run(STATUS, d)[1])["rules"][0]
            self.assertEqual(row["defect"], "audience missing")

    def test_gap_without_tombstone_is_reported_and_tombstone_covers_it(self):
        with scratch() as d:
            rule_dir = self.repo(d) / "rule"
            rule_dir.mkdir(parents=True)
            (rule_dir / "001.md").write_text(RULE.format(title="a", id="001"))
            (rule_dir / "003.md").write_text(RULE.format(title="c", id="003"))
            self.assertEqual(load(run(STATUS, d)[1])["gaps"], [2])
            retired = self.repo(d) / "retired"
            retired.mkdir()
            (retired / "002.md").write_text(
                "---\ntitle: b\nretired: 2026-10-02\nreason: gone\n---\n"
            )
            self.assertEqual(load(run(STATUS, d)[1])["gaps"], [])


if __name__ == "__main__":
    unittest.main()
