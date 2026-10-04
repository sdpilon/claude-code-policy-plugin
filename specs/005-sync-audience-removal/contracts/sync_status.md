# Contract: `sync_status.py` output (extended)

Invoked by `/policy:sync` step 1:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/scripts/sync_status.py --dir .policy/rule [--root <repo root>]
```

## New option

- `--root <path>`: directory that derived-doc paths resolve against. Default: `.`.

## Output

A JSON array, one row per rule, sorted by `id`. Existing fields are unchanged. New fields are `missing_wording`, `stale_in`, `pending`, and `held`. Each `stale_in` entry has a `reason`.

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
        "reason": "dropped",
        "text": "Secrets MUST NOT appear in CI logs.",
        "status": "found"
      }
    ]
  }
]
```

## Guarantees

- `stale_in` lists an audience when it is present in `synced_wording` and either:
  - absent from `audience` (`reason: "dropped"`), with `text` the recorded `synced_wording` entry; or
  - still in `audience`, with a `wording` entry that differs from its `synced_wording` entry (`reason: "reworded"`), with `text` the recorded entry.
- `status` is `found` only when the stored text, matched with whitespace normalization, occurs exactly once in the doc.
- A missing doc yields `status: "absent"` and never raises an error.
- `kind` is `"file"` only for `.claude/rules/<id>.md`, and `found` there requires the file content to equal the stored text plus a newline.
- `missing_wording` lists active audiences with no `wording` entry.
- `pending` lists each target whose current `wording` is not present in it (`kind` and `path` as in `stale_in`). A target whose wording is present exactly once is not listed. Additions are proposed only from `pending` (R15).
- A `reworded` stale entry with `status: "not_found"` is omitted from `stale_in` when the current `wording` for that audience is present exactly once in the same doc (R15).
- `held` lists each existing agent-only file `.claude/rules/<id>.md` whose content is neither the current `wording` plus a newline nor the last-written wording plus a newline (`path`, `audience`, `kind: "file"`). It is never proposed for overwrite and is reported by path and rule ID (FR-002, Assumptions).
- The content hash ignores `synced_hash` and `synced_wording`, so recording does not make a rule read as changed.
- A rule with `changed: true` because of `stale_in`, `missing_wording`, or `pending` is reported as changed, whether or not the stale text is found.
- Output is deterministic for the same files.

## Error behavior

Invalid rules still produce a row with `error` and `changed: true`, and `stale_in` is `[]` for them. A rule that cannot be parsed also has `missing_wording` set to `[]`. A rule that parses but fails validation, such as one with a missing wording entry, still reports `missing_wording` for each audience it lacks.
