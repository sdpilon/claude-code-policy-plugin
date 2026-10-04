import json
import unittest
from pathlib import Path

from tests._cli import run, scratch, settle_docs

REPO = Path(__file__).resolve().parent.parent
RECORD = "skills/sync/scripts/record_sync.py"
STATUS = "skills/sync/scripts/sync_status.py"

RULE = """---
title: "No secrets in CI logs"
tags: [security]
created: 2026-10-02T00:00:00Z
modified: 2026-10-02T00:00:00Z
audience: [agent]
verification:
  method: ci-blocking
  via: "secret-scan job"
wording:
  agent: "Never print secrets to CI output."
---

**{id}**: Secrets MUST NOT appear in CI logs.
"""


def without_synced_fields(text):
    """Drop the synced_hash line and the synced_wording block; every other line is kept as-is."""
    out, in_block = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith(("synced_hash:", "synced_wording:")):
            in_block = line.startswith("synced_wording:")
            continue
        if in_block and line.startswith("  "):
            continue
        in_block = False
        out.append(line)
    return "".join(out)


def make_rules(root, ids):
    rule_dir = Path(root) / ".policy" / "rule"
    rule_dir.mkdir(parents=True)
    for rule_id in ids:
        (rule_dir / f"{rule_id}.md").write_text(RULE.format(id=rule_id), encoding="utf-8")
        settle_docs(root, {"agent": "Never print secrets to CI output."}, int(rule_id))
    return rule_dir


def statuses(rule_dir):
    code, out, _ = run(STATUS, "--dir", str(rule_dir), "--root", str(rule_dir.parent.parent))
    assert code == 0, out
    return {f"{row['id']:03d}": row for row in json.loads(out)}


class RecordSyncTests(unittest.TestCase):
    def test_records_hash_so_rules_report_unchanged(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001", "002"])
            code, out, _ = run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001", "002")
            self.assertEqual(code, 0)
            self.assertIn("recorded 001", out)
            self.assertIn("recorded 002", out)
            rows = statuses(rule_dir)
            self.assertFalse(rows["001"]["changed"])
            self.assertFalse(rows["002"]["changed"])

    def test_second_run_is_a_no_op(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")
            before = (rule_dir / "001.md").read_bytes()
            code, out, _ = run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")
            self.assertEqual(code, 0)
            self.assertIn("unchanged 001", out)
            self.assertEqual((rule_dir / "001.md").read_bytes(), before)

    def test_unknown_id_exits_2_and_writes_nothing(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            before = (rule_dir / "001.md").read_bytes()
            code, _out, err = run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001", "999")
            self.assertEqual(code, 2)
            self.assertIn("999", err)
            self.assertEqual((rule_dir / "001.md").read_bytes(), before)

    def test_body_and_other_fields_are_unchanged_byte_for_byte(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            original = (rule_dir / "001.md").read_text(encoding="utf-8")
            run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")
            recorded = (rule_dir / "001.md").read_text(encoding="utf-8")
            self.assertEqual(without_synced_fields(recorded), original)

    def test_recording_an_edited_rule_updates_its_hash(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")
            path = rule_dir / "001.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace("CI logs", "build logs"),
                encoding="utf-8",
            )
            self.assertTrue(statuses(rule_dir)["001"]["changed"])
            code, out, _ = run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")
            self.assertEqual(code, 0)
            self.assertIn("recorded 001", out)
            self.assertFalse(statuses(rule_dir)["001"]["changed"])


class ConcurrentWriteTests(unittest.TestCase):
    """T026: a rule that changed after it was read must not be overwritten."""

    @staticmethod
    def module():
        import importlib.util
        import sys

        scripts = REPO / "skills" / "sync" / "scripts"
        sys.path.insert(0, str(scripts))
        spec = importlib.util.spec_from_file_location("record_sync", scripts / "record_sync.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_write_is_refused_when_rule_changed_after_it_was_read(self):
        module = self.module()
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            path = rule_dir / "001.md"
            current = path.read_text(encoding="utf-8")
            updated = module.with_synced_hash(current, module.content_hash(current))
            concurrent = current.replace("CI logs", "build logs")
            path.write_text(concurrent, encoding="utf-8")
            with self.assertRaises(module.ChangedDuringRecord):
                module.write_if_unchanged(path, current, updated)
            self.assertEqual(path.read_text(encoding="utf-8"), concurrent)

    def test_write_proceeds_when_rule_is_unchanged(self):
        module = self.module()
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            path = rule_dir / "001.md"
            current = path.read_text(encoding="utf-8")
            updated = module.with_synced_hash(current, module.content_hash(current))
            module.write_if_unchanged(path, current, updated)
            self.assertEqual(path.read_text(encoding="utf-8"), updated)


HUMAN = "Secrets MUST NOT appear in CI logs."
AGENT = "Never print secrets to CI output."

WORDING_RULE = """---
title: "No secrets in CI logs"
created: 2026-10-02T00:00:00Z
modified: 2026-10-02T00:00:00Z
audience: [{audience}]
verification:
  method: written-only
  via: ""
wording:
{wording}{synced}---

**001**: Secrets MUST NOT appear in CI logs.
"""


def write_wording_rule(rule_dir, audience, wording, synced=""):
    rule_dir.mkdir(parents=True, exist_ok=True)
    path = rule_dir / "001.md"
    body = "".join(f"  {a}: {t}\n" for a, t in wording.items())
    path.write_text(
        WORDING_RULE.format(audience=audience, wording=body, synced=synced), encoding="utf-8"
    )
    settle_docs(rule_dir.parent, wording)
    return path


class RecordSyncWordingTests(unittest.TestCase):
    def test_records_wording_for_current_audiences(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            path = write_wording_rule(rule_dir, "human, agent", {"human": HUMAN, "agent": AGENT})
            self.assertEqual(run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")[0], 0)
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"synced_wording:\n  human: {HUMAN}\n  agent: {AGENT}\n", text)

    def test_prunes_synced_wording_for_dropped_audience(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            synced = f"synced_wording:\n  human: {HUMAN}\n  agent: {AGENT}\n"
            path = write_wording_rule(rule_dir, "agent", {"agent": AGENT}, synced)
            self.assertEqual(run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")[0], 0)
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"synced_wording:\n  agent: {AGENT}\n", text)
            self.assertNotIn("  human:", text.split("synced_wording:", 1)[1])

    def test_removes_synced_wording_block_when_no_current_wording_remains(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            synced = f"synced_wording:\n  human: {HUMAN}\n"
            path = write_wording_rule(rule_dir, "agent", {}, synced)
            self.assertEqual(run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")[0], 0)
            self.assertNotIn("synced_wording", path.read_text(encoding="utf-8"))

    def test_recorded_rule_reads_unchanged(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            write_wording_rule(rule_dir, "human, agent", {"human": HUMAN, "agent": AGENT})
            run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")
            _, out, _ = run(STATUS, "--dir", str(rule_dir), "--root", d)
            row = json.loads(out)[0]
            self.assertFalse(row["changed"])
            self.assertEqual(row["stale_in"], [])


class RecordSyncExpectTests(unittest.TestCase):
    def proposed_hash(self, rule_dir):
        _, out, _ = run(STATUS, "--dir", str(rule_dir), "--root", str(rule_dir.parent))
        return json.loads(out)[0]["current_hash"]

    def test_records_when_source_still_matches_the_proposal(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            digest = self.proposed_hash(rule_dir)
            code, out, _ = run(
                RECORD, "--root", str(d), "--dir", str(rule_dir), "--expect", f"001={digest}", "001"
            )
            self.assertEqual(code, 0)
            self.assertIn("recorded 001", out)

    def test_refuses_and_writes_nothing_when_source_changed_after_proposal(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            digest = self.proposed_hash(rule_dir)
            path = rule_dir / "001.md"
            path.write_text(path.read_text(encoding="utf-8").replace("CI logs", "build logs"))
            before = path.read_bytes()
            code, _out, err = run(
                RECORD, "--dir", str(rule_dir), "--expect", f"001={digest}", "001"
            )
            self.assertEqual(code, 1)
            self.assertIn("changed since it was proposed", err)
            self.assertEqual(path.read_bytes(), before)

    def test_expect_for_a_rule_not_being_recorded_exits_2(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001", "002"])
            code, _out, err = run(
                RECORD, "--root", str(d), "--dir", str(rule_dir), "--expect", "002=abc", "001"
            )
            self.assertEqual(code, 2)
            self.assertIn("002", err)


class RecordSyncUnappliedTests(unittest.TestCase):
    """FR-004 and R14: record_sync refuses a rule that still has an unapplied change."""

    NEW_HUMAN = "Secrets MUST NOT leak into CI logs."

    def test_refuses_while_an_addition_is_pending(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            path = write_wording_rule(rule_dir, "human, agent", {"human": HUMAN, "agent": AGENT})
            (Path(d) / "CONTRIBUTING.md").unlink()
            before = path.read_bytes()
            code, _out, err = run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")
            self.assertEqual(code, 1)
            self.assertIn("addition to CONTRIBUTING.md", err)
            self.assertEqual(path.read_bytes(), before)

    def test_scenario_11_partial_approval_is_refused_then_recorded(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            path = write_wording_rule(rule_dir, "human, agent", {"human": HUMAN, "agent": AGENT})
            self.assertEqual(run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")[0], 0)
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    f"wording:\n  human: {HUMAN}", f"wording:\n  human: {self.NEW_HUMAN}", 1
                ),
                encoding="utf-8",
            )
            # The addition is approved and applied; the removal of the old sentence is declined.
            (Path(d) / "CONTRIBUTING.md").write_text(
                f"{HUMAN}\n{self.NEW_HUMAN}\n", encoding="utf-8"
            )
            before = path.read_bytes()
            code, _out, err = run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")
            self.assertEqual(code, 1)
            self.assertIn("removal from CONTRIBUTING.md", err)
            self.assertEqual(path.read_bytes(), before)
            # Once the old sentence is removed too, every change is applied and the record goes through.
            (Path(d) / "CONTRIBUTING.md").write_text(f"{self.NEW_HUMAN}\n", encoding="utf-8")
            self.assertEqual(run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")[0], 0)

    def test_not_found_report_does_not_block_recording(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            synced = f"synced_wording:\n  human: {HUMAN}\n  agent: {AGENT}\n"
            write_wording_rule(rule_dir, "agent", {"agent": AGENT}, synced)
            (Path(d) / "CONTRIBUTING.md").write_text("Hand-edited text.\n", encoding="utf-8")
            code, _out, _err = run(RECORD, "--root", str(d), "--dir", str(rule_dir), "001")
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
