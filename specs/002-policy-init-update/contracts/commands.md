# Contract: `/policy:init` and `/policy:update`

Both commands run from the repository root and take no arguments. Each is a skill that invokes a
script; the script is the source of truth for behavior and exit codes.

## `/policy:init`

**Script**: `skills/init/scripts/init_policy.py`

**Effect**:

| Project state | Action | Output | Exit |
|---|---|---|---|
| No `.policy/` | Create `rule/`, `retired/`, write `README.md` from template, write manifest | `created: .policy/README.md`, `created: .policy/manifest.json` | `0` |
| Manifest present | Nothing | `already initialized: .policy/manifest.json` | `0` |
| `.policy/README.md` present, no manifest | Create `rule/`, `retired/`, write manifest; `README.md` left unchanged and untracked | `user-owned: .policy/README.md (not tracked)` | `0` |

Init never modifies an existing file (FR-002).

## `/policy:update`

**Script**: `skills/update/scripts/update_policy.py`

**Output**: One line per tracked or shipped path, grouped by state, then a summary line.

```text
updated:        .policy/README.md  (0.1.0 -> 0.2.0)
current:        (none)
customized:     .policy/README.md  (see diff below)
missing:        (none)
no-longer-shipped: (none)
user-owned:     (none)

--- diff .policy/README.md (project -> shipped 0.2.0)
...unified diff...

summary: 1 updated, 1 customized
```

Diff blocks appear only for `customized` files.

**Exit codes**:

| Code | Meaning |
|---|---|
| `0` | No `customized` or `missing` files after the run |
| `1` | At least one `customized` or `missing` file |
| `2` | Manifest missing, corrupt, or unsupported (no files changed) |

`no-longer-shipped` and `user-owned` never affect the exit code (FR-012).

**Guarantees**:

- Only `stale` entries are overwritten (see `data-model.md` invariants).
- Writes are atomic per file.
- Running twice in a row with no plugin change produces no writes and reports nothing as `updated` (edge case in the spec).
