# Contract: `sync_status.py` output (extended)

Invoked by `/policy:sync` step 1:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/scripts/sync_status.py --dir .policy/rule [--root <repo root>]
```

## New option

- `--root <path>`: directory that derived-doc paths resolve against. Default: `.`.

## Output

A JSON array, one row per rule, sorted by `id`. Existing fields are unchanged. New fields are `missing_wording` and `stale_in`.

```json
[
  {
    "id": 1,
    "audience": ["agent"],
    "targets": ["CLAUDE.md", ".claude/rules/001.md"],
    "current_hash": "45c8…",
    "synced_hash": "05f0…",
    "changed": true,
    "missing_wording": [],
    "stale_in": [
      {
        "path": "CONTRIBUTING.md",
        "audience": "human",
        "kind": "span",
        "text": "Secrets MUST NOT appear in CI logs.",
        "status": "found"
      }
    ]
  }
]
```

## Guarantees

- `stale_in` lists only audiences present in `synced_wording` and absent from `audience`.
- `status` is `found` only when the stored text, matched with whitespace normalization, occurs exactly once in the doc.
- A missing doc yields `status: "absent"` and never raises an error.
- `kind` is `"file"` only for `.claude/rules/<id>.md`, and `found` there requires the file content to equal the stored text plus a newline.
- `missing_wording` lists active audiences with no `wording` entry.
- The content hash ignores `synced_hash` and `synced_wording`, so recording does not make a rule read as changed.
- Output is deterministic for the same files.

## Error behavior

Unchanged. Malformed rules still produce a row with `error` and `changed: true`, and `stale_in` and `missing_wording` are `[]` for them.
