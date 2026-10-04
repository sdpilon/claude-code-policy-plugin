#!/usr/bin/env python3
"""Backs the CI audit: run ci-checked checks from a consumer registry and file issues (FR-010..FR-016).

The plugin ships dispatch, dedupe, and filing only. The check implementations live in the
consumer's registry file (--registry), which must define CHECKS: dict[str, Callable[[], bool]].
"""

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
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
from github_tracker import GitHubTracker, TrackerError

LABEL_PREFIX = "policy-audit:"


class RegistryError(Exception):
    pass


class DryRunTracker:
    """Logs what would be filed. Searches nothing, creates nothing."""

    def find_open(self, label):
        return []

    def create(self, title, body, label):
        return f"(dry run) {title}"


def load_registry(path):
    path = Path(path)
    if not path.is_file():
        raise RegistryError(f"registry not found: {path}")
    spec = importlib.util.spec_from_file_location("policy_audit_registry", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise RegistryError(f"registry failed to import: {e}") from e
    checks = getattr(module, "CHECKS", None)
    if not isinstance(checks, dict):
        raise RegistryError("registry must define CHECKS as a dict of name to callable")
    return checks


def load_rules(policy_dir):
    """Return [(id, fields)] for ci-checked rules, sorted by ID. Unparseable files are reported."""
    rule_dir = Path(policy_dir) / "rule"
    rules = []
    if not rule_dir.is_dir():
        return rules
    for path in rule_dir.rglob("*.md"):
        rule_id = ids.parse_id(path.stem)
        if rule_id is None:
            continue
        try:
            fields = fm.parse(path.read_text(encoding="utf-8"))
        except fm.FrontmatterError as e:
            print(f"error: {path}: {e}", file=sys.stderr)
            continue
        verification = fields.get("verification") or {}
        if isinstance(verification, dict) and verification.get("method") == "ci-checked":
            rules.append((rule_id, fields))
    rules.sort(key=lambda r: r[0])
    return rules


def via_of(fields):
    verification = fields.get("verification") or {}
    return verification.get("via", "") if isinstance(verification, dict) else ""


def evaluate(via, checks):
    """Return ('pass'|'fail'|'unbuilt', detail) for one check name."""
    if via not in checks:
        return "unbuilt", None
    try:
        ok = bool(checks[via]())
    except Exception as e:  # noqa: BLE001 - a check that raises counts as failing (spec US4)
        return "fail", f"check raised {type(e).__name__}: {e}"
    return ("pass", None) if ok else ("fail", "check returned False")


def issue_text(kind, via, rule_ids, detail):
    rules = ", ".join(ids.format_id(r) for r in rule_ids)
    if kind == "unbuilt":
        title = f"Build policy check: {via}"
        body = (
            f"The ci-checked rules {rules} name the check `{via}`, which the registry does not define. "
            "Build the check, or change the rules' verification.via.\n"
        )
    else:
        title = f"Policy check failing: {via}"
        body = f"The check `{via}` failed for the rules {rules}. Detail: {detail}\n"
    body += f"\n<!-- policy-audit-key: {via} -->\n"
    return title, body


def run_audit(rules, checks, tracker, out=print):
    """Run every rule's check once per check name, file at most one issue per name. Returns exit code."""
    by_via = {}
    for rule_id, fields in rules:
        by_via.setdefault(via_of(fields), []).append(rule_id)

    verdicts = {}
    tracked = {}  # via -> issue URL, once known
    for rule_id, fields in rules:
        rid = ids.format_id(rule_id)
        if fields.get("defect"):
            out(f"skipped {rid} (defect)")
            continue
        via = via_of(fields)
        if not via:
            out(f"skipped {rid} (no verification.via)")
            continue

        if via not in verdicts:
            verdicts[via] = evaluate(via, checks)
        kind, detail = verdicts[via]
        if kind == "pass":
            out(f"pass {rid}")
            continue

        if via in tracked:
            out(f"skipped {rid} (tracked by {tracked[via]})")
            continue
        label = f"{LABEL_PREFIX}{via}"
        try:
            existing = tracker.find_open(label)
            if existing:
                tracked[via] = existing[0]["url"]
                out(f"skipped {rid} (already open: {tracked[via]})")
                continue
            title, body = issue_text(kind, via, by_via[via], detail)
            tracked[via] = tracker.create(title, body, label)
        except TrackerError as e:
            print(f"error: tracker: {e}", file=sys.stderr)
            return 1
        out(f"filed {rid} {tracked[via]}")
    return 0


def main(argv):
    p = argparse.ArgumentParser(prog="audit_checks.py")
    p.add_argument("--registry", required=True)
    p.add_argument("--policy-dir", default=".policy")
    p.add_argument("--tracker", choices=["github", "none"], default="github")
    args = p.parse_args(argv)

    try:
        checks = load_registry(args.registry)
    except RegistryError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    policy_dir = Path(args.policy_dir)
    if not policy_dir.is_dir():
        print(f"error: policy dir not found: {policy_dir}", file=sys.stderr)
        return 2

    tracker = GitHubTracker() if args.tracker == "github" else DryRunTracker()
    return run_audit(load_rules(policy_dir), checks, tracker)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
