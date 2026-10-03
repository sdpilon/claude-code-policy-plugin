"""Shared, dependency-free rule ID allocation.

Rules live under `.policy/rule/` (recursive); tombstones under `.policy/retired/` (flat).
Tombstones count toward allocation, so a retired ID is never reissued (FR-004).
See specs/001-rule-per-file-restructure/contracts/policy_ids.md.
"""

import argparse
import json
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path

_DIGITS = re.compile(r"[0-9]+")


def format_id(n):
    """Zero-pad to a minimum of three digits. Grows past three digits without re-padding."""
    if n < 0:
        raise ValueError("rule IDs are non-negative")
    return f"{n:03d}"


def parse_id(stem):
    """Inverse of format_id. Returns None for anything that is not all decimal digits."""
    if not _DIGITS.fullmatch(stem):
        return None
    return int(stem)


def _ids_in(root, recursive):
    if not root.is_dir():
        return []
    paths = root.rglob("*.md") if recursive else root.glob("*.md")
    return [n for n in (parse_id(p.stem) for p in paths) if n is not None]


def highest_id(rule_root, retired_root):
    ids = _ids_in(Path(rule_root), recursive=True) + _ids_in(Path(retired_root), recursive=False)
    return max(ids, default=0)


def allocate_id(rule_root, retired_root, reserve: Callable[[int], bool], max_attempts=100):
    """Return the first free ID above the highest in use that `reserve` successfully claims.

    `reserve(n)` must atomically claim `n` (e.g. create its file with O_EXCL) and return True
    on success, False if it already exists. A retired ID is skipped before reserving.
    """
    retired_root = Path(retired_root)
    candidate = highest_id(rule_root, retired_root) + 1
    for _ in range(max_attempts):
        if (retired_root / f"{format_id(candidate)}.md").exists():
            candidate += 1
            continue
        if reserve(candidate):
            return candidate
        candidate += 1
    raise RuntimeError(f"could not reserve a rule ID after {max_attempts} attempts")


def reserve_file(target_dir):
    """Build a reserve() callback that claims `<target_dir>/<format_id(n)>.md` exclusively."""
    target_dir = Path(target_dir)

    def reserve(n):
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(target_dir / f"{format_id(n)}.md", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        os.close(fd)
        return True

    return reserve


def _cli(argv):
    parser = argparse.ArgumentParser(prog="policy_ids.py")
    sub = parser.add_subparsers(dest="command", required=True)
    h = sub.add_parser("highest")
    h.add_argument("--dir", default=".policy/rule")
    h.add_argument("--retired-dir", default=".policy/retired")
    args = parser.parse_args(argv)
    n = highest_id(args.dir, args.retired_dir)
    print(json.dumps({"highest": n, "highest_formatted": format_id(n)}))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
