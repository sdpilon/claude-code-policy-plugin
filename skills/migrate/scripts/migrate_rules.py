#!/usr/bin/env python3
"""Backs /policy:migrate: mechanically split old `.policy/<topic>.md` files into rule files.

Never resolves a shared rationale or a missing audience itself. It records them in
`needs_review` for a human (FR-011, FR-012). See contracts/migrate_rules.md.
"""

import argparse
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

OLD_ID_RE = re.compile(r"^\*\*([A-Z][A-Z0-9]*-\d+)\*\*:\s*(.+)$")
TIER_RE = re.compile(r"<!--\s*tier:\s*([a-z-]+)\s*;\s*via:\s*(.*?)\s*-->")


def sections(lines):
    """Yield (section_index, start, end) spans for each `## ` section; (0, 0, n) if none."""
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not starts:
        return None
    spans = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(lines)
        spans.append((k, s, e))
    return spans


def main(argv):
    p = argparse.ArgumentParser(prog="migrate_rules.py")
    p.add_argument("--source-dir", default=".policy")
    p.add_argument("--dest-dir", default=".policy/rule")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    source = Path(args.source_dir)
    if not source.is_dir():
        print(f"error: source directory {source} does not exist", file=sys.stderr)
        return 1
    dest = Path(args.dest_dir)
    retired = dest.parent / "retired"
    topic_files = sorted(f for f in source.glob("*.md"))

    migrated, needs_review = [], []
    dry_next = ids.highest_id(dest, retired) + 1

    for topic in topic_files:
        lines = topic.read_text(encoding="utf-8").splitlines()
        spans = sections(lines)
        if spans is None:
            spans = [(0, 0, len(lines))]
            section_known = False
        else:
            section_known = True

        for sec_idx, s, e in spans:
            block = lines[s:e]
            obligations = [(i, OLD_ID_RE.match(line)) for i, line in enumerate(block)]
            obligations = [(i, m) for i, m in obligations if m]
            if not obligations:
                continue
            rationale_lines = [line for line in block if line.startswith("Rationale:")]
            shared = len(obligations) > 1 and len(rationale_lines) == 1
            group = f"{topic.name}#{sec_idx}" if shared else None

            for k, (i, m) in enumerate(obligations):
                old_id, statement = m.group(1), m.group(2).strip()
                next_i = obligations[k + 1][0] if k + 1 < len(obligations) else len(block)
                tier, via = None, None
                for line in block[i:next_i]:
                    tm = TIER_RE.search(line)
                    if tm:
                        tier, via = tm.group(1), tm.group(2)
                        break

                if args.dry_run:
                    new_id = dry_next
                    dry_next += 1
                else:
                    dest.mkdir(parents=True, exist_ok=True)
                    new_id = ids.allocate_id(dest, retired, ids.reserve_file(dest))

                if shared:
                    rationale = "TODO: see migration report"
                elif rationale_lines:
                    rationale = rationale_lines[0][len("Rationale:") :].strip()
                else:
                    rationale = ""

                fields = {
                    "title": "",
                    "tags": [],
                    "created": fm.now_utc(),
                    "modified": fm.now_utc(),
                    "audience": [],
                }
                if tier:
                    fields["verification"] = {"method": tier, "via": via or ""}

                reasons = ["audience not set"]
                if group:
                    reasons.append(f"shared rationale — see group {group}")
                if not section_known:
                    reasons.append(
                        "could not determine section boundaries — check rationale manually"
                    )

                if not args.dry_run:
                    target = dest / f"{ids.format_id(new_id)}.md"
                    body = f"**{ids.format_id(new_id)}**: {statement}\n"
                    if rationale:
                        body += f"\nRationale: {rationale}\n"
                    target.write_text(fm.render(fields) + "\n" + body, encoding="utf-8")

                migrated.append(
                    {
                        "source_file": str(topic),
                        "source_id": old_id,
                        "new_id": new_id,
                        "shared_rationale_group": group,
                    }
                )
                for reason in reasons:
                    needs_review.append({"new_id": new_id, "reason": reason})

    print(json.dumps({"migrated": migrated, "needs_review": needs_review}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
