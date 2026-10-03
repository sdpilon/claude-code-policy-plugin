#!/usr/bin/env python3
"""Backs /policy:add: allocate the next rule ID and write the rule file (FR-001..FR-003)."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "scripts" / "policy_ids.py").exists()) / "scripts"))
import policy_frontmatter as fm  # noqa: E402
import policy_ids as ids  # noqa: E402

METHODS = sorted(fm.METHODS)


def fail(message, code=2):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


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
    args = p.parse_args(argv)

    audience = [a.strip() for a in args.audience.split(",") if a.strip()]
    if not audience or any(a not in fm.AUDIENCES for a in audience):
        fail("--audience must be one or more of: human, agent")
    if args.verification_method not in fm.METHODS:
        fail(f"--verification-method must be one of: {', '.join(METHODS)}")
    if not args.title.strip() or not args.statement.strip():
        fail("--title and --statement must be non-empty")

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
