import sys
import unittest
from pathlib import Path

from tests._cli import REPO, load, run, scratch

SYNC = "skills/sync/scripts/sync_status.py"
sys.path.insert(0, str(REPO / "skills" / "sync" / "scripts"))
import sync_status

RULE = """---
title: "{title}"
created: 2026-10-02T00:00:00Z
modified: 2026-10-02T00:00:00Z
audience: [{audience}]
verification:
  method: written-only
  via: ""
{wording}{synced}---

**{id}**: Rule {id} MUST hold.
"""


def rule_text(title, audience, rule_id, synced=""):
    audiences = [a.strip() for a in audience.split(",")]
    wording = "".join(f'  {a}: "Rule {rule_id} MUST hold for {a}."\n' for a in audiences)
    return RULE.format(
        title=title,
        audience=audience,
        id=f"{rule_id:03d}",
        wording=f"wording:\n{wording}",
        synced=synced,
    )


def write(d, rule_id, audience, synced=""):
    path = Path(d) / "rule" / f"{rule_id:03d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rule_text(f"t{rule_id}", audience, rule_id, synced))
    return path


class SyncStatusTests(unittest.TestCase):
    def test_missing_synced_hash_is_always_changed(self):
        with scratch() as d:
            write(d, 1, "agent")
            rows = load(run(SYNC, "--dir", str(Path(d) / "rule"))[1])
            self.assertTrue(rows[0]["changed"])
            self.assertIsNone(rows[0]["synced_hash"])

    def test_targets_follow_audience_exactly(self):
        with scratch() as d:
            write(d, 1, "human")
            write(d, 2, "agent")
            write(d, 3, "human, agent")
            rows = {r["id"]: r for r in load(run(SYNC, "--dir", str(Path(d) / "rule"))[1])}
            self.assertEqual(rows[1]["targets"], ["CONTRIBUTING.md"])
            self.assertEqual(rows[2]["targets"], ["CLAUDE.md", ".claude/rules/002.md"])
            self.assertEqual(
                rows[3]["targets"], ["CONTRIBUTING.md", "CLAUDE.md", ".claude/rules/003.md"]
            )

    def test_unchanged_after_synced_hash_is_written(self):
        """Writing synced_hash must not itself make the rule look changed (the self-reference bug)."""
        with scratch() as d:
            path = write(d, 1, "agent")
            digest = sync_status.content_hash(path.read_text())
            path.write_text(rule_text("t1", "agent", 1, f"synced_hash: {digest}\n"))
            row = load(run(SYNC, "--dir", str(Path(d) / "rule"))[1])[0]
            self.assertFalse(row["changed"])

    def test_content_change_after_sync_is_detected(self):
        with scratch() as d:
            path = write(d, 1, "agent")
            digest = sync_status.content_hash(path.read_text())
            path.write_text(rule_text("edited", "agent", 1, f"synced_hash: {digest}\n"))
            row = load(run(SYNC, "--dir", str(Path(d) / "rule"))[1])[0]
            self.assertTrue(row["changed"])

    def test_malformed_frontmatter_is_reported_as_changed_with_error(self):
        with scratch() as d:
            path = Path(d) / "rule" / "001.md"
            path.parent.mkdir(parents=True)
            path.write_text("no frontmatter at all\n")
            row = load(run(SYNC, "--dir", str(Path(d) / "rule"))[1])[0]
            self.assertTrue(row["changed"])
            self.assertIn("error", row)


if __name__ == "__main__":
    unittest.main()
