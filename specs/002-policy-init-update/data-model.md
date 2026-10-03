# Data Model: Policy Init and Safe Update

## Manifest

The project's record of what the plugin wrote. Lives at `.policy/manifest.json`.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `format_version` | integer | yes | Manifest schema version. This feature writes `1`. |
| `plugin_version` | string | yes | Plugin version at the last write, read from `.claude-plugin/plugin.json`. |
| `files` | object | yes | Map from project-relative path to tracked entry. May be empty. |

## Tracked file entry

One entry per file the plugin wrote. Keyed by project-relative path (for example `.policy/README.md`).

| Field | Type | Required | Meaning |
|---|---|---|---|
| `shipped_version` | string | yes | Plugin version whose template was written to this file. |
| `sha256` | string (64 hex chars) | yes | SHA-256 of the file's content at write time, computed over LF-normalized UTF-8 bytes (research.md §2). |

## Shipped template

A file bundled in the plugin that init writes and update can rewrite. Currently one:

| Shipped path | Template source | Tracked |
|---|---|---|
| `.policy/README.md` | `templates/policy-readme.md` | yes |

Rule files (`.policy/rule/`), tombstones (`.policy/retired/`), and the manifest itself are never tracked.

## Classification states

Computed by `scripts/policy_manifest.py` for each tracked entry and each shipped template. These drive the update table in the spec.

| State | Condition | Update action | Counts as drift |
|---|---|---|---|
| `current` | Entry exists; file hash matches entry; shipped template unchanged | No-op | no |
| `stale` | Entry exists; file hash matches entry; shipped template differs | Overwrite with template; update entry | no |
| `customized` | Entry exists; file hash differs from entry | Leave file; report diff | yes |
| `missing` | Entry exists; file absent | Leave absent; report | yes |
| `no-longer-shipped` | Entry exists; no shipped template for path | Keep file; report | no |
| `new` | No entry; shipped template exists; file absent | Create file; add entry | no |
| `user-owned` | No entry; shipped template exists; file present | Leave file; report | no |

## Invariants

- A file is overwritten only in the `stale` state. Every other state leaves the file bytes unchanged.
- `files` keys are unique project-relative paths using forward slashes.
- After init, every entry's `sha256` equals the fingerprint of the file on disk.
- After a successful update, every `stale` entry is rewritten with the new `shipped_version` and fingerprint.
