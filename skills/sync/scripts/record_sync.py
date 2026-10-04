#!/usr/bin/env python3
"""Backs /policy:sync's apply-and-record step: write each named rule's synced_hash and
synced_wording (FR-001..FR-004).

Writes only the synced_hash line and the synced_wording block in the frontmatter. The body and
every other field stay byte-identical. synced_wording holds the wording for the rule's current
audiences, so audiences dropped since the last record are pruned. Validates every ID before
writing anything, so a bad ID writes nothing.

A rule is refused, and nothing is written, while it still has an unapplied proposed change: a
pending addition, or a removal whose text is still found in its doc (FR-004, R14).
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
from sync_status import AUDIENCE_ORDER, build_row, content_hash, unapplied

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


def parse_expect(raw_items, ids_given):
    """Map rule ID to the hash it had when proposed. Each --expect must name a rule being recorded."""
    expected = {}
    for item in raw_items:
        raw_id, sep, digest = item.partition("=")
        if not sep or not raw_id.isdigit() or not digest:
            fail(f"--expect expects ID=HASH, got {item!r}")
        if raw_id not in ids_given:
            fail(f"--expect names rule {raw_id}, which is not being recorded")
        expected[int(raw_id)] = digest
    return expected


def describe(entry):
    if "reason" not in entry:
        return f"addition to {entry['path']}"
    return f"{entry['reason']} removal from {entry['path']}"


def main(argv):
    p = argparse.ArgumentParser(prog="record_sync.py")
    p.add_argument("--dir", default=".policy/rule")
    p.add_argument("--root", default=".", help="directory derived-doc paths resolve against")
    p.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="ID=HASH",
        help="content hash the rule had when it was proposed; recording is refused if it changed",
    )
    p.add_argument("ids", nargs="+", metavar="ID")
    args = p.parse_args(argv)
    rule_dir = Path(args.dir)
    doc_root = Path(args.root)
    expected = parse_expect(args.expect, args.ids)

    # Phase 1: resolve and compute every change before any write.
    plan = []
    for raw in args.ids:
        path = resolve(raw, rule_dir)
        current = path.read_text(encoding="utf-8")
        try:
            fields = fm.parse(current)
            digest = content_hash(current)
            updated = with_synced_hash(current, digest, synced_wording_for(fields))
        except (ValueError, fm.FrontmatterError) as e:
            fail(f"rule {raw}: {e}")
        if int(raw) in expected and expected[int(raw)] != digest:
            fail(
                f"rule {raw} changed since it was proposed; nothing was written. Re-run sync.",
                code=1,
            )
        outstanding = unapplied(build_row(current, int(raw), doc_root))
        if outstanding:
            listed = "; ".join(describe(e) for e in outstanding)
            fail(
                f"rule {raw} still has unapplied changes ({listed}); nothing was written. "
                "Apply them, or leave the rule out of this record.",
                code=1,
            )
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
