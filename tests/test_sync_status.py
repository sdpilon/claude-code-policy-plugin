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


HUMAN = "Secrets MUST NOT appear in CI logs."
AGENT = "Never print secrets to CI output."


def write_rule(d, audience, wording, synced_wording, rule_id=1):
    """A rule file with explicit wording and synced_wording maps (no derived-doc checks here)."""
    lines = [
        "---",
        'title: "t"',
        "created: 2026-10-02T00:00:00Z",
        "modified: 2026-10-02T00:00:00Z",
        f"audience: [{', '.join(audience)}]",
        "verification:",
        "  method: written-only",
        '  via: ""',
        "wording:",
        *[f"  {a}: {t}" for a, t in wording.items()],
    ]
    if synced_wording:
        lines += ["synced_wording:", *[f"  {a}: {t}" for a, t in synced_wording.items()]]
    lines += ["---", "", f"**{rule_id:03d}**: Rule MUST hold.", ""]
    path = Path(d) / "rule" / f"{rule_id:03d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def sync_rows(d, root):
    return load(run(SYNC, "--dir", str(Path(d) / "rule"), "--root", str(root))[1])


class SyncHashTests(unittest.TestCase):
    def test_hash_ignores_synced_wording(self):
        base = "---\ntitle: t\naudience: [agent]\nwording:\n  agent: Never print.\n---\n\nbody\n"
        with_synced = base.replace(
            "---\n\nbody", "synced_wording:\n  agent: Never print.\n---\n\nbody"
        )
        self.assertEqual(sync_status.content_hash(base), sync_status.content_hash(with_synced))

    def test_hash_changes_when_wording_changes(self):
        before = "---\nwording:\n  agent: Never print.\n---\n"
        after = "---\nwording:\n  agent: Never reveal.\n---\n"
        self.assertNotEqual(sync_status.content_hash(before), sync_status.content_hash(after))


TRANSITIONS = [
    (["human"], ["agent"], {"human"}),
    (["agent"], ["human"], {"agent"}),
    (["human", "agent"], ["agent"], {"human"}),
    (["human", "agent"], ["human"], {"agent"}),
    (["agent"], ["human", "agent"], set()),
    (["human"], ["human", "agent"], set()),
]


class StaleTransitionTests(unittest.TestCase):
    def test_every_dropped_audience_is_listed_and_no_added_audience_is_removed(self):
        for old, new, dropped in TRANSITIONS:
            with self.subTest(old=old, new=new), scratch() as d:
                synced = {a: {"human": HUMAN, "agent": AGENT}[a] for a in old}
                wording = {a: {"human": HUMAN, "agent": AGENT}[a] for a in new}
                write_rule(d, new, wording, synced)
                root = Path(d) / "docs"
                root.mkdir()
                if "human" in old:
                    (root / "CONTRIBUTING.md").write_text(HUMAN + "\n", encoding="utf-8")
                if "agent" in old:
                    (root / "CLAUDE.md").write_text(AGENT + "\n", encoding="utf-8")
                    rules = root / ".claude" / "rules"
                    rules.mkdir(parents=True)
                    (rules / "001.md").write_text(AGENT + "\n", encoding="utf-8")
                row = sync_rows(d, root)[0]
                stale_audiences = {entry["audience"] for entry in row["stale_in"]}
                self.assertEqual(stale_audiences, dropped)
                self.assertTrue(stale_audiences.isdisjoint(set(new)))


class MalformedRuleTests(unittest.TestCase):
    def test_invalid_audience_gets_no_stale_or_missing_entries(self):
        with scratch() as d:
            write_rule(d, ["robot"], {"human": HUMAN}, {"human": HUMAN, "agent": AGENT})
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(HUMAN + "\n", encoding="utf-8")
            row = sync_rows(d, root)[0]
            self.assertIn("error", row)
            self.assertTrue(row["changed"])
            self.assertEqual(row["stale_in"], [])

    def test_missing_wording_is_still_reported_for_a_malformed_rule(self):
        with scratch() as d:
            write_rule(d, ["human", "agent"], {"human": HUMAN}, {})
            row = sync_rows(d, Path(d))[0]
            self.assertIn("error", row)
            self.assertEqual(row["missing_wording"], ["agent"])


class StaleStatusTests(unittest.TestCase):
    def dropped_human(self, d, contributing=None, claude=None):
        """Rule 001 moved from [human, agent] to [agent]; the human text is in CONTRIBUTING.md."""
        write_rule(
            d,
            ["agent"],
            {"agent": AGENT},
            {"human": HUMAN, "agent": AGENT},
        )
        root = Path(d) / "docs"
        root.mkdir(exist_ok=True)
        if contributing is not None:
            (root / "CONTRIBUTING.md").write_text(contributing, encoding="utf-8")
        if claude is not None:
            (root / "CLAUDE.md").write_text(claude, encoding="utf-8")
        return root

    def stale_human(self, row):
        return next(e for e in row["stale_in"] if e["audience"] == "human")

    def test_exact_text_is_found_once_with_kind_span(self):
        with scratch() as d:
            root = self.dropped_human(d, contributing=f"# Rules\n\n{HUMAN}\n")
            entry = self.stale_human(sync_rows(d, root)[0])
            self.assertEqual(entry["status"], "found")
            self.assertEqual(entry["kind"], "span")
            self.assertEqual(entry["path"], "CONTRIBUTING.md")
            self.assertEqual(entry["text"], HUMAN)

    def test_rewrapped_text_still_matches_with_whitespace_normalized(self):
        with scratch() as d:
            root = self.dropped_human(d, contributing="Secrets MUST NOT\n  appear\tin CI logs.\n")
            self.assertEqual(self.stale_human(sync_rows(d, root)[0])["status"], "found")

    def test_reworded_text_is_not_found(self):
        with scratch() as d:
            root = self.dropped_human(d, contributing="Secrets must never appear in CI logs.\n")
            self.assertEqual(self.stale_human(sync_rows(d, root)[0])["status"], "not_found")

    def test_duplicated_text_is_ambiguous(self):
        with scratch() as d:
            root = self.dropped_human(d, contributing=f"{HUMAN}\n\n{HUMAN}\n")
            self.assertEqual(self.stale_human(sync_rows(d, root)[0])["status"], "ambiguous")

    def test_missing_doc_is_absent_without_error(self):
        with scratch() as d:
            root = self.dropped_human(d)
            row = sync_rows(d, root)[0]
            self.assertEqual(self.stale_human(row)["status"], "absent")
            self.assertNotIn("error", row)

    def test_agent_only_file_is_found_only_on_exact_content(self):
        with scratch() as d:
            write_rule(d, ["human"], {"human": HUMAN}, {"agent": AGENT})
            root = Path(d) / "docs"
            rules = root / ".claude" / "rules"
            rules.mkdir(parents=True)
            (rules / "001.md").write_text(AGENT + "\n", encoding="utf-8")
            entry = next(e for e in sync_rows(d, root)[0]["stale_in"] if e["kind"] == "file")
            self.assertEqual(entry["status"], "found")
            self.assertEqual(entry["path"], ".claude/rules/001.md")
            (rules / "001.md").write_text(AGENT + " Edited.\n", encoding="utf-8")
            entry = next(e for e in sync_rows(d, root)[0]["stale_in"] if e["kind"] == "file")
            self.assertEqual(entry["status"], "not_found")

    def test_declined_removal_stays_changed_and_found(self):
        with scratch() as d:
            root = self.dropped_human(d, contributing=f"{HUMAN}\n")
            row = sync_rows(d, root)[0]
            self.assertTrue(row["changed"])
            self.assertEqual(self.stale_human(row)["status"], "found")

    def test_still_targeted_audience_is_never_stale(self):
        with scratch() as d:
            write_rule(
                d,
                ["human", "agent"],
                {"human": HUMAN, "agent": AGENT},
                {"human": HUMAN, "agent": AGENT},
            )
            row = sync_rows(d, Path(d))[0]
            self.assertEqual(row["stale_in"], [])
            self.assertEqual(row["missing_wording"], [])

    def test_active_audience_without_wording_is_reported(self):
        with scratch() as d:
            write_rule(d, ["human", "agent"], {"human": HUMAN}, {})
            row = sync_rows(d, Path(d))[0]
            self.assertEqual(row["missing_wording"], ["agent"])
            self.assertTrue(row["changed"])


RECORD = "skills/sync/scripts/record_sync.py"
EDIT = "skills/edit/scripts/edit_rule.py"


class AudienceChangeRecordTests(unittest.TestCase):
    """FR-003 and plan decision R8: an audience change reads as changed, and a recorded rule does not."""

    def test_audience_change_after_record_reads_changed(self):
        with scratch() as d:
            write(d, 1, "human, agent")
            rule_dir = Path(d) / "rule"
            self.assertEqual(run(RECORD, "--dir", str(rule_dir), "001")[0], 0)
            self.assertFalse(sync_rows(d, Path(d))[0]["changed"])
            code, out, _ = run(EDIT, "--dir", str(rule_dir), "--set", "audience=agent", "001")
            self.assertEqual(code, 0, out)
            row = sync_rows(d, Path(d))[0]
            self.assertTrue(row["changed"])
            self.assertEqual(row["targets"], ["CLAUDE.md", ".claude/rules/001.md"])

    def test_recorded_rule_with_no_audience_change_reads_unchanged(self):
        with scratch() as d:
            write(d, 1, "human, agent")
            rule_dir = Path(d) / "rule"
            self.assertEqual(run(RECORD, "--dir", str(rule_dir), "001")[0], 0)
            self.assertFalse(sync_rows(d, Path(d))[0]["changed"])


if __name__ == "__main__":
    unittest.main()
