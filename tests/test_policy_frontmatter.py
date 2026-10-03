import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import policy_frontmatter as fm  # noqa: E402

VALID = """---
title: "No secrets in CI logs"
tags: [security, ci]
created: 2026-10-02T00:00:00Z
modified: 2026-10-02T00:00:00Z
audience: [agent]
verification:
  method: ci-blocking
  via: "secret-scan job"
---

**047**: Secrets MUST NOT appear in CI logs.
"""


class ParseRenderTests(unittest.TestCase):
    def test_round_trip_preserves_key_order(self):
        fields = fm.parse(VALID)
        rendered = fm.render(fields)
        self.assertEqual(
            [line.split(":")[0] for line in rendered.splitlines()[1:-1] if not line.startswith("  ")],
            ["title", "tags", "created", "modified", "audience", "verification"],
        )
        self.assertEqual(fm.parse(rendered), fields)

    def test_parses_block_list_and_nested_mapping(self):
        text = "---\ntitle: t\ntags:\n- a\n- b\nverification:\n  method: written-only\n  via: x\n---\n"
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


if __name__ == "__main__":
    unittest.main()
