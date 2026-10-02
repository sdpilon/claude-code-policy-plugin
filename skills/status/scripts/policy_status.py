#!/usr/bin/env python3
"""Deterministically inventories a repo's .policy/*.md obligations and their
enforcement tier, so the policy-status skill doesn't have to re-derive this
by reading every policy file, every CI workflow, and cross-referencing them
by hand on every single invocation.

Tier is read from an inline annotation when present, on the obligation's own
line or the line immediately after it:

    <!-- tier: ci-blocking|ci-checked|human-verified|written-only; via: <note> -->

An obligation with no annotation is reported as "unclassified". The skill
should classify an unclassified obligation once -- with the same reasoning
it always used to do for every obligation on every run -- and then write the
annotation back into the policy file. From then on this script picks it up
instantly and the classification cost is never paid again for that
obligation, only for genuinely new or reworded ones.
"""

import json
import re
import sys
import pathlib

TIER_RE = re.compile(r"<!--\s*tier:\s*([a-z-]+)\s*;\s*via:\s*(.*?)\s*-->")
OBLIGATION_RE = re.compile(r"\*\*([A-Z][A-Z0-9]*-\d+)\*\*:\s*(.+)")


def find_repo_root(start: str) -> pathlib.Path | None:
    d = pathlib.Path(start).resolve()
    for candidate in [d, *d.parents]:
        if (candidate / ".policy").is_dir():
            return candidate
    return None


def extract_obligations(root: pathlib.Path) -> list[dict]:
    obligations = []
    for f in sorted((root / ".policy").glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            m = OBLIGATION_RE.search(lines[i])
            if not m:
                i += 1
                continue
            oid = m.group(1)
            statement_parts = [m.group(2).strip()]
            tier, via = "unclassified", None
            tm = TIER_RE.search(lines[i])
            if tm:
                tier, via = tm.group(1), tm.group(2)

            # A markdown obligation is one paragraph: consume wrapped
            # continuation lines until a blank line, a tier annotation
            # (which ends the paragraph), or the next obligation/heading.
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() == "":
                    break
                tm2 = TIER_RE.search(nxt)
                if tm2:
                    tier, via = tm2.group(1), tm2.group(2)
                    j += 1
                    break
                if OBLIGATION_RE.search(nxt) or nxt.lstrip().startswith("#"):
                    break
                statement_parts.append(nxt.strip())
                j += 1

            obligations.append(
                {
                    "id": oid,
                    "statement": " ".join(statement_parts),
                    "file": str(f.relative_to(root)),
                    "tier": tier,
                    "via": via,
                }
            )
            i = j
    return obligations


JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*(#.*)?$")
STEP_NAME_RE = re.compile(r"^\s*-\s*name:\s*(.+?)\s*(#.*)?$")
CONTINUE_ON_ERROR_RE = re.compile(r"^\s*continue-on-error:\s*(['\"]?)true\1\s*(#.*)?$")
JOB_IF_RE = re.compile(r"^\s{4}if:\s*(.+?)\s*(#.*)?$")


def introspect_ci(root: pathlib.Path):
    """Best-effort CI job inventory, to help a reviewer classify an
    unclassified obligation -- never authoritative, never a substitute for
    actually reading the workflow when it matters. Deliberately avoids a
    real YAML parser (and the PyYAML dependency that implies) in favor of a
    line-based scan tailored to GitHub Actions' typical flat job/step shape;
    anything more exotic (anchors, flow-style mappings) just won't be seen,
    the same way this script's obligation extraction only ever sees the
    `**ID**:` paragraph shape and nothing cleverer."""
    workflows_dir = root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []

    jobs = []
    for wf in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
        lines = wf.read_text(encoding="utf-8").splitlines()
        in_jobs = False
        current = None
        for line in lines:
            if line.rstrip() == "jobs:":
                in_jobs = True
                continue
            if not in_jobs:
                continue
            jm = JOB_RE.match(line)
            if jm:
                current = {
                    "workflow": wf.name,
                    "job": jm.group(1),
                    "blocking": True,
                    "condition": None,
                    "steps": [],
                }
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


def main() -> int:
    start = sys.argv[1] if len(sys.argv) > 1 else "."
    root = find_repo_root(start)
    if root is None:
        print(f"ERROR: no .policy/ directory found from '{start}' upward", file=sys.stderr)
        return 1

    result = {
        "repo_root": str(root),
        "obligations": extract_obligations(root),
        "ci_jobs": introspect_ci(root),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
