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
- `edit` rejects an audience removal when `wording.<audience>` differs from a recorded `synced_wording.<audience>` (FR-012). The check runs before the `wording` key is dropped.
- `edit` rejects a statement change without the review flag (FR-009).

## Sync row (extended)

| Field | Type | Meaning |
|-------|------|---------|
| `id` | int | Rule ID (existing) |
| `audience` | list | Current audience (existing) |
| `targets` | list of paths | Derived docs for current audiences (existing) |
| `current_hash` | hex | Content hash, excluding `synced_hash` and `synced_wording` |
| `synced_hash` | hex or null | Recorded hash (existing) |
| `changed` | bool | True when the hash differs, the rule is invalid, or `missing_wording`, `stale_in`, or `pending` is non-empty |
| `error` | string | Present only for invalid or unparseable rules (existing) |
| `missing_wording` | list of audiences | **New.** Active audiences with no `wording` entry. Empty when none. |
| `stale_in` | list of stale locations | **New.** Locations for audiences dropped since the last record, or reworded while still targeted. Empty when none, and always empty for an invalid rule. |
| `pending` | list of targets | **New.** Targets whose current `wording` is not already in place, so an addition is proposed. Empty when none, and always empty for an invalid rule. |
| `held` | list of targets | **New.** Existing agent-only files whose content is neither the current nor the last-written wording plus a newline. Reported, never overwritten. Empty when none, and always empty for an invalid rule. |

### Stale location

| Field | Type | Meaning |
|-------|------|---------|
| `path` | string | `CONTRIBUTING.md` (human), `CLAUDE.md` (agent), or `.claude/rules/<id>.md` (agent) |
| `audience` | string | The audience whose recorded wording is searched for |
| `kind` | `"span"` or `"file"` | `span` for text inside a shared doc; `file` for the per-rule file |
| `reason` | `"dropped"` or `"reworded"` | `dropped`: the audience left `audience`. `reworded`: the audience is still targeted and its `wording` differs from `synced_wording` |
| `text` | string | The matched span in the doc when `found` (the exact bytes a removal deletes); otherwise the recorded `synced_wording` entry for that audience |
| `status` | `"found"`, `"not_found"`, `"ambiguous"`, `"absent"` | Result of the whitespace-normalized match |

Only `status: "found"` entries are removal candidates. The others are reported.

## Proposal pairing (sync skill, not stored)

- A `dropped` removal is proposed alone. Its `targets` no longer include that audience.
- A `reworded` removal is proposed together with an addition of the current `wording` for the same audience to the same doc (FR-002). For `kind: "file"`, the addition overwrites the file (R12).

## State transitions

`synced` (hash and wording recorded, no stale locations) → audience dropped, or wording edited for a still-targeted audience → `changed` → `add`/`edit` already wrote new `wording` → sync proposes removals for `dropped` and `reworded` stale locations, and additions from `pending` (paired with `reworded` removals) → every change proposed for the rule approved and applied → `record_sync` writes `synced_wording` for active audiences and prunes dropped ones → `synced` again. If any change for the rule was declined or failed, the rule is not recorded and stays `changed` (FR-004).

An audience dropped while its wording has an unrecorded edit does not reach this flow: `edit` rejects it (FR-012). The person records the wording change first, then drops the audience.

A declined removal keeps the rule `changed` and the stale location listed.
