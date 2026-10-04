# Data Model: Sync Removal When Audience Drops a Target

The rule file gains two nested maps in frontmatter. The body is unchanged in shape.

## Rule

One file under `.policy/rule/`.

| Field | Location | Type | Required | Role |
|-------|----------|------|----------|------|
| `title`, `tags`, `created`, `modified` | frontmatter | as today | as today | unchanged |
| `audience` | frontmatter | list, subset of `{human, agent}` | yes, non-empty | Determines `targets` |
| `wording` | frontmatter | map: audience → one-sentence string | yes, one entry per audience in `audience` | Audience-specific prose propagated into derived docs |
| `verification` | frontmatter | nested map | yes | unchanged |
| `synced_hash` | frontmatter | hex | written by `record_sync` | Content hash, excluding `synced_hash` and `synced_wording` |
| `synced_wording` | frontmatter | map: audience → string | written by `record_sync` | Wording last written to each audience's derived doc |
| body statement | body | `**<id>**: <statement>` | yes | Formal one-sentence rule, read by `judge`, `audit`, `status` |
| `Rationale:` | body | optional | no | unchanged |

### Validation rules

- Every value in `wording` and `synced_wording` is a single line: `add` and `edit` collapse runs of whitespace, trim the ends, and store the result. No sentence-count or modal-verb check is applied; that judgment happens at `add`/`edit` approval.
- `wording` keys must equal the set of `audience` values. A missing key is a defect.
- `synced_wording` keys may be any subset of `{human, agent}`. Keys for audiences no longer in `audience` are stale until `record_sync` prunes them.
- Empty values are invalid in `wording`. In `synced_wording`, an absent key means nothing was written for that audience.

## Sync row (extended)

| Field | Type | Meaning |
|-------|------|---------|
| `id` | int | Rule ID (existing) |
| `audience` | list | Current audience (existing) |
| `targets` | list of paths | Derived docs for current audiences (existing) |
| `current_hash` | hex | Content hash, excluding `synced_hash` and `synced_wording` |
| `synced_hash` | hex or null | Recorded hash (existing) |
| `changed` | bool | Existing rule, unchanged |
| `error` | string | Present only for malformed rules (existing) |
| `missing_wording` | list of audiences | **New.** Active audiences with no `wording` entry. Empty when none. |
| `stale_in` | list of stale locations | **New.** Docs for audiences dropped since last record. Empty when none. |

### Stale location

| Field | Type | Meaning |
|-------|------|---------|
| `path` | string | `CONTRIBUTING.md` (human), `CLAUDE.md` (agent), or `.claude/rules/<id>.md` (agent) |
| `audience` | string | The dropped audience whose wording is searched for |
| `kind` | `"span"` or `"file"` | `span` for text inside a shared doc; `file` for the per-rule file |
| `text` | string | The stored `synced_wording` for that audience |
| `status` | `"found"`, `"not_found"`, `"ambiguous"`, `"absent"` | Result of the whitespace-normalized match |

Only `status: "found"` entries are removal candidates. The others are reported.

## State transitions

`synced` (hash and wording recorded, no stale locations) → audience or wording edited → `changed` → `add`/`edit` already wrote new `wording` → sync proposes writes for active audiences and removals for stale locations → approved and applied → `record_sync` writes `synced_wording` for active audiences and prunes dropped ones → `synced` again.

A declined removal keeps the rule `changed` and the stale location listed.
