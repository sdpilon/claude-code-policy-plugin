#!/usr/bin/env python3
"""Backs /policy:sync's apply-and-record step: write each named rule's synced_hash (FR-001..FR-003).

Writes only the synced_hash line in the frontmatter. The body and every other field stay
byte-identical. Validates every ID before writing anything, so a bad ID writes nothing.
"""

import argparse
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
import policy_ids as ids
import policy_lock
from sync_status import content_hash

LOCK_TIMEOUT = 10.0
ChangedDuringRecord = policy_lock.ChangedDuringWrite


def fail(message, code=2):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def with_synced_hash(text, digest):
    """Return text with its frontmatter synced_hash line set to digest, adding it if absent."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("unterminated frontmatter block") from None
    line = f"synced_hash: {digest}\n"
    for i in range(1, end):
        if lines[i].startswith("synced_hash:"):
            lines[i] = line
            return "".join(lines)
    lines.insert(end, line)
    return "".join(lines)


def resolve(raw, rule_dir):
    if not raw.isdigit():
        fail(f"rule ID must be a number, got {raw!r}")
    path = rule_dir / f"{ids.format_id(int(raw))}.md"
    if not path.is_file():
        fail(f"no rule {raw} under {rule_dir}")
    return path


def main(argv):
    p = argparse.ArgumentParser(prog="record_sync.py")
    p.add_argument("--dir", default=".policy/rule")
    p.add_argument("ids", nargs="+", metavar="ID")
    args = p.parse_args(argv)
    rule_dir = Path(args.dir)

    # Phase 1: resolve and compute every change before any write.
    plan = []
    for raw in args.ids:
        path = resolve(raw, rule_dir)
        current = path.read_text(encoding="utf-8")
        try:
            updated = with_synced_hash(current, content_hash(current))
        except ValueError as e:
            fail(f"rule {raw}: {e}")
        plan.append((raw, path, current, updated))

    # Phase 2: write only the rules that changed, under the rule-directory lock, and only if
    # each still matches what was read in phase 1.
    try:
        with policy_lock.write_lock(rule_dir, timeout=LOCK_TIMEOUT):
            for raw, path, current, updated in plan:
                if updated == current:
                    print(f"unchanged {raw}")
                    continue
                try:
                    write_if_unchanged(path, current, updated)
                except ChangedDuringRecord as e:
                    print(
                        f"error: rule {raw} changed while it was being recorded; re-run: {e}",
                        file=sys.stderr,
                    )
                    return 1
                except OSError as e:
                    print(f"error: writing rule {raw}: {e}", file=sys.stderr)
                    return 1
                print(f"recorded {raw}")
    except policy_lock.LockTimeout as e:
        print(
            f"error: another policy write holds the lock ({e}); nothing was written",
            file=sys.stderr,
        )
        return 1
    return 0


def write_if_unchanged(path, expected, updated):
    """Write updated only if the file still holds expected. Callers hold the write lock."""
    policy_lock.write_if_unchanged(path, expected, updated)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
