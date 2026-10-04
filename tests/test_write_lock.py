import importlib.util
import sys
import unittest
from pathlib import Path

from tests._cli import scratch

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
SYNC = REPO / "skills" / "sync" / "scripts"
EDIT = REPO / "skills" / "edit" / "scripts"

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


def load(name, folder):
    for p in (SCRIPTS, SYNC, EDIT):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    spec = importlib.util.spec_from_file_location(name, folder / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy_lock = load("policy_lock", SCRIPTS)
record_sync = load("record_sync", SYNC)
edit_rule = load("edit_rule", EDIT)


def make_rule(rule_dir, rid="001"):
    rule_dir.mkdir(parents=True, exist_ok=True)
    path = rule_dir / f"{rid}.md"
    path.write_text(RULE.format(id=rid), encoding="utf-8")
    return path


class WriteLockTests(unittest.TestCase):
    def test_second_holder_times_out_while_lock_is_held(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            with (
                policy_lock.write_lock(rule_dir),
                self.assertRaises(policy_lock.LockTimeout),
                policy_lock.write_lock(rule_dir, timeout=0.2),
            ):
                pass

    def test_lock_is_released_on_exit(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            with policy_lock.write_lock(rule_dir):
                pass
            with policy_lock.write_lock(rule_dir, timeout=0.2):
                pass

    def test_lock_file_is_not_a_rule(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            with policy_lock.write_lock(rule_dir):
                pass
            self.assertEqual(list(rule_dir.glob("*.md")), [])


class BusyLockTests(unittest.TestCase):
    def test_record_sync_refuses_to_write_while_lock_is_busy(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            path = make_rule(rule_dir)
            before = path.read_bytes()
            record_sync.LOCK_TIMEOUT = 0.2
            try:
                with policy_lock.write_lock(rule_dir):
                    code = record_sync.main(["--dir", str(rule_dir), "001"])
            finally:
                record_sync.LOCK_TIMEOUT = 10.0
            self.assertEqual(code, 1)
            self.assertEqual(path.read_bytes(), before)

    def test_edit_commit_refuses_to_write_while_lock_is_busy(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            path = make_rule(rule_dir)
            before = path.read_bytes()
            text = path.read_text(encoding="utf-8")
            new_text, _ = edit_rule.edit_text(text, "001", [("title", "Renamed")])
            plan = [("001", path, text, new_text)]
            edit_rule.LOCK_TIMEOUT = 0.2
            try:
                with policy_lock.write_lock(rule_dir):
                    code = edit_rule.commit_plan(plan, rule_dir)
            finally:
                edit_rule.LOCK_TIMEOUT = 10.0
            self.assertEqual(code, 1)
            self.assertEqual(path.read_bytes(), before)


class ChangedSinceReadTests(unittest.TestCase):
    def test_edit_commit_keeps_a_concurrent_change_and_reports_it(self):
        with scratch() as d:
            rule_dir = Path(d) / "rule"
            path = make_rule(rule_dir)
            text = path.read_text(encoding="utf-8")
            new_text, _ = edit_rule.edit_text(text, "001", [("title", "Renamed")])
            plan = [("001", path, text, new_text)]
            concurrent = text.replace("CI logs", "build logs")
            path.write_text(concurrent, encoding="utf-8")
            code = edit_rule.commit_plan(plan, rule_dir)
            self.assertEqual(code, 1)
            self.assertEqual(path.read_text(encoding="utf-8"), concurrent)


if __name__ == "__main__":
    unittest.main()
