# Data Model: Policy Plugin Gaps

No new storage. The rule file format is unchanged except for the `modified` and
`synced_hash` values, which the new commands write.

## Rule (existing, `.policy/rule/<id>.md`)

Frontmatter fields:

| Field | Type | Written by |
|---|---|---|
| `title` | string | `add`, `edit` |
| `tags` | list of strings | `add`, `edit` |
| `created` | UTC timestamp | `add` (never changed) |
| `modified` | UTC timestamp | `add`, `edit` (set to now on every changed rule) |
| `audience` | list, subset of `human`, `agent` | `add`, `edit` |
| `verification.method` | one of `ci-blocking`, `ci-checked`, `human-verified`, `written-only` | `add`, `edit` |
| `verification.via` | string, intended check name | `add`, `edit` |
| `synced_hash` | sha256 hex, optional | `record_sync` only |

Body: one line `**NNN**: <statement>` plus an optional rationale. `statement` must be one
sentence with exactly one modal verb (MUST, SHOULD, MUST NOT, MAY).

**Invariant**: `synced_hash` equals `content_hash(file)` after `record_sync` runs, where
`content_hash` ignores the `synced_hash` line. An edit changes the content hash, so the rule
reads as changed until the next `record_sync`.

## Sync record

The `synced_hash` field on a rule. States: absent (never synced, always "changed"), matches
current content (in sync), differs from current content (changed since last sync).

## Edit change set

A proposed edit to one or more rules.

| Field | Meaning |
|---|---|
| `ids` | one or more rule IDs, each must exist under `.policy/rule/` |
| `set` | map of field path to new value. Allowed paths: `title`, `tags`, `audience`, `verification.method`, `verification.via`, `statement`, `rationale` |
| `preview` | boolean. When true, print the before and after values and write nothing |

Result per rule: `changed`, `unchanged`, or `rejected` with a reason. A run is all-or-none:
any `rejected` stops the run before any write.

## Check registry (consumer-supplied)

A Python module exporting `CHECKS: dict[str, Callable[[], bool]]`. Keys are check names,
matched against `verification.via`. A check returns True when it passes.

## Audit issue

Keyed by `verification.via`.

| Field | Value |
|---|---|
| label | `policy-audit:<via>` (the search key) |
| title | `Policy check failing: <via>` or `Build policy check: <via>` |
| body | rule IDs and titles that depend on the check, plus the hidden marker `<!-- policy-audit-key: <via> -->` |
| state | open. The audit never closes an issue (FR-016). |

Per-rule log line, one per `ci-checked` rule: `pass`, `filed <issue>`, `skipped (already open)`,
`skipped (defect)`, or `skipped (no check)` when the check is absent and an issue was filed
for it (`filed`). An unverifiable rule never fails the build.

## State transitions

- Rule: `added` → `edited` (modified updated, hash stale) → `synced` (`record_sync`) → `edited` …
- Rule: `retired` via the retire skill (not changed by this feature).
- Audit issue: `filed` (open) → stays open until a human closes it. The audit does not transition it.
