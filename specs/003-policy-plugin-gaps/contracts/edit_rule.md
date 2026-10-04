# Contract: edit_rule.py

Backs the new `edit` skill (FR-004 to FR-009).

## Invocation

```text
python3 skills/edit/scripts/edit_rule.py [--dir .policy/rule] [--preview] \
    --set <field>=<value> [--set <field>=<value> ...] <ID> [<ID> ...]
```

- `<ID>`: one or more rule numbers. One ID is a single edit; several is a bulk edit.
- `--set`: repeatable. Allowed fields:
  - `title`: string
  - `tags`: comma-separated list
  - `audience`: comma-separated, each `human` or `agent`
  - `verification.method`: one of `ci-blocking`, `ci-checked`, `human-verified`, `written-only`
  - `verification.via`: string
  - `statement`: one sentence with exactly one modal verb
  - `rationale`: string
- `--preview`: print the before and after values for each rule and write nothing.

Any other field is rejected by name.

## Behavior

1. Parse and validate every target before writing anything.
   - Missing or unreadable ID: reject that rule.
   - Field invalid for the rule's current state, for example a `statement` with two modal
     verbs: reject that rule.
   - `fm.validate` on the resulting fields must pass.
2. If any rule is rejected, stop. Print each rejection and write nothing. Exit 2.
3. With `--preview`, print the per-rule before and after values and exit 0. Write nothing.
4. Otherwise, for each rule, set `modified` to `fm.now_utc()` and apply the change. Leave
   `created` and `synced_hash` as they are.
5. Write each file with `atomic_write_bytes`. If a write fails partway, restore the files
   already written from their in-memory originals and exit 1, reporting which were restored.

## Output

stdout, one line per rule: `changed <ID>`, `unchanged <ID>` (no field changed), or
`rejected <ID>: <reason>`. With `--preview`, the before and after lines for each changed field.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | every named rule was changed or unchanged; or a preview |
| 2 | at least one rule rejected; nothing written |
| 1 | an I/O failure during writes, or a rule that changed since it was read; restore attempted and reported. Also when another policy write holds the rule-directory lock for longer than the timeout: nothing is written. |

## Guarantees

- A rule with no changed field keeps its file byte-identical and its `modified` unchanged.
- A changed rule always has `modified` at or after the edit time.
- Derived docs are never read or written.
- After an edit, `synced_hash` no longer matches the content, so the rule shows as changed
  until `record_sync` runs.
