#!/usr/bin/env python3
"""Backs /policy:sync: per-rule audience, derived targets, and change detection (FR-007, FR-008).

Content hash covers the rule file with its `synced_hash:` line removed, so writing the new
synced_hash after a successful sync does not itself make the rule look changed.
"""

import argparse
import hashlib
import json
import re
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

SYNCED_LINE = re.compile(r"^synced_hash:.*\n?", re.MULTILINE)


def content_hash(text):
    return hashlib.sha256(SYNCED_LINE.sub("", text).encode("utf-8")).hexdigest()


def targets_for(audience, rule_id):
    targets = []
    if "human" in audience:
        targets.append("CONTRIBUTING.md")
    if "agent" in audience:
        targets += ["CLAUDE.md", f".claude/rules/{ids.format_id(rule_id)}.md"]
    return targets


def main(argv):
    p = argparse.ArgumentParser(prog="sync_status.py")
    p.add_argument("--dir", default=".policy/rule")
    args = p.parse_args(argv)
    root = Path(args.dir)
    if not root.is_dir():
        print("[]")
        return 0

    rows = []
    for path in root.rglob("*.md"):
        rule_id = ids.parse_id(path.stem)
        if rule_id is None:
            continue
        text = path.read_text(encoding="utf-8")
        try:
            fields = fm.parse(text)
        except fm.FrontmatterError as e:
            rows.append(
                {
                    "id": rule_id,
                    "audience": [],
                    "targets": [],
                    "current_hash": content_hash(text),
                    "synced_hash": None,
                    "changed": True,
                    "error": str(e),
                }
            )
            continue
        problems = fm.validate(fields)
        audience = fields.get("audience") if isinstance(fields.get("audience"), list) else []
        row = {
            "id": rule_id,
            "audience": audience,
            "targets": targets_for([a for a in audience if a in fm.AUDIENCES], rule_id),
            "current_hash": content_hash(text),
            "synced_hash": fields.get("synced_hash"),
        }
        row["changed"] = row["synced_hash"] is None or row["synced_hash"] != row["current_hash"]
        if problems:
            row["changed"] = True
            row["error"] = "; ".join(problems)
        rows.append(row)

    rows.sort(key=lambda r: r["id"])
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
