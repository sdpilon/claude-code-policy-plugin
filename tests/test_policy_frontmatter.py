import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import policy_frontmatter as fm

VALID = """---
title: "No secrets in CI logs"
tags: [security, ci]
created: 2026-10-02T00:00:00Z
modified: 2026-10-02T00:00:00Z
audience: [agent]
verification:
  method: ci-blocking
  via: "secret-scan job"
wording:
  agent: "Never print secrets to CI output."
---

**047**: Secrets MUST NOT appear in CI logs.
"""


class ParseRenderTests(unittest.TestCase):
    def test_round_trip_preserves_key_order(self):
        fields = fm.parse(VALID)
        rendered = fm.render(fields)
        self.assertEqual(
            [
                line.split(":")[0]
                for line in rendered.splitlines()[1:-1]
                if not line.startswith("  ")
            ],
            ["title", "tags", "created", "modified", "audience", "verification", "wording"],
        )
        self.assertEqual(fm.parse(rendered), fields)

    def test_parses_block_list_and_nested_mapping(self):
        text = (
            "---\ntitle: t\ntags:\n- a\n- b\nverification:\n  method: written-only\n  via: x\n---\n"
        )
        fields = fm.parse(text)
        self.assertEqual(fields["tags"], ["a", "b"])
        self.assertEqual(fields["verification"], {"method": "written-only", "via": "x"})

    def test_no_frontmatter_block_raises(self):
        with self.assertRaises(fm.FrontmatterError):
            fm.parse("**047**: no frontmatter here\n")

    def test_unsupported_syntax_raises_with_line_number(self):
        with self.assertRaises(fm.FrontmatterError) as ctx:
            fm.parse("---\ntitle: ok\n  stray indent\n---\n")
        self.assertEqual(ctx.exception.line, 3)


class ValidateTests(unittest.TestCase):
    def valid_fields(self):
        return fm.parse(VALID)

    def test_valid_rule_has_no_errors(self):
        self.assertEqual(fm.validate(self.valid_fields()), [])

    def test_missing_audience_fails(self):
        fields = self.valid_fields()
        del fields["audience"]
        self.assertTrue(any("audience" in e for e in fm.validate(fields)))

    def test_empty_audience_fails(self):
        fields = self.valid_fields()
        fields["audience"] = []
        self.assertTrue(any("audience" in e for e in fm.validate(fields)))

    def test_audience_outside_enum_fails(self):
        fields = self.valid_fields()
        fields["audience"] = ["robot"]
        self.assertTrue(any("human or agent" in e for e in fm.validate(fields)))

    def test_verification_method_outside_enum_fails(self):
        fields = self.valid_fields()
        fields["verification"]["method"] = "maybe"
        self.assertTrue(any("verification.method" in e for e in fm.validate(fields)))

    def test_tombstone_requires_reason(self):
        errors = fm.validate_tombstone({"title": "t", "retired": "2026-10-02", "reason": ""})
        self.assertTrue(any("reason" in e for e in errors))


class ValidateStatementTests(unittest.TestCase):
    def test_one_sentence_one_modal_is_valid(self):
        self.assertEqual(fm.validate_statement("Secrets MUST NOT appear in CI logs."), [])

    def test_each_modal_form_is_accepted(self):
        for text in ("Builds MUST pass.", "Builds SHOULD pass.", "Builds MAY skip lint."):
            with self.subTest(text=text):
                self.assertEqual(fm.validate_statement(text), [])

    def test_two_modal_verbs_fail(self):
        problems = fm.validate_statement("Builds MUST pass and MAY skip lint.")
        self.assertTrue(any("modal" in p for p in problems))

    def test_no_modal_verb_fails(self):
        problems = fm.validate_statement("Builds pass.")
        self.assertTrue(any("modal" in p for p in problems))

    def test_two_sentences_fail(self):
        problems = fm.validate_statement("Builds MUST pass. Releases MUST be tagged.")
        self.assertTrue(any("one sentence" in p for p in problems))

    def test_empty_statement_fails(self):
        self.assertTrue(fm.validate_statement("   "))


class WordingTests(unittest.TestCase):
    def fields(self):
        return fm.parse(VALID)

    def test_normalize_collapses_runs_and_trims(self):
        self.assertEqual(
            fm.normalize_wording("  Secrets\tMUST\n\nnot   leak. \r\n"), "Secrets MUST not leak."
        )

    def test_normalize_keeps_single_spaces_and_punctuation(self):
        self.assertEqual(fm.normalize_wording("a: b, c."), "a: b, c.")

    def test_normalize_of_only_whitespace_is_empty(self):
        self.assertEqual(fm.normalize_wording(" \t\n "), "")

    def test_valid_fields_pass(self):
        self.assertEqual(fm.validate(self.fields()), [])

    def test_missing_wording_fails(self):
        fields = self.fields()
        del fields["wording"]
        self.assertTrue(any("wording is required" in e for e in fm.validate(fields)))

    def test_wording_keys_must_match_audience(self):
        fields = self.fields()
        fields["audience"] = ["human", "agent"]
        problems = fm.validate(fields)
        self.assertTrue(any("no entry for audience ['human']" in e for e in problems))

    def test_wording_for_audience_not_in_rule_fails(self):
        fields = self.fields()
        fields["wording"] = {"agent": "Use it.", "human": "Use it."}
        self.assertTrue(any("not in audience" in e for e in fm.validate(fields)))

    def test_newline_in_wording_value_fails(self):
        fields = self.fields()
        fields["wording"] = {"agent": "Line one\nline two"}
        self.assertTrue(any("single line" in e for e in fm.validate(fields)))

    def test_empty_wording_value_fails(self):
        fields = self.fields()
        fields["wording"] = {"agent": "  "}
        self.assertTrue(any("non-empty" in e for e in fm.validate(fields)))

    def test_synced_wording_key_outside_enum_fails(self):
        fields = self.fields()
        fields["synced_wording"] = {"robot": "Beep."}
        self.assertTrue(any("synced_wording keys" in e for e in fm.validate(fields)))

    def test_synced_wording_subset_of_audiences_passes(self):
        fields = self.fields()
        fields["synced_wording"] = {"agent": "Never print secrets to CI output."}
        self.assertEqual(fm.validate(fields), [])


if __name__ == "__main__":
    unittest.main()
