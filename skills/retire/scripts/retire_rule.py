#!/usr/bin/env python3
"""Backs /policy:retire: write a tombstone, then remove the rule file (FR-004, FR-016).

The tombstone is written first, so an interruption leaves a duplicate rather than an ID gap.
See contracts/retire_rule.md.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "scripts" / "policy_ids.py").exists()) / "scripts"))
import policy_frontmatter as fm  # noqa: E402
import policy_ids as ids  # noqa: E402


def fail(message, code):
    print(f"error: {message}", file=sys.stderr)
    return code


def main(argv):
    p = argparse.ArgumentParser(prog="retire_rule.py")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--superseded-by", type=int, default=None)
    p.add_argument("--rule-dir", default=".policy/rule")
    p.add_argument("--retired-dir", default=".policy/retired")
    args = p.parse_args(argv)

    if not args.reason.strip():
        return fail("--reason must be non-empty", 2)

    rule_dir, retired_dir = Path(args.rule_dir), Path(args.retired_dir)
    tombstone = retired_dir / f"{ids.format_id(args.id)}.md"

    matches = [path for path in rule_dir.rglob("*.md") if ids.parse_id(path.stem) == args.id] if rule_dir.is_dir() else []
    if not matches:
        return fail(f"no rule file for ID {ids.format_id(args.id)}", 1)
    rule_file = matches[0]
    if tombstone.exists():
        return fail(f"a tombstone already exists for ID {ids.format_id(args.id)}", 1)

    if args.superseded_by is not None:
        replacement = ids.format_id(args.superseded_by)
        found = any(ids.parse_id(p.stem) == args.superseded_by for p in rule_dir.rglob("*.md")) if rule_dir.is_dir() else False
        found = found or (retired_dir / f"{replacement}.md").exists()
        if not found:
            return fail(f"--superseded-by {replacement} names no rule or tombstone", 2)

    try:
        title = fm.read_file(rule_file).get("title", "")
    except fm.FrontmatterError as e:
        return fail(f"cannot read {rule_file}: {e}", 1)

    fields = {"title": title, "retired": fm.now_utc()[:10], "reason": args.reason.strip()}
    if args.superseded_by is not None:
        fields["superseded_by"] = str(args.superseded_by)
    problems = fm.validate_tombstone(fields)
    if problems:
        return fail("; ".join(problems), 2)

    retired_dir.mkdir(parents=True, exist_ok=True)
    tombstone.write_text(fm.render(fields) + "\n", encoding="utf-8")
    rule_file.unlink()

    print(json.dumps({"id": args.id, "tombstone": str(tombstone), "removed": str(rule_file)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
