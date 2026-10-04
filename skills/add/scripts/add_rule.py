#!/usr/bin/env python3
"""Backs /policy:add: allocate the next rule ID and write the rule file (FR-001..FR-003)."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        next(
            p
            for p in Path(__file__).resolve().parents
            if (p / "scripts" / "policy_ids.py").exists()
        )
        / "scripts"
    ),
)
import policy_frontmatter as fm
import policy_ids as ids

METHODS = sorted(fm.METHODS)


def fail(message, code=2):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def parse_wording(raw_items, audience):
    """Map each audience to its normalized wording. Exactly one wording per audience is required."""
    wording = {}
    for item in raw_items:
        if "=" not in item:
            fail(f"--wording expects AUDIENCE=TEXT, got {item!r}")
        key, text = item.split("=", 1)
        key = key.strip()
        if key not in audience:
            fail(f"--wording audience {key!r} is not in --audience")
        if key in wording:
            fail(f"--wording given more than once for {key!r}")
        normalized = fm.normalize_wording(text)
        if not normalized:
            fail(f"--wording for {key!r} is empty")
        wording[key] = normalized
    missing = [a for a in audience if a not in wording]
    if missing:
        fail(f"--wording is required for each audience; missing {', '.join(missing)}")
    return {a: wording[a] for a in audience}


def main(argv):
    p = argparse.ArgumentParser(prog="add_rule.py")
    p.add_argument("--statement", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--audience", required=True)
    p.add_argument("--verification-method", required=True)
    p.add_argument("--verification-via", default="")
    p.add_argument("--tags", default="")
    p.add_argument("--dir", default="", help="optional subdirectory under the rule tree")
    p.add_argument("--policy-dir", default=".policy")
    p.add_argument("--rationale", default="")
    p.add_argument(
        "--wording",
        action="append",
        default=[],
        metavar="AUDIENCE=TEXT",
        help="one-sentence wording for an audience; repeat once per audience in --audience",
    )
    args = p.parse_args(argv)

    audience = [a.strip() for a in args.audience.split(",") if a.strip()]
    if not audience or any(a not in fm.AUDIENCES for a in audience):
        fail("--audience must be one or more of: human, agent")
    if args.verification_method not in fm.METHODS:
        fail(f"--verification-method must be one of: {', '.join(METHODS)}")
    if not args.title.strip() or not args.statement.strip():
        fail("--title and --statement must be non-empty")
    statement_problems = fm.validate_statement(args.statement)
    if statement_problems:
        fail("; ".join(statement_problems))
    wording = parse_wording(args.wording, audience)

    policy_dir = Path(args.policy_dir)
    rule_root = policy_dir / "rule"
    retired_root = policy_dir / "retired"
    target_dir = rule_root / args.dir if args.dir else rule_root

    now = fm.now_utc()
    fields = {
        "title": args.title,
        "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
        "created": now,
        "modified": now,
        "audience": audience,
        "verification": {"method": args.verification_method, "via": args.verification_via},
        "wording": wording,
    }

    try:
        new_id = ids.allocate_id(rule_root, retired_root, ids.reserve_file(target_dir))
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    path = target_dir / f"{ids.format_id(new_id)}.md"
    body = f"**{ids.format_id(new_id)}**: {args.statement.strip()}\n"
    if args.rationale.strip():
        body += f"\nRationale: {args.rationale.strip()}\n"
    problems = fm.validate(fields)
    if problems:
        path.unlink()
        fail("; ".join(problems))
    path.write_text(fm.render(fields) + "\n" + body, encoding="utf-8")

    print(json.dumps({"id": new_id, "path": str(path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
