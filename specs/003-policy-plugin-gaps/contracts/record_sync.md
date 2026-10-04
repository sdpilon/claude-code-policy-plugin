# Contract: record_sync.py

Backs the sync skill's apply-and-record step (FR-001 to FR-003, FR-019).

## Invocation

```text
python3 skills/sync/scripts/record_sync.py [--dir .policy/rule] <ID> [<ID> ...]
```

- `<ID>`: a rule number as written in the filename, for example `004`. One or more.
- `--dir`: rule directory, default `.policy/rule`.

## Behavior

1. Validate every ID exists as `<dir>/<ID>.md`. Any missing ID fails the whole run with no write.
2. For each rule, compute `content_hash(text)` from `skills/sync/scripts/sync_status.py`.
3. If the stored `synced_hash` already equals that hash, leave the file byte-identical.
4. Otherwise set the `synced_hash` line and write the file with `atomic_write_bytes`.
5. Print one line per rule: `recorded <ID>`, `unchanged <ID>`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | every named rule is now recorded or was already recorded |
| 2 | an ID is missing or malformed; nothing was written |
| 1 | an unexpected I/O error; files already written stay written (each write is atomic) |

## Output

stdout: one line per rule. stderr: errors only, prefixed `error:`.

## Guarantees

- Running it twice in a row writes nothing the second time.
- A rule's body and other frontmatter fields are unchanged, byte for byte.
- It never reads or writes derived docs (`CONTRIBUTING.md`, `CLAUDE.md`, `.claude/rules/`).
