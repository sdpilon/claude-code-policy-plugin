#!/usr/bin/env python3
"""Backs /policy:edit: change fields of one or more rules (FR-004..FR-009).

Every target is loaded and validated before any write. A rejected rule stops the whole run.
A changed rule gets a fresh `modified` and keeps its `synced_hash`, so it reads as changed in
sync_status until record_sync runs.
"""

import argparse
import copy
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
import policy_manifest as manifest

EDITABLE = {
    "title",
    "tags",
    "audience",
    "verification.method",
    "verification.via",
    "statement",
    "rationale",
}


def fail(message, code=2):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def split_document(text):
    """Return (frontmatter_block, rest). The block ends with its closing '---' line."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("unterminated frontmatter block") from None
    return "".join(lines[: end + 1]), "".join(lines[end + 1 :])


def set_statement(rest, rule_id, statement):
    prefix = f"**{rule_id}**: "
    lines = rest.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = prefix + statement + "\n"
            return "".join(lines)
    raise ValueError(f"no statement line starting with {prefix!r}")


def set_rationale(rest, rationale):
    lines = rest.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("Rationale:"):
            if rationale:
                lines[i] = f"Rationale: {rationale}\n"
            else:
                del lines[i]
            return "".join(lines)
    if rationale:
        return rest.rstrip("\n") + f"\n\nRationale: {rationale}\n"
    return rest


def apply_set(fields, rest, rule_id, key, value):
    """Return (fields, rest) with one --set applied. Raises ValueError for a bad value."""
    if key == "title":
        fields["title"] = value
    elif key == "tags":
        fields["tags"] = [t.strip() for t in value.split(",") if t.strip()]
    elif key == "audience":
        fields["audience"] = [a.strip() for a in value.split(",") if a.strip()]
    elif key in ("verification.method", "verification.via"):
        verification = dict(fields.get("verification") or {})
        verification[key.split(".", 1)[1]] = value
        fields["verification"] = verification
    elif key == "statement":
        problems = fm.validate_statement(value)
        if problems:
            raise ValueError("; ".join(problems))
        rest = set_statement(rest, rule_id, value.strip())
    elif key == "rationale":
        rest = set_rationale(rest, value.strip())
    return fields, rest


def edit_text(text, rule_id, sets):
    """Return (new_text, changed_fields). Pure: no I/O."""
    _front, rest = split_document(text)
    before_fields = fm.parse(text)
    fields = copy.deepcopy(before_fields)
    new_rest = rest
    for key, value in sets:
        fields, new_rest = apply_set(fields, new_rest, rule_id, key, value)
    if fields == before_fields and new_rest == rest:
        return text, []
    fields["modified"] = fm.now_utc()
    problems = fm.validate(fields)
    if problems:
        raise ValueError("; ".join(problems))
    # render() ends with the closing '---' line already; rest keeps the original blank line, if any.
    new_text = fm.render(fields).rstrip("\n") + "\n" + new_rest
    return new_text, [k for k, _ in sets]


def resolve(raw, rule_dir):
    if not raw.isdigit():
        fail(f"rule ID must be a number, got {raw!r}")
    path = rule_dir / f"{ids.format_id(int(raw))}.md"
    if not path.is_file():
        fail(f"no rule {raw} under {rule_dir}")
    return path


def parse_sets(raw_sets):
    sets = []
    for item in raw_sets:
        if "=" not in item:
            fail(f"--set expects field=value, got {item!r}")
        key, value = item.split("=", 1)
        if key not in EDITABLE:
            fail(f"field {key!r} is not editable; allowed: {', '.join(sorted(EDITABLE))}")
        sets.append((key, value))
    return sets


def main(argv):
    p = argparse.ArgumentParser(prog="edit_rule.py")
    p.add_argument("--dir", default=".policy/rule")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--set", dest="sets", action="append", default=[], metavar="FIELD=VALUE")
    p.add_argument("ids", nargs="+", metavar="ID")
    args = p.parse_args(argv)
    sets = parse_sets(args.sets)
    if not sets:
        fail("at least one --set is required")
    rule_dir = Path(args.dir)

    # Phase 1: load and validate every target. Nothing is written in this phase.
    plan = []
    rejected = []
    for raw in args.ids:
        path = resolve(raw, rule_dir)
        text = path.read_text(encoding="utf-8")
        try:
            new_text, _changed = edit_text(text, ids.format_id(int(raw)), sets)
        except ValueError as e:
            rejected.append((raw, str(e)))
            continue
        plan.append((raw, path, text, new_text))

    for raw, reason in rejected:
        print(f"rejected {raw}: {reason}")
    if rejected:
        return 2

    if args.preview:
        for raw, _path, text, new_text in plan:
            if new_text == text:
                print(f"unchanged {raw}")
                continue
            print(f"preview {raw}")
            for key, value in sets:
                print(f"  {key} -> {value}")
        return 0

    # Phase 2: write only the rules that changed.
    for raw, path, text, new_text in plan:
        if new_text == text:
            print(f"unchanged {raw}")
            continue
        try:
            manifest.atomic_write_bytes(path, new_text.encode("utf-8"))
        except OSError as e:
            print(f"error: writing rule {raw}: {e}", file=sys.stderr)
            return 1
        print(f"changed {raw}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
