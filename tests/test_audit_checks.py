import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path

from tests._cli import run, scratch

REPO = Path(__file__).resolve().parent.parent
AUDIT = "skills/audit/scripts/audit_checks.py"
SCRIPTS = REPO / "skills" / "audit" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load("audit_checks")
github_tracker = load("github_tracker")

RULE = """---
title: "Rule {rid}"
tags: []
created: 2026-10-02T00:00:00Z
modified: 2026-10-02T00:00:00Z
audience: [agent]
verification:
  method: {method}
  via: "{via}"
{defect}---

**{rid}**: Builds MUST pass.
"""


def write_rule(policy_dir, rid, via, method="ci-checked", defect=None):
    rule_dir = Path(policy_dir) / "rule"
    rule_dir.mkdir(parents=True, exist_ok=True)
    defect_line = f"defect: {defect}\n" if defect else ""
    text = RULE.format(rid=rid, via=via, method=method, defect=defect_line)
    (rule_dir / f"{rid}.md").write_text(text, encoding="utf-8")


class FakeTracker:
    """In-memory tracker: records every search and every filed issue."""

    def __init__(self, open_issues=None):
        self.open = {label: list(urls) for label, urls in (open_issues or {}).items()}
        self.created = []

    def find_open(self, label):
        return [{"url": url} for url in self.open.get(label, [])]

    def create(self, title, body, label):
        url = f"https://example.test/issues/{len(self.created) + 1}"
        self.created.append({"title": title, "body": body, "label": label, "url": url})
        self.open.setdefault(label, []).append(url)
        return url


class AuditTests(unittest.TestCase):
    def audit(self, policy_dir, checks, tracker):
        lines = []
        rules = audit.load_rules(Path(policy_dir))
        code = audit.run_audit(rules, checks, tracker, out=lines.append)
        return code, lines

    def test_passing_check_logs_pass_and_files_nothing(self):
        with scratch() as d:
            write_rule(d, "001", "lint-clean")
            tracker = FakeTracker()
            code, lines = self.audit(d, {"lint-clean": lambda: True}, tracker)
            self.assertEqual(code, 0)
            self.assertEqual(lines, ["pass 001"])
            self.assertEqual(tracker.created, [])

    def test_failing_check_files_one_issue_with_label_and_marker(self):
        with scratch() as d:
            write_rule(d, "002", "deploy-gate")
            tracker = FakeTracker()
            code, lines = self.audit(d, {"deploy-gate": lambda: False}, tracker)
            self.assertEqual(code, 0)
            self.assertEqual(len(tracker.created), 1)
            issue = tracker.created[0]
            self.assertEqual(issue["title"], "Policy check failing: deploy-gate")
            self.assertEqual(issue["label"], "policy-audit:deploy-gate")
            self.assertIn("<!-- policy-audit-key: deploy-gate -->", issue["body"])
            self.assertTrue(lines[0].startswith("filed 002"))

    def test_unbuilt_check_files_build_issue(self):
        with scratch() as d:
            write_rule(d, "003", "secret-scan")
            tracker = FakeTracker()
            _code, lines = self.audit(d, {}, tracker)
            self.assertEqual(tracker.created[0]["title"], "Build policy check: secret-scan")
            self.assertTrue(lines[0].startswith("filed 003"))

    def test_existing_open_issue_prevents_filing_even_after_title_change(self):
        with scratch() as d:
            write_rule(d, "004", "deploy-gate")
            tracker = FakeTracker({"policy-audit:deploy-gate": ["https://example.test/9"]})
            _code, lines = self.audit(d, {"deploy-gate": lambda: False}, tracker)
            self.assertEqual(tracker.created, [])
            self.assertIn("already open", lines[0])
            self.assertIn("https://example.test/9", lines[0])

    def test_defect_rule_is_skipped_and_its_check_never_runs(self):
        with scratch() as d:
            write_rule(d, "005", "must-not-run", defect="owner review pending")
            calls = []
            tracker = FakeTracker()
            code, lines = self.audit(d, {"must-not-run": lambda: calls.append(1) or False}, tracker)
            self.assertEqual(code, 0)
            self.assertEqual(calls, [])
            self.assertEqual(tracker.created, [])
            self.assertEqual(lines, ["skipped 005 (defect)"])

    def test_raising_check_counts_as_failing_with_exception_in_body(self):
        def boom():
            raise RuntimeError("probe timed out")

        with scratch() as d:
            write_rule(d, "006", "flaky-probe")
            tracker = FakeTracker()
            code, _lines = self.audit(d, {"flaky-probe": boom}, tracker)
            self.assertEqual(code, 0)
            self.assertEqual(tracker.created[0]["title"], "Policy check failing: flaky-probe")
            self.assertIn("probe timed out", tracker.created[0]["body"])

    def test_rules_sharing_one_check_produce_one_issue(self):
        with scratch() as d:
            write_rule(d, "007", "shared-gate")
            write_rule(d, "008", "shared-gate")
            tracker = FakeTracker()
            _code, lines = self.audit(d, {"shared-gate": lambda: False}, tracker)
            self.assertEqual(len(tracker.created), 1)
            self.assertIn("007", tracker.created[0]["body"])
            self.assertIn("008", tracker.created[0]["body"])
            self.assertEqual(len(lines), 2)

    def test_second_run_files_nothing_new(self):
        with scratch() as d:
            write_rule(d, "009", "deploy-gate")
            tracker = FakeTracker()
            checks = {"deploy-gate": lambda: False}
            self.audit(d, checks, tracker)
            self.assertEqual(len(tracker.created), 1)
            _code, lines = self.audit(d, checks, tracker)
            self.assertEqual(len(tracker.created), 1)
            self.assertTrue(lines[0].startswith("skipped 009 (already open"))

    def test_non_ci_checked_rules_are_ignored(self):
        with scratch() as d:
            write_rule(d, "010", "lint-clean", method="written-only")
            tracker = FakeTracker()
            code, lines = self.audit(d, {}, tracker)
            self.assertEqual((code, lines, tracker.created), (0, [], []))

    def test_tracker_failure_exits_1(self):
        class Broken(FakeTracker):
            def find_open(self, label):
                raise audit.TrackerError("gh not authenticated")

        with scratch() as d:
            write_rule(d, "011", "deploy-gate")
            code, _lines = self.audit(d, {"deploy-gate": lambda: False}, Broken())
            self.assertEqual(code, 1)


class RegistryCliTests(unittest.TestCase):
    def test_registry_without_checks_exits_2_and_files_nothing(self):
        with scratch() as d:
            write_rule(Path(d) / ".policy", "001", "lint-clean")
            registry = Path(d) / "checks.py"
            registry.write_text("NOT_CHECKS = {}\n", encoding="utf-8")
            code, _out, err = run(
                AUDIT,
                "--registry",
                str(registry),
                "--policy-dir",
                str(Path(d) / ".policy"),
                "--tracker",
                "none",
            )
            self.assertEqual(code, 2)
            self.assertIn("CHECKS", err)

    def test_dry_run_tracker_logs_without_filing(self):
        with scratch() as d:
            write_rule(Path(d) / ".policy", "002", "secret-scan")
            registry = Path(d) / "checks.py"
            registry.write_text("CHECKS = {}\n", encoding="utf-8")
            code, out, _err = run(
                AUDIT,
                "--registry",
                str(registry),
                "--policy-dir",
                str(Path(d) / ".policy"),
                "--tracker",
                "none",
            )
            self.assertEqual(code, 0)
            self.assertIn("filed 002", out)
            self.assertIn("(dry run)", out)


class GitHubTrackerTests(unittest.TestCase):
    def fake_gh(self, directory, existing_json):
        log = Path(directory) / "calls.log"
        script = Path(directory) / "gh"
        script.write_text(
            "#!/bin/sh\n"
            f'echo "$@" >> "{log}"\n'
            'case "$1 $2" in\n'
            f"  'issue list') echo '{existing_json}' ;;\n"
            "  'issue create') echo 'https://github.test/owner/repo/issues/7' ;;\n"
            "  'label create') exit 0 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return str(script), log

    def test_find_open_parses_gh_json(self):
        with tempfile.TemporaryDirectory() as d:
            gh, _log = self.fake_gh(d, '[{"url": "https://github.test/owner/repo/issues/3"}]')
            tracker = github_tracker.GitHubTracker(gh=gh)
            self.assertEqual(
                tracker.find_open("policy-audit:x"),
                [{"url": "https://github.test/owner/repo/issues/3"}],
            )

    def test_create_labels_then_files_and_returns_url(self):
        with tempfile.TemporaryDirectory() as d:
            gh, log = self.fake_gh(d, "[]")
            tracker = github_tracker.GitHubTracker(gh=gh)
            url = tracker.create("Policy check failing: x", "body", "policy-audit:x")
            self.assertEqual(url, "https://github.test/owner/repo/issues/7")
            calls = log.read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(c.startswith("label create policy-audit:x") for c in calls))
            self.assertTrue(any(c.startswith("issue create") for c in calls))

    def test_never_closes_issues(self):
        with tempfile.TemporaryDirectory() as d:
            gh, log = self.fake_gh(d, "[]")
            tracker = github_tracker.GitHubTracker(gh=gh)
            tracker.find_open("policy-audit:x")
            tracker.create("t", "b", "policy-audit:x")
            self.assertFalse(any("close" in c for c in log.read_text().splitlines()))


class TrackerFailureTests(unittest.TestCase):
    """T027: one tracker failure must not stop the remaining rules from being checked."""

    def test_later_rules_still_run_and_exit_is_1(self):
        class FailsForOneLabel(FakeTracker):
            def find_open(self, label):
                if label == "policy-audit:broken-gate":
                    raise audit.TrackerError("gh not authenticated")
                return super().find_open(label)

        with scratch() as d:
            write_rule(d, "001", "broken-gate")
            write_rule(d, "002", "deploy-gate")
            write_rule(d, "003", "lint-clean")
            tracker = FailsForOneLabel()
            lines = []
            code = audit.run_audit(
                audit.load_rules(Path(d)),
                {
                    "broken-gate": lambda: False,
                    "deploy-gate": lambda: False,
                    "lint-clean": lambda: True,
                },
                tracker,
                out=lines.append,
            )
            self.assertEqual(code, 1)
            self.assertTrue(any(l.startswith("error 001") for l in lines), lines)
            self.assertTrue(any(l.startswith("filed 002") for l in lines), lines)
            self.assertIn("pass 003", lines)
            self.assertEqual(
                [i["title"] for i in tracker.created], ["Policy check failing: deploy-gate"]
            )


if __name__ == "__main__":
    unittest.main()
