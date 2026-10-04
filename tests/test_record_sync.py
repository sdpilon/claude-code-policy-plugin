import json
import unittest
from pathlib import Path

from tests._cli import run, scratch

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
---

**{id}**: Secrets MUST NOT appear in CI logs.
"""


def make_rules(root, ids):
    rule_dir = Path(root) / ".policy" / "rule"
    rule_dir.mkdir(parents=True)
    for rule_id in ids:
        (rule_dir / f"{rule_id}.md").write_text(RULE.format(id=rule_id), encoding="utf-8")
    return rule_dir


def statuses(rule_dir):
    code, out, _ = run(STATUS, "--dir", str(rule_dir))
    assert code == 0, out
    return {f"{row['id']:03d}": row for row in json.loads(out)}


class RecordSyncTests(unittest.TestCase):
    def test_records_hash_so_rules_report_unchanged(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001", "002"])
            code, out, _ = run(RECORD, "--dir", str(rule_dir), "001", "002")
            self.assertEqual(code, 0)
            self.assertIn("recorded 001", out)
            self.assertIn("recorded 002", out)
            rows = statuses(rule_dir)
            self.assertFalse(rows["001"]["changed"])
            self.assertFalse(rows["002"]["changed"])

    def test_second_run_is_a_no_op(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            run(RECORD, "--dir", str(rule_dir), "001")
            before = (rule_dir / "001.md").read_bytes()
            code, out, _ = run(RECORD, "--dir", str(rule_dir), "001")
            self.assertEqual(code, 0)
            self.assertIn("unchanged 001", out)
            self.assertEqual((rule_dir / "001.md").read_bytes(), before)

    def test_unknown_id_exits_2_and_writes_nothing(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            before = (rule_dir / "001.md").read_bytes()
            code, _out, err = run(RECORD, "--dir", str(rule_dir), "001", "999")
            self.assertEqual(code, 2)
            self.assertIn("999", err)
            self.assertEqual((rule_dir / "001.md").read_bytes(), before)

    def test_body_and_other_fields_are_unchanged_byte_for_byte(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            original = (rule_dir / "001.md").read_text(encoding="utf-8")
            run(RECORD, "--dir", str(rule_dir), "001")
            recorded = (rule_dir / "001.md").read_text(encoding="utf-8")
            stripped = "".join(
                line
                for line in recorded.splitlines(keepends=True)
                if not line.startswith("synced_hash:")
            )
            self.assertEqual(stripped, original)

    def test_recording_an_edited_rule_updates_its_hash(self):
        with scratch() as d:
            rule_dir = make_rules(d, ["001"])
            run(RECORD, "--dir", str(rule_dir), "001")
            path = rule_dir / "001.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace("CI logs", "build logs"),
                encoding="utf-8",
            )
            self.assertTrue(statuses(rule_dir)["001"]["changed"])
            code, out, _ = run(RECORD, "--dir", str(rule_dir), "001")
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


if __name__ == "__main__":
    unittest.main()
