import re
import unittest
from pathlib import Path

from tests._cli import run, scratch

EDIT = "skills/edit/scripts/edit_rule.py"
SYNCED = "a" * 64

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
synced_hash: {synced}
---

**{id}**: Secrets MUST NOT appear in CI logs.
"""


def make_rule(root, rule_id="001", synced=SYNCED):
    rule_dir = Path(root) / ".policy" / "rule"
    rule_dir.mkdir(parents=True, exist_ok=True)
    path = rule_dir / f"{rule_id}.md"
    path.write_text(RULE.format(id=rule_id, synced=synced), encoding="utf-8")
    return rule_dir, path


class EditRuleTests(unittest.TestCase):
    def test_edit_sets_modified_to_now(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            code, out, _ = run(
                EDIT, "--dir", str(rule_dir), "--set", "title=Keep secrets out of logs", "001"
            )
            self.assertEqual(code, 0, out)
            self.assertIn("changed 001", out)
            text = path.read_text(encoding="utf-8")
            modified = next(l for l in text.splitlines() if l.startswith("modified:"))
            self.assertGreater(modified.split(":", 1)[1].strip().strip('"'), "2026-10-02T00:00:00Z")
            self.assertIn("title: Keep secrets out of logs", text)

    def test_edit_leaves_synced_hash_untouched(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            run(EDIT, "--dir", str(rule_dir), "--set", "title=Renamed", "001")
            self.assertIn(f"synced_hash: {SYNCED}", path.read_text(encoding="utf-8"))

    def test_statement_edit_replaces_the_body_sentence(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            code, _out, _ = run(
                EDIT,
                "--dir",
                str(rule_dir),
                "--set",
                "statement=Secrets MUST NOT appear in build logs.",
                "--reviewed-wording",
                "001",
            )
            self.assertEqual(code, 0)
            text = path.read_text(encoding="utf-8")
            self.assertIn("**001**: Secrets MUST NOT appear in build logs.", text)
            self.assertNotIn("Secrets MUST NOT appear in CI logs.", text)

    def test_disallowed_field_is_rejected_by_name(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            before = path.read_bytes()
            code, _out, err = run(
                EDIT, "--dir", str(rule_dir), "--set", "created=2020-01-01T00:00:00Z", "001"
            )
            self.assertEqual(code, 2)
            self.assertIn("created", err)
            self.assertEqual(path.read_bytes(), before)

    def test_statement_with_two_modal_verbs_is_rejected_and_file_unchanged(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            before = path.read_bytes()
            code, out, _err = run(
                EDIT,
                "--dir",
                str(rule_dir),
                "--set",
                "statement=Secrets MUST NOT leak and MAY be logged.",
                "--reviewed-wording",
                "001",
            )
            self.assertEqual(code, 2)
            self.assertIn("rejected 001", out)
            self.assertEqual(path.read_bytes(), before)

    def test_invalid_verification_method_is_rejected(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            before = path.read_bytes()
            code, _out, _err = run(
                EDIT,
                "--dir",
                str(rule_dir),
                "--set",
                "verification.method=maybe",
                "001",
            )
            self.assertEqual(code, 2)
            self.assertEqual(path.read_bytes(), before)

    def test_preview_prints_change_and_writes_nothing(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            before = path.read_bytes()
            code, out, _ = run(
                EDIT,
                "--dir",
                str(rule_dir),
                "--preview",
                "--set",
                "title=Renamed",
                "001",
            )
            self.assertEqual(code, 0)
            self.assertIn("Renamed", out)
            self.assertEqual(path.read_bytes(), before)

    def test_same_value_is_unchanged_and_keeps_modified(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            before = path.read_bytes()
            code, out, _ = run(
                EDIT, "--dir", str(rule_dir), "--set", "title=No secrets in CI logs", "001"
            )
            self.assertEqual(code, 0)
            self.assertIn("unchanged 001", out)
            self.assertEqual(path.read_bytes(), before)


class BulkEditTests(unittest.TestCase):
    def test_bulk_edit_changes_every_listed_rule(self):
        with scratch() as d:
            rule_dir, first = make_rule(d, "001")
            _, second = make_rule(d, "002")
            code, out, _ = run(
                EDIT, "--dir", str(rule_dir), "--set", "audience=agent", "001", "002"
            )
            self.assertEqual(code, 0, out)
            self.assertIn("changed 001", out)
            self.assertIn("changed 002", out)
            for path in (first, second):
                self.assertIn("audience: [agent]", path.read_text(encoding="utf-8"))

    def test_one_invalid_rule_means_no_rule_changes(self):
        with scratch() as d:
            rule_dir, first = make_rule(d, "001")
            _, second = make_rule(d, "002")
            # Rule 002 has no statement line, so a statement edit cannot apply to it.
            second.write_text(
                second.read_text(encoding="utf-8").replace("**002**:", "Note:"),
                encoding="utf-8",
            )
            before_first = first.read_bytes()
            before_second = second.read_bytes()
            code, out, _ = run(
                EDIT,
                "--dir",
                str(rule_dir),
                "--set",
                "statement=Secrets MUST NOT appear in build logs.",
                "--reviewed-wording",
                "001",
                "002",
            )
            self.assertEqual(code, 2)
            self.assertIn("rejected 002", out)
            self.assertNotIn("changed 001", out)
            self.assertEqual(first.read_bytes(), before_first)
            self.assertEqual(second.read_bytes(), before_second)

    def test_bulk_preview_writes_nothing(self):
        with scratch() as d:
            rule_dir, first = make_rule(d, "001")
            _, second = make_rule(d, "002")
            before = (first.read_bytes(), second.read_bytes())
            code, out, _ = run(
                EDIT, "--dir", str(rule_dir), "--preview", "--set", "tags=ci", "001", "002"
            )
            self.assertEqual(code, 0)
            self.assertIn("preview 001", out)
            self.assertIn("preview 002", out)
            self.assertEqual((first.read_bytes(), second.read_bytes()), before)

    def test_write_failure_restores_files_already_written(self):
        import importlib.util
        import io
        from contextlib import redirect_stderr, redirect_stdout

        repo = Path(__file__).resolve().parent.parent
        spec = importlib.util.spec_from_file_location("edit_rule", repo / EDIT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        real_write = module.manifest.atomic_write_bytes
        calls = []

        def flaky_write(path, data):
            calls.append(Path(path).name)
            # The second write fails; the restore writes that follow must succeed.
            if len(calls) == 2:
                raise OSError("disk full")
            return real_write(path, data)

        with scratch() as d:
            rule_dir, first = make_rule(d, "001")
            _, second = make_rule(d, "002")
            before = (first.read_bytes(), second.read_bytes())
            module.manifest.atomic_write_bytes = flaky_write
            out, err = io.StringIO(), io.StringIO()
            try:
                with redirect_stdout(out), redirect_stderr(err):
                    code = module.main(["--dir", str(rule_dir), "--set", "tags=ci", "001", "002"])
            finally:
                module.manifest.atomic_write_bytes = real_write
            self.assertEqual(code, 1)
            self.assertIn("restored", err.getvalue())
            self.assertEqual((first.read_bytes(), second.read_bytes()), before)


RULE_BOTH = """---
title: "No secrets in CI logs"
tags: [security]
created: 2026-10-02T00:00:00Z
modified: 2026-10-02T00:00:00Z
audience: [human, agent]
verification:
  method: ci-blocking
  via: "secret-scan job"
wording:
  human: "Secrets MUST NOT appear in CI logs."
  agent: "Never print secrets to CI output."
synced_hash: {synced}
synced_wording:
  human: "Secrets MUST NOT appear in CI logs."
  agent: "Never print secrets to CI output."
---

**001**: Secrets MUST NOT appear in CI logs.
"""


class WordingEditTests(unittest.TestCase):
    def make_both(self, d):
        rule_dir = Path(d) / ".policy" / "rule"
        rule_dir.mkdir(parents=True)
        path = rule_dir / "001.md"
        path.write_text(RULE_BOTH.format(synced=SYNCED), encoding="utf-8")
        return rule_dir, path

    def test_wording_for_an_audience_is_editable(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            code, out, _ = run(
                EDIT,
                "--dir",
                str(rule_dir),
                "--set",
                "wording.agent=Never   print secrets.",
                "001",
            )
            self.assertEqual(code, 0, out)
            self.assertIn("  agent: Never print secrets.\n", path.read_text(encoding="utf-8"))

    def test_wording_for_audience_not_in_rule_is_rejected(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            before = path.read_bytes()
            code, out, _ = run(
                EDIT, "--dir", str(rule_dir), "--set", "wording.human=Secrets MUST NOT leak.", "001"
            )
            self.assertEqual(code, 2)
            self.assertIn("not in audience", out)
            self.assertEqual(path.read_bytes(), before)

    def test_dropping_an_audience_drops_its_wording_but_keeps_synced_wording(self):
        with scratch() as d:
            rule_dir, path = self.make_both(d)
            code, out, _ = run(EDIT, "--dir", str(rule_dir), "--set", "audience=agent", "001")
            self.assertEqual(code, 0, out)
            text = path.read_text(encoding="utf-8")
            wording_block = text.split("wording:\n", 1)[1].split("synced_hash:", 1)[0]
            self.assertEqual(wording_block, "  agent: Never print secrets to CI output.\n")
            self.assertIn("synced_wording:\n  human: Secrets MUST NOT appear in CI logs.", text)

    def test_adding_an_audience_without_wording_is_rejected(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            before = path.read_bytes()
            code, out, _ = run(EDIT, "--dir", str(rule_dir), "--set", "audience=human,agent", "001")
            self.assertEqual(code, 2)
            self.assertIn("human", out)
            self.assertEqual(path.read_bytes(), before)

    def test_editing_wording_never_changes_synced_wording(self):
        with scratch() as d:
            rule_dir, path = self.make_both(d)
            run(EDIT, "--dir", str(rule_dir), "--set", "wording.agent=Never print secrets.", "001")
            text = path.read_text(encoding="utf-8")
            self.assertIn(
                "synced_wording:\n  human: Secrets MUST NOT appear in CI logs.\n"
                "  agent: Never print secrets to CI output.",
                text,
            )

    def test_statement_preview_lists_each_audience_wording_for_review(self):
        with scratch() as d:
            rule_dir, _path = self.make_both(d)
            code, out, _ = run(
                EDIT,
                "--dir",
                str(rule_dir),
                "--preview",
                "--set",
                "statement=Secrets MUST NOT appear in build logs.",
                "--reviewed-wording",
                "001",
            )
            self.assertEqual(code, 0)
            self.assertIn("review wording.agent: Never print secrets to CI output.", out)
            self.assertIn("review wording.human: Secrets MUST NOT appear in CI logs.", out)


class DropAndReviewTests(unittest.TestCase):
    make_both = WordingEditTests.make_both

    """FR-012: a drop that would discard an unrecorded wording edit is refused. FR-009: review flag."""

    def test_drop_is_rejected_after_an_unrecorded_wording_edit(self):
        with scratch() as d:
            rule_dir, path = self.make_both(d)
            run(
                EDIT, "--dir", str(rule_dir), "--set", "wording.human=Secrets MUST NOT leak.", "001"
            )
            before = path.read_bytes()
            code, out, _ = run(EDIT, "--dir", str(rule_dir), "--set", "audience=agent", "001")
            self.assertEqual(code, 2)
            self.assertIn("audience human cannot be dropped", out)
            self.assertIn("Run sync", out)
            self.assertEqual(path.read_bytes(), before)

    def test_drop_is_allowed_when_wording_matches_what_was_recorded(self):
        with scratch() as d:
            rule_dir, _path = self.make_both(d)
            code, out, _ = run(EDIT, "--dir", str(rule_dir), "--set", "audience=agent", "001")
            self.assertEqual(code, 0, out)
            self.assertIn("changed 001", out)

    def test_drop_is_allowed_for_an_audience_never_recorded(self):
        with scratch() as d:
            rule_dir, path = self.make_both(d)
            text = re.sub(r"synced_wording:\n(  .*\n)+", "", path.read_text(encoding="utf-8"))
            path.write_text(text, encoding="utf-8")
            wording_edit = run(
                EDIT, "--dir", str(rule_dir), "--set", "wording.human=Changed.", "001"
            )
            self.assertEqual(wording_edit[0], 0, wording_edit[1])
            code, out, _ = run(EDIT, "--dir", str(rule_dir), "--set", "audience=agent", "001")
            self.assertEqual(code, 0, out)

    def test_statement_change_without_review_flag_writes_nothing(self):
        with scratch() as d:
            rule_dir, path = make_rule(d)
            before = path.read_bytes()
            code, _out, err = run(
                EDIT,
                "--dir",
                str(rule_dir),
                "--set",
                "statement=Secrets MUST NOT appear in build logs.",
                "001",
            )
            self.assertEqual(code, 2)
            self.assertIn("--reviewed-wording", err)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
