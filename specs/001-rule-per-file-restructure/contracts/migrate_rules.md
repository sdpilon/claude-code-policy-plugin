# Contract: `skills/migrate/scripts/migrate_rules.py`

Backs `/policy:migrate` (User Story 4). Performs the mechanical split only; never
decides how to handle a previously-shared rationale (FR-012) — it flags that case for
the skill to walk the user through afterward.

## CLI

```
python3 skills/migrate/scripts/migrate_rules.py \
  --source-dir .policy \
  --dest-dir .policy/rule \
  [--dry-run]
```

## Behavior

1. Reads every `<source-dir>/*.md` file (old topic-file format — flat, non-recursive,
   matching the convention being migrated away from).
2. For each bolded `**<PREFIX>-N**: <statement>` found, allocates a fresh ID via
   `scripts/policy_ids.py` scoped to `<dest-dir>`, and writes
   `<dest-dir>/<format_id(new_id)>.md` (zero-padded filename and bold-line token; see
   `policy_ids.md`), composing the new rule file as follows:
   - `title`: left blank (`""`) for a human to fill in — the script has no reliable way
     to invent a good short name from a MUST-statement.
   - `audience`: left as `[]` (invalid per the Rule schema) rather than guessing —
     forces a human decision on every migrated rule rather than defaulting silently.
   - `verification`: carried over if an old-style `<!-- tier: ...; via: ... -->`
     comment was present on or after that obligation's line; otherwise left absent.
   - rationale: carried over verbatim from the old file *only* when that rationale
     paragraph was not shared with any sibling obligation in the same section; when it
     was shared, the new file's rationale is left as `"TODO: see migration report"` and
     the mapping is recorded (see Output) instead of guessing a split.
3. Writes nothing when `--dry-run` is set; still produces the full report.

## Output

One JSON object on stdout:

```json
{
  "migrated": [
    {"source_file": ".policy/security.md", "source_id": "SEC-7", "new_id": 47, "shared_rationale_group": null},
    {"source_file": ".policy/security.md", "source_id": "SEC-8", "new_id": 48, "shared_rationale_group": "security.md#2"}
  ],
  "needs_review": [
    {"new_id": 47, "reason": "audience not set"},
    {"new_id": 48, "reason": "audience not set"},
    {"new_id": 48, "reason": "shared rationale — see group security.md#2"}
  ]
}
```

Every migrated rule appears in `needs_review` for `audience` at minimum (FR-012's
rationale-sharing flag is additional, not a replacement). `/policy:migrate` MUST
present `needs_review` to the user as the guided cleanup pass (Constitution Principle
III) rather than treating a successful mechanical split as the finished job.

## Errors

- `--source-dir` missing: exit `1`.
- A line matches the old ID pattern but the file has no detectable topic-level
  `##`-section boundaries (so rationale-sharing can't be determined): the rule is
  migrated, and `needs_review` gets an added `"reason": "could not determine section
  boundaries — check rationale manually"` entry rather than silently assuming no
  sharing.
