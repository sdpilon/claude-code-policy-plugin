#!/usr/bin/env python3
"""Deterministic inventory of a repo's rules for /policy:status and /policy:audit.

Reads rule files under .policy/rule/ (recursive), takes the enforcement tier from the
`verification` frontmatter field, and reports defects and ID gaps (FR-009, FR-010, FR-017).
Also includes a best-effort CI job inventory to help classify rules. Deliberately uses no
YAML parser beyond policy_frontmatter's restricted subset.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "scripts" / "policy_ids.py").exists()) / "scripts"))
import policy_frontmatter as fm  # noqa: E402
import policy_ids as ids  # noqa: E402

BOLD_ID_RE = re.compile(r"^\*\*(\d+)\*\*:\s*(.+)$")
JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*(#.*)?$")
STEP_NAME_RE = re.compile(r"^\s*-\s*name:\s*(.+?)\s*(#.*)?$")
CONTINUE_ON_ERROR_RE = re.compile(r"^\s*continue-on-error:\s*(['\"]?)true\1\s*(#.*)?$")
JOB_IF_RE = re.compile(r"^\s{4}if:\s*(.+?)\s*(#.*)?$")


def find_repo_root(start):
    d = Path(start).resolve()
    for candidate in [d, *d.parents]:
        if (candidate / ".policy").is_dir():
            return candidate
    return None


def extract_rules(root):
    rule_root = root / ".policy" / "rule"
    rules, seen = [], {}
    if not rule_root.is_dir():
        return rules, seen
    for path in sorted(rule_root.rglob("*.md")):
        rule_id = ids.parse_id(path.stem)
        if rule_id is None:
            continue
        text = path.read_text(encoding="utf-8")
        row = {"id": rule_id, "title": "", "statement": "", "tier": "unclassified", "via": None,
               "path": str(path.relative_to(root))}
        try:
            fields = fm.parse(text)
        except fm.FrontmatterError as e:
            row["defect"] = f"frontmatter: {e}"
            rules.append(row)
            seen[rule_id] = row
            continue
        row["title"] = fields.get("title", "") if isinstance(fields.get("title"), str) else ""
        audience = fields.get("audience")
        if not isinstance(audience, list) or not audience:
            row["defect"] = "audience missing"
        verification = fields.get("verification")
        if isinstance(verification, dict) and verification.get("method") in fm.METHODS:
            row["tier"] = verification["method"]
            row["via"] = verification.get("via") or None
        for line in text.splitlines():
            m = BOLD_ID_RE.match(line)
            if m:
                row["statement"] = m.group(2).strip()
                break
        rules.append(row)
        seen[rule_id] = row
    return rules, seen


def find_gaps(root, rule_ids):
    retired_root = root / ".policy" / "retired"
    retired_ids = set(ids._ids_in(retired_root, recursive=False)) if retired_root.is_dir() else set()
    present = set(rule_ids) | retired_ids
    if not present:
        return []
    return [n for n in range(1, max(present) + 1) if n not in present]


JOB_RE_ALL = JOB_RE


def introspect_ci(root):
    """Best-effort CI job inventory. Never authoritative; a line-based scan of GitHub Actions."""
    workflows_dir = root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    jobs = []
    for wf in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
        in_jobs, current = False, None
        for line in wf.read_text(encoding="utf-8").splitlines():
            if line.rstrip() == "jobs:":
                in_jobs = True
                continue
            if not in_jobs:
                continue
            jm = JOB_RE_ALL.match(line)
            if jm:
                current = {"workflow": wf.name, "job": jm.group(1), "blocking": True,
                           "condition": None, "steps": []}
                jobs.append(current)
                continue
            if current is None:
                continue
            if CONTINUE_ON_ERROR_RE.match(line):
                current["blocking"] = False
            ifm = JOB_IF_RE.match(line)
            if ifm:
                current["condition"] = ifm.group(1)
            sm = STEP_NAME_RE.match(line)
            if sm:
                current["steps"].append(sm.group(1).strip("'\""))
    return jobs


def main(argv):
    start = argv[0] if argv else "."
    root = find_repo_root(start)
    if root is None:
        print(f"ERROR: no .policy/ directory found from '{start}' upward", file=sys.stderr)
        return 1
    rules, seen = extract_rules(root)
    rules.sort(key=lambda r: r["id"])
    result = {
        "repo_root": str(root),
        "rules": rules,
        "gaps": find_gaps(root, seen.keys()),
        "ci_jobs": introspect_ci(root),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
