#!/usr/bin/env python3
"""Backs /policy:sync's apply-and-record step: write each named rule's synced_hash and
synced_wording (FR-001..FR-004).

Writes only the synced_hash line and the synced_wording block in the frontmatter. The body and
every other field stay byte-identical. synced_wording holds the wording for the rule's current
audiences, so audiences dropped since the last record are pruned. Validates every ID before
writing anything, so a bad ID writes nothing.
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
import policy_frontmatter as fm
import policy_ids as ids
import policy_lock
from sync_status import AUDIENCE_ORDER, content_hash

LOCK_TIMEOUT = 10.0
ChangedDuringRecord = policy_lock.ChangedDuringWrite


def fail(message, code=2):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def synced_wording_for(fields):
    """The wording for the rule's current audiences, as written to derived docs. None when empty."""
    audience = fields.get("audience") if isinstance(fields.get("audience"), list) else []
    wording = fields.get("wording") if isinstance(fields.get("wording"), dict) else {}
    current = {a: wording[a] for a in AUDIENCE_ORDER if a in audience and a in wording}
    return current or None


def with_synced_hash(text, digest, synced_wording=None):
    """Return text with synced_hash set to digest and the synced_wording block set to synced_wording.

    An existing line or block is replaced in place, and a missing one is added before the closing
    '---'. A synced_wording of None removes the block.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("unterminated frontmatter block") from None
    block = []
    if synced_wording:
        ordered = {a: synced_wording[a] for a in AUDIENCE_ORDER if a in synced_wording}
        block = fm.render({"synced_wording": ordered}).splitlines(keepends=True)[1:-1]
    hash_line = f"synced_hash: {digest}\n"

    out = []
    placed_hash = placed_wording = False
    i = 1
    while i < end:
        line = lines[i]
        if line.startswith("synced_hash:"):
            out.append(hash_line)
            placed_hash = True
            i += 1
        elif line.startswith("synced_wording:"):
            i += 1
            while i < end and lines[i].startswith("  "):
                i += 1
            out += block
            placed_wording = True
        else:
            out.append(line)
            i += 1
    if not placed_hash:
        out.append(hash_line)
    if not placed_wording:
        out += block
    return "".join([lines[0], *out, *lines[end:]])


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
            fields = fm.parse(current)
            updated = with_synced_hash(current, content_hash(current), synced_wording_for(fields))
        except (ValueError, fm.FrontmatterError) as e:
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
