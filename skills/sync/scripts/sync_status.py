#!/usr/bin/env python3
"""Backs /policy:sync: per-rule audience, derived targets, change detection, and stale text (FR-007, FR-008).

Content hash covers the rule file with its `synced_hash:` line and its `synced_wording:` block
removed, so writing either field after a successful sync does not itself make the rule look changed.

For each audience dropped since the last record, the wording last written to its derived doc
(`synced_wording`) is searched for in that doc. Matching is whitespace-normalized and must hit
exactly once to be a removal candidate (specs/005-sync-audience-removal/research.md R2).
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
SYNCED_WORDING_BLOCK = re.compile(r"^synced_wording:[^\n]*\n?(?:^  [^\n]*\n)*", re.MULTILINE)
WORD_SPLIT_RE = re.compile(r"[ \t\r\n]+")
AUDIENCE_ORDER = ("human", "agent")


def content_hash(text):
    stripped = SYNCED_WORDING_BLOCK.sub("", SYNCED_LINE.sub("", text))
    return hashlib.sha256(stripped.encode("utf-8")).hexdigest()


def targets_for(audience, rule_id):
    targets = []
    if "human" in audience:
        targets.append("CONTRIBUTING.md")
    if "agent" in audience:
        targets += ["CLAUDE.md", f".claude/rules/{ids.format_id(rule_id)}.md"]
    return targets


def stale_locations_for(audience, rule_id):
    """(path, kind) pairs where an audience's derived text lives."""
    locations = []
    if audience == "human":
        locations.append(("CONTRIBUTING.md", "span"))
    if audience == "agent":
        locations.append(("CLAUDE.md", "span"))
        locations.append((f".claude/rules/{ids.format_id(rule_id)}.md", "file"))
    return locations


def word_pattern(text):
    words = [w for w in WORD_SPLIT_RE.split(text) if w]
    return re.compile(WORD_SPLIT_RE.pattern.join(re.escape(w) for w in words))


def find_stale(root, rule_id, audience, text, reason):
    """Search every derived doc for one audience's recorded wording (dropped or reworded)."""
    results = []
    for rel_path, kind in stale_locations_for(audience, rule_id):
        entry = {
            "path": rel_path,
            "audience": audience,
            "kind": kind,
            "reason": reason,
            "text": text,
        }
        doc = root / rel_path
        if not doc.is_file():
            entry["status"] = "absent"
        elif kind == "file":
            content = doc.read_text(encoding="utf-8")
            entry["status"] = "found" if content == text + "\n" else "not_found"
        else:
            matches = list(word_pattern(text).finditer(doc.read_text(encoding="utf-8")))
            if len(matches) == 0:
                entry["status"] = "not_found"
            elif len(matches) > 1:
                entry["status"] = "ambiguous"
            else:
                entry["status"] = "found"
                entry["text"] = matches[0].group(0)
        results.append(entry)
    return results


def main(argv):
    p = argparse.ArgumentParser(prog="sync_status.py")
    p.add_argument("--dir", default=".policy/rule")
    p.add_argument("--root", default=".", help="directory derived-doc paths resolve against")
    args = p.parse_args(argv)
    root = Path(args.dir)
    doc_root = Path(args.root)
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
                    "missing_wording": [],
                    "stale_in": [],
                    "error": str(e),
                }
            )
            continue
        problems = fm.validate(fields)
        audience = fields.get("audience") if isinstance(fields.get("audience"), list) else []
        active = [a for a in audience if a in fm.AUDIENCES]
        wording = fields.get("wording") if isinstance(fields.get("wording"), dict) else {}
        synced_wording = (
            fields.get("synced_wording") if isinstance(fields.get("synced_wording"), dict) else {}
        )
        missing_wording = [a for a in active if a not in wording]
        stale_in = []
        for audience_key in AUDIENCE_ORDER:
            if audience_key not in synced_wording:
                continue
            if audience_key not in active:
                stale_in += find_stale(
                    doc_root, rule_id, audience_key, synced_wording[audience_key], "dropped"
                )
            elif audience_key in wording and wording[audience_key] != synced_wording[audience_key]:
                stale_in += find_stale(
                    doc_root, rule_id, audience_key, synced_wording[audience_key], "reworded"
                )
        row = {
            "id": rule_id,
            "audience": audience,
            "targets": targets_for(active, rule_id),
            "current_hash": content_hash(text),
            "synced_hash": fields.get("synced_hash"),
            "missing_wording": missing_wording,
            "stale_in": stale_in,
        }
        row["changed"] = (
            row["synced_hash"] is None
            or row["synced_hash"] != row["current_hash"]
            or bool(missing_wording)
            or bool(stale_in)
        )
        if problems:
            # A malformed rule gets no removal proposal (spec Edge Cases). Missing wording is still
            # reported, since that is the defect a person must fix (quickstart Scenario 6).
            row["changed"] = True
            row["error"] = "; ".join(problems)
            row["stale_in"] = []
        rows.append(row)

    rows.sort(key=lambda r: r["id"])
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
