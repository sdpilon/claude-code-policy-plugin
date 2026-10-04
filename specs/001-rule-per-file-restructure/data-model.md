# Phase 1 Data Model: One-Rule-Per-File Restructuring

## Rule

A single committed, enforceable statement. One file = one rule.

**Location**: `.policy/rule/<id>.md`, optionally nested under organizational
subdirectories (`.policy/rule/<group>/<id>.md`). Nesting carries zero identity meaning.

**Filename**: the decimal integer ID, zero-padded to a minimum of three digits (e.g.
`047.md`), growing to additional digits once the value exceeds what three digits hold
(e.g. `1000.md`) — the same minimum-width-not-a-cap convention Spec Kit's own
`003-`-style feature directories use. No alphabetic prefix. Padding exists so a plain
directory listing sorts in numeric order; `id` itself (see below) stays a plain
integer everywhere else — padding is a filename/display concern only, applied by
`scripts/policy_ids.py`'s `format_id`, and reversed by its `parse_id`.

| Field | Location | Type | Required | Notes |
|---|---|---|---|---|
| `id` | derived from filename | integer | yes | Globally unique across the whole `.policy/rule/` tree. Permanent — never reused, even after deletion. Independent of directory placement. Held as a plain integer (not a padded string) everywhere except the filename and the bold statement line. |
| `title` | frontmatter | string | yes | Human name. Not an identifier — carries no uniqueness guarantee and nothing else may key off it. Free to change anytime. |
| `tags` | frontmatter | list of strings | no (default: empty) | Purely decorative. Never used for identity, lookup, directory placement, or ID allocation. |
| `created` | frontmatter | ISO 8601 timestamp | yes | Set once, at creation. |
| `modified` | frontmatter | ISO 8601 timestamp | yes | Updated whenever the rule's own content changes. |
| `audience` | frontmatter | list, subset of `{human, agent}` | yes, non-empty | Which derived document(s) this rule propagates into. `/policy:sync` reads this directly instead of inferring it. |
| `verification` | frontmatter | mapping `{method, via}` | yes | `method` ∈ `{ci-blocking, ci-checked, human-verified, written-only}`; `via` is a free-text note. Replaces the old inline `<!-- tier: ...; via: ... -->` comment. |
| `synced_hash` | frontmatter | string (sha256 hex) or absent | no | Content hash as of the last successful `/policy:sync`. Absent means "never synced." |
| statement | body | one sentence, bold, leading with the zero-padded ID | yes | `**047**: <subject> MUST/SHOULD/MUST NOT/MAY <requirement>.` No alpha prefix. |
| rationale | body | prose paragraph | yes | Self-contained; may end with `See also [048](048.md)[, [049](049.md)...]` links (zero-padded, matching the target's own filename) to related rules instead of restating shared context. |

**Validation rules**:

- `id` must be unique across the entire tree at the moment a new rule is written (FR-002,
  FR-003). Enforced by `scripts/policy_ids.py`'s allocate-and-recheck, not by convention.
- `audience` must be present and non-empty; a rule file missing it is a defect
  `/policy:status` surfaces, not silently treated as any particular audience (Edge Cases).
- `verification.method` must be one of the four enumerated values; an unrecognized or
  absent value is reported as `unclassified`, mirroring today's `policy_status.py`
  behavior for a missing tier annotation.
- Moving a rule's file between organizational subdirectories, or into/out of the flat
  root, must not change `id`, `title`, or any other field (FR-005).

**Lifecycle**: created by `/policy:add` or `/policy:migrate` → edited in place for
wording/metadata changes → retired via the retirement operation (FR-016), which removes
the rule file and writes its tombstone. Its ID is never reissued (FR-004). A rule removed
any other way leaves an ID gap that `/policy:status` reports (FR-017).

## Tombstone

A retired rule's permanent marker. Frontmatter only, no statement or rationale body.
Git history keeps the full retired content.

**Location**: `.policy/retired/<id>.md`. A sibling of `.policy/rule/`, so status, sync,
and audit never treat a tombstone as a live rule. ID allocation scans both directories.

| Field | Location | Type | Required | Notes |
|---|---|---|---|---|
| `id` | derived from filename | integer | yes | The retired rule's ID. Same formatting as rule filenames. |
| `title` | frontmatter | string | yes | Copied from the rule at retirement, for readable listings. |
| `retired` | frontmatter | ISO 8601 date | yes | When the rule was retired. |
| `reason` | frontmatter | string | yes | Why it was retired. Required, so the decision is never silent. |
| `superseded_by` | frontmatter | integer | no | ID of the rule that replaces it, if any. |

**Validation rules**: `id` must match the filename. Only one tombstone per ID may exist.

## Derived Document

A human-facing (e.g. `CONTRIBUTING.md`) or agent-operational (e.g. `CLAUDE.md` or a
`.claude/rules/*.md` file) document kept in sync with the subset of Rules whose
`audience` includes that document's audience.

| Field | Notes |
|---|---|
| audience | `human` or `agent` — which Rules it draws from. |
| content | Derived, not authored directly; `/policy:sync` proposes changes, a human approves them (Constitution Principle III). |

**Relationship**: many Rules → one or more Derived Documents, selected per-rule by
`audience`, not by directory or topic.

## Migration Mapping (transient — exists only during a `/policy:migrate` run)

Not a persisted entity; describes what `migrate_rules.py` produces as its report.

| Field | Notes |
|---|---|
| `source_file` | The old `.policy/<topic>.md` path an obligation came from. |
| `source_statement_id` | The old `<PREFIX>-N` token. |
| `new_rule_id` | The freshly allocated integer ID (plain integer; rendered zero-padded only in the new file's name and bold line). |
| `shared_rationale_group` | Set when this obligation's original rationale paragraph was shared with one or more sibling obligations in the same source section — signals the cleanup pass is needed (FR-012), never auto-resolved. |
