# Contract: `scripts/policy_ids.py`

Shared, dependency-free ID allocation. Used as a library by `add_rule.py` and
`migrate_rules.py`; also runnable directly for inspection.

## Library API

- `highest_id(tree_root: Path) -> int` — recursively scans `<tree_root>/**/*.md` for
  filenames that parse as an integer via `parse_id` (zero-padded or not — parsing
  tolerates either); returns the highest found, or `0` if none exist.
- `format_id(n: int) -> str` — renders `n` zero-padded to a minimum of three digits
  (`47 -> "047"`), growing to more digits once `n` exceeds what three digits hold
  (`1000 -> "1000"`, never truncated or re-padded to four). The single source of truth
  for what a rule's filename and bold-line token look like; `add_rule.py`,
  `migrate_rules.py`, and `policy_status.py` all call this rather than formatting an ID
  themselves.
- `parse_id(filename_stem: str) -> int | None` — the inverse of `format_id`: `int()` on
  a stem that is all decimal digits (leading zeros tolerated, e.g. `"047"` and `"47"`
  both parse to `47`), `None` for anything else (so a non-rule file sitting in the tree
  is silently skipped rather than crashing the scan).
- `allocate_id(tree_root: Path, reserve: Callable[[int], bool]) -> int` — computes
  `highest_id(tree_root) + 1`, calls `reserve(candidate)` (expected to atomically claim
  the ID, e.g. by creating `<tree_root>/<format_id(candidate)>.md` with `O_EXCL`
  semantics and returning whether that succeeded), and retries with the next integer on
  failure. Raises if no ID can be reserved after a bounded number of retries (defends
  against a reservation function that always fails, not against unbounded contention).

## CLI (debugging / ad hoc use)

```
python3 scripts/policy_ids.py highest --dir .policy/rule
```

Output (stdout, JSON, one line): `{"highest": 46, "highest_formatted": "046"}`

Exit codes: `0` success. `1` the given `--dir` does not exist (reported as
`{"highest": 0, "highest_formatted": "000"}` on stdout first, per `highest_id`'s "no
rules yet" behavior — this is not an error case).

The CLI does not expose `allocate_id` directly, since allocation is only meaningful
paired with an actual file-write; `add_rule.py` and `migrate_rules.py` are the real
entry points for that.
