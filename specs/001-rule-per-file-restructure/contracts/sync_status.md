# Contract: `skills/sync/scripts/sync_status.py`

Backs `/policy:sync` (User Story 2). Pre-computes the mechanical part of sync — which
rules are unchanged since last sync, and which derived document(s) each rule targets —
so the skill's own judgment is spent only on *how* to word a derived document's update,
not on rediscovering *whether* one is needed.

## CLI

```
python3 skills/sync/scripts/sync_status.py --dir .policy/rule
```

## Output

```json
[
  {
    "id": 47,
    "audience": ["agent"],
    "targets": ["CLAUDE.md", ".claude/rules/047.md"],
    "current_hash": "ab12...",
    "synced_hash": "ab12...",
    "changed": false
  },
  {
    "id": 48,
    "audience": ["human", "agent"],
    "targets": ["CONTRIBUTING.md", "CLAUDE.md", ".claude/rules/048.md"],
    "current_hash": "cd34...",
    "synced_hash": null,
    "changed": true
  }
]
```

`targets` is derived mechanically from `audience` (`human` → `CONTRIBUTING.md`;
`agent` → `CLAUDE.md` and `.claude/rules/<id>.md`), so `/policy:sync` never infers the
target. `id` is a plain integer, as everywhere outside a rule's filename and bold-line token
(see `policy_ids.md`'s `format_id`/`parse_id`). `current_hash` is a sha256 of the rule
file's content with its `synced_hash:` line removed. Excluding that line keeps writing
the new `synced_hash` from making the rule look changed again. `changed` is
`current_hash != synced_hash` (a rule with no `synced_hash` yet is always `changed`).
`/policy:sync` MUST skip proposing an update for any rule where `changed` is `false`
(FR-008) and, after a propagation is approved and applied, write the new `synced_hash`
back into that rule's frontmatter via `scripts/policy_frontmatter.py`.

## Errors

- `--dir` does not exist: prints `[]`, exit `0` (nothing to sync is not an error).
- A rule file fails frontmatter validation (`policy_frontmatter.validate` returns
  errors): that rule is included in the output with `"changed": true` and an added
  `"error"` field — forcing it in front of a human rather than silently skipping a
  malformed rule.
