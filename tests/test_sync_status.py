import sys
import unittest
from pathlib import Path

from tests._cli import REPO, load, run, scratch, settle_docs

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
            settle_docs(
                d, {"human": "Rule 1 MUST hold for human.", "agent": "Rule 1 MUST hold for agent."}
            )
            rule_dir = Path(d) / "rule"
            self.assertEqual(run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")[0], 0)
            self.assertFalse(sync_rows(d, Path(d))[0]["changed"])
            code, out, _ = run(EDIT, "--dir", str(rule_dir), "--set", "audience=agent", "001")
            self.assertEqual(code, 0, out)
            row = sync_rows(d, Path(d))[0]
            self.assertTrue(row["changed"])
            self.assertEqual(row["targets"], ["CLAUDE.md", ".claude/rules/001.md"])

    def test_recorded_rule_with_no_audience_change_reads_unchanged(self):
        with scratch() as d:
            write(d, 1, "human, agent")
            settle_docs(
                d, {"human": "Rule 1 MUST hold for human.", "agent": "Rule 1 MUST hold for agent."}
            )
            rule_dir = Path(d) / "rule"
            self.assertEqual(run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")[0], 0)
            self.assertFalse(sync_rows(d, Path(d))[0]["changed"])


NEW_HUMAN = "Secrets MUST NOT leak into CI logs."


class RewordedAndReasonTests(unittest.TestCase):
    """FR-001, FR-002, R9 and R12: rewording a still-targeted audience, and the reason field."""

    def test_reworded_audience_is_found_with_reason_reworded(self):
        with scratch() as d:
            write_rule(
                d,
                ["human", "agent"],
                {"human": NEW_HUMAN, "agent": AGENT},
                {"human": HUMAN, "agent": AGENT},
            )
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(f"Intro.\n\n{HUMAN}\n", encoding="utf-8")
            row = sync_rows(d, root)[0]
            self.assertTrue(row["changed"])
            self.assertEqual(len(row["stale_in"]), 1)
            entry = row["stale_in"][0]
            self.assertEqual(entry["path"], "CONTRIBUTING.md")
            self.assertEqual(entry["audience"], "human")
            self.assertEqual(entry["reason"], "reworded")
            self.assertEqual(entry["status"], "found")
            self.assertEqual(entry["text"], HUMAN)

    def test_reworded_text_hand_edited_is_not_found(self):
        with scratch() as d:
            write_rule(
                d,
                ["human", "agent"],
                {"human": NEW_HUMAN, "agent": AGENT},
                {"human": HUMAN, "agent": AGENT},
            )
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(
                "Secrets must never reach CI logs.\n", encoding="utf-8"
            )
            entry = sync_rows(d, root)[0]["stale_in"][0]
            self.assertEqual((entry["reason"], entry["status"]), ("reworded", "not_found"))

    def test_reworded_text_appearing_twice_is_ambiguous(self):
        with scratch() as d:
            write_rule(
                d,
                ["human", "agent"],
                {"human": NEW_HUMAN, "agent": AGENT},
                {"human": HUMAN, "agent": AGENT},
            )
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(f"{HUMAN}\n\n{HUMAN}\n", encoding="utf-8")
            entry = sync_rows(d, root)[0]["stale_in"][0]
            self.assertEqual(entry["status"], "ambiguous")

    def test_reworded_agent_only_file_is_found_on_exact_content(self):
        with scratch() as d:
            write_rule(d, ["agent"], {"agent": "Print no secrets, ever."}, {"agent": AGENT})
            root = Path(d) / "docs"
            rules = root / ".claude" / "rules"
            rules.mkdir(parents=True)
            (rules / "001.md").write_text(AGENT + "\n", encoding="utf-8")
            file_entry = next(e for e in sync_rows(d, root)[0]["stale_in"] if e["kind"] == "file")
            self.assertEqual((file_entry["reason"], file_entry["status"]), ("reworded", "found"))

    def test_dropped_entries_carry_reason_dropped(self):
        with scratch() as d:
            write_rule(d, ["agent"], {"agent": AGENT}, {"human": HUMAN, "agent": AGENT})
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(HUMAN + "\n", encoding="utf-8")
            entry = next(e for e in sync_rows(d, root)[0]["stale_in"] if e["audience"] == "human")
            self.assertEqual(entry["reason"], "dropped")


class PendingAdditionTests(unittest.TestCase):
    """FR-004 and R15: additions are proposed only for targets where the wording is not in place."""

    def test_missing_wording_in_target_is_pending(self):
        with scratch() as d:
            write_rule(d, ["human"], {"human": HUMAN}, {})
            root = Path(d) / "docs"
            root.mkdir()
            row = sync_rows(d, root)[0]
            self.assertEqual(
                row["pending"], [{"path": "CONTRIBUTING.md", "audience": "human", "kind": "span"}]
            )

    def test_wording_already_in_target_is_not_pending(self):
        with scratch() as d:
            write_rule(d, ["human"], {"human": HUMAN}, {})
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(f"Intro.\n\n{HUMAN}\n", encoding="utf-8")
            self.assertEqual(sync_rows(d, root)[0]["pending"], [])

    def test_ambiguous_wording_in_target_is_not_pending(self):
        with scratch() as d:
            write_rule(d, ["human"], {"human": HUMAN}, {})
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(f"{HUMAN}\n\n{HUMAN}\n", encoding="utf-8")
            self.assertEqual(sync_rows(d, root)[0]["pending"], [])

    def test_agent_only_file_with_exact_content_is_not_pending(self):
        with scratch() as d:
            write_rule(d, ["agent"], {"agent": AGENT}, {"agent": AGENT})
            root = Path(d) / "docs"
            (root / ".claude" / "rules").mkdir(parents=True)
            (root / ".claude" / "rules" / "001.md").write_text(AGENT + "\n", encoding="utf-8")
            (root / "CLAUDE.md").write_text(f"{AGENT}\n", encoding="utf-8")
            self.assertEqual(sync_rows(d, root)[0]["pending"], [])

    def test_absent_doc_is_pending_and_is_never_created(self):
        with scratch() as d:
            write_rule(d, ["human"], {"human": HUMAN}, {})
            root = Path(d) / "docs"
            root.mkdir()
            row = sync_rows(d, root)[0]
            self.assertEqual(row["pending"][0]["path"], "CONTRIBUTING.md")
            self.assertFalse((root / "CONTRIBUTING.md").exists())


class OutputClarityTests(unittest.TestCase):
    """SC-004: the sync output alone names the document, the rule, and the text it will change."""

    def test_stale_entry_names_document_rule_and_text(self):
        with scratch() as d:
            write_rule(d, ["agent"], {"agent": AGENT}, {"human": HUMAN, "agent": AGENT})
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(HUMAN + "\n", encoding="utf-8")
            row = sync_rows(d, root)[0]
            entry = next(e for e in row["stale_in"] if e["audience"] == "human")
            self.assertEqual(
                (row["id"], entry["path"], entry["text"]), (1, "CONTRIBUTING.md", HUMAN)
            )


class AppliedRewordedTests(unittest.TestCase):
    """R15: a reworded removal whose new wording is already in place is not reported again."""

    def test_applied_reworded_removal_is_not_reported(self):
        with scratch() as d:
            write_rule(
                d,
                ["human", "agent"],
                {"human": NEW_HUMAN, "agent": AGENT},
                {"human": HUMAN, "agent": AGENT},
            )
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(f"Intro.\n\n{NEW_HUMAN}\n", encoding="utf-8")
            (root / "CLAUDE.md").write_text(f"{AGENT}\n", encoding="utf-8")
            (root / ".claude" / "rules").mkdir(parents=True)
            (root / ".claude" / "rules" / "001.md").write_text(AGENT + "\n", encoding="utf-8")
            row = sync_rows(d, root)[0]
            self.assertEqual(row["stale_in"], [])
            self.assertTrue(row["changed"])
            self.assertEqual(row["pending"], [])

    def test_reworded_removal_with_old_text_still_present_is_kept(self):
        with scratch() as d:
            write_rule(
                d,
                ["human"],
                {"human": NEW_HUMAN},
                {"human": HUMAN},
            )
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text(f"{HUMAN}\n", encoding="utf-8")
            row = sync_rows(d, root)[0]
            self.assertEqual([e["status"] for e in row["stale_in"]], ["found"])
            self.assertEqual(row["pending"][0]["path"], "CONTRIBUTING.md")

    def test_unapplied_reworded_removal_with_new_text_absent_is_not_found_and_kept(self):
        with scratch() as d:
            write_rule(d, ["human"], {"human": NEW_HUMAN}, {"human": HUMAN})
            root = Path(d) / "docs"
            root.mkdir()
            (root / "CONTRIBUTING.md").write_text("Hand-edited text.\n", encoding="utf-8")
            row = sync_rows(d, root)[0]
            self.assertEqual([e["status"] for e in row["stale_in"]], ["not_found"])


class HeldFileTests(unittest.TestCase):
    """FR-002 and the Assumptions: a hand-edited agent-only file is held, never overwritten."""

    NEW_AGENT = "Never leak secrets to CI output."

    def agent_file(self, d, root, text):
        rules = root / ".claude" / "rules"
        rules.mkdir(parents=True, exist_ok=True)
        path = rules / "001.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_hand_edited_agent_file_is_held_not_pending(self):
        with scratch() as d:
            write_rule(d, ["agent"], {"agent": AGENT}, {})
            root = Path(d) / "docs"
            root.mkdir()
            path = self.agent_file(d, root, "Hand-written paragraph.\n")
            row = sync_rows(d, root)[0]
            self.assertEqual(
                row["held"], [{"path": ".claude/rules/001.md", "audience": "agent", "kind": "file"}]
            )
            self.assertNotIn(".claude/rules/001.md", [e["path"] for e in row["pending"]])
            self.assertEqual(path.read_text(encoding="utf-8"), "Hand-written paragraph.\n")

    def test_agent_file_with_exact_wording_is_neither_held_nor_pending(self):
        with scratch() as d:
            write_rule(d, ["agent"], {"agent": AGENT}, {})
            root = Path(d) / "docs"
            root.mkdir()
            self.agent_file(d, root, AGENT + "\n")
            (root / "CLAUDE.md").write_text(AGENT + "\n", encoding="utf-8")
            row = sync_rows(d, root)[0]
            self.assertEqual(row["held"], [])
            self.assertEqual(row["pending"], [])

    def test_reworded_file_still_holding_last_written_wording_is_overwritten_not_held(self):
        with scratch() as d:
            write_rule(d, ["agent"], {"agent": self.NEW_AGENT}, {"agent": AGENT})
            root = Path(d) / "docs"
            root.mkdir()
            self.agent_file(d, root, AGENT + "\n")
            row = sync_rows(d, root)[0]
            self.assertEqual(row["held"], [])
            self.assertIn(".claude/rules/001.md", [e["path"] for e in row["pending"]])

    def test_reworded_file_with_hand_edits_is_held(self):
        with scratch() as d:
            write_rule(d, ["agent"], {"agent": self.NEW_AGENT}, {"agent": AGENT})
            root = Path(d) / "docs"
            root.mkdir()
            path = self.agent_file(d, root, "Someone rewrote this by hand.\n")
            row = sync_rows(d, root)[0]
            self.assertEqual([e["path"] for e in row["held"]], [".claude/rules/001.md"])
            self.assertNotIn(".claude/rules/001.md", [e["path"] for e in row["pending"]])
            self.assertEqual(path.read_text(encoding="utf-8"), "Someone rewrote this by hand.\n")


if __name__ == "__main__":
    unittest.main()
