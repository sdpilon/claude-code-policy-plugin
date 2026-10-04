# Implementation Plan: Sync Removal When Audience Drops a Target

**Branch**: `005-sync-audience-removal` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-sync-audience-removal/spec.md`

## Summary

Each rule stores its wording per audience in its own file, and sync writes that exact wording
into the matching derived doc. Sync also records the wording it last wrote, per audience, in the
rule's frontmatter. When an audience drops a target, sync finds the last-written wording by exact
text match in the no-longer-targeted doc and proposes removing it. Detection is a script; the
agent only drafts wording at `add`/`edit` time and drafts proposal text at sync time. Hand-edited
text that no longer matches is reported, never removed.

## Technical Context

**Language/Version**: Python 3 (stdlib only, matching the existing scripts)

**Primary Dependencies**: None beyond the standard library and the existing `scripts/` helpers (`policy_ids`, `policy_frontmatter`, `policy_lock`, `policy_manifest`)

**Storage**: `.policy/rule/*.md` (source, now with per-audience wording and last-written wording in frontmatter) and derived docs `CONTRIBUTING.md`, `CLAUDE.md`, `.claude/rules/<id>.md` (outputs)

**Testing**: `unittest` through `tests/_cli.py`; `tools/check.sh` (ruff, markdown, shell checks)

**Target Platform**: macOS and Linux, invoked from a consuming repo's root via `${CLAUDE_PLUGIN_ROOT}`

**Project Type**: Claude Code plugin (skills plus supporting scripts)

**Performance Goals**: N/A. Each rule and each derived doc is read once per sync.

**Constraints**: Detection is exact text match, so it is deterministic. No write without approval. Output is deterministic for the same inputs.

**Scale/Scope**: Tens to low hundreds of rules, so per-rule exact-match scans of three derived docs are fine.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` (version 2.0.1):

- **I. Mechanism, Never Content**: PASS. The plugin adds mechanism only. Riposte's prose is migrated into riposte's own rule files, not shipped.
- **II. Single Source of Truth**: PASS with a note. The rule file remains the only source, and derived docs are copies. Principle II says each rule is one sentence with one modal verb. The design keeps the formal statement as that one sentence and adds per-audience wordings, each validated to the same one-sentence, one-modal rule. This expands the concept of a rule, so the constitution needs a MINOR amendment (see Complexity Tracking).
- **III. Checkpointed Steps**: PASS. Removals are proposed in sync step 4 and written only after approval (step 5), with the re-check from FR-005.
- **IV. Deterministic Before Generative**: PASS. Detection (exact-match scan, last-written lookup, content hash) is computed by scripts. The agent drafts wording only at `add`/`edit` time, which Principle IV reserves for LLM judgment.
- **V. Honest Enforcement Reporting**: PASS (not applicable). Enforcement tiers are unchanged.
- **Plugin Constraints, skill layout**: PASS. Changes stay in `skills/{add,edit,sync}/` with their scripts beside them.
- **Plugin Constraints, skill descriptions**: PASS, with a condition. `add`, `edit`, and `sync` descriptions are not expected to change materially. If `add` or `edit` gains wording triggers, fresh-context trigger tests are required before merge (tracked in tasks).
- **Plugin Constraints, optional pieces degrade gracefully**: PASS. A missing derived doc yields no removal (FR-007). A rule with no wording for an active audience is a defect, reported like any other.
- **Development Workflow, README current state**: PASS. README gets updated for the new `add`/`edit` fields and sync removal.
- **Development Workflow, deferred phases in ROADMAP.yaml**: PASS. Riposte's one-time migration is an ops step, not a deferred phase in this repo.

**Result**: No gate violations. One justified expansion (Principle II) recorded in Complexity Tracking.

**Re-check after Phase 1 design**: PASS, subject to the Principle II amendment.

## Project Structure

### Documentation (this feature)

```text
specs/005-sync-audience-removal/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── rule_wording.md  # Phase 1 output: frontmatter wording and synced_wording
│   └── sync_status.md   # Phase 1 output: extended sync row
├── checklists/
│   └── requirements.md
└── tasks.md             # Created by /speckit-tasks, not by this command
```

### Source Code (repository root)

```text
scripts/
├── policy_frontmatter.py         # MODIFIED: KEY_ORDER gains wording, synced_wording; validate both maps
└── ...

skills/add/
├── SKILL.md                      # MODIFIED: ask for per-audience wording
└── scripts/add_rule.py           # MODIFIED: --wording audience=text (repeatable); required per audience

skills/edit/
├── SKILL.md                      # MODIFIED: wording.<audience> is editable
└── scripts/edit_rule.py          # MODIFIED: EDITABLE gains wording.human, wording.agent

skills/sync/
├── SKILL.md                      # MODIFIED: removal and not-found steps; wording text per target
└── scripts/
    ├── sync_status.py            # MODIFIED: --root; exact-match stale_in per row; content hash ignores synced_wording
    └── record_sync.py            # MODIFIED: write synced_wording for active audiences, drop others

tests/
├── test_add_rule.py              # MODIFIED: fixtures and wording validation
├── test_edit_rule.py             # MODIFIED: wording.<audience> edits
├── test_sync_status.py           # MODIFIED: stale_in cases
├── test_record_sync.py           # MODIFIED: synced_wording written and pruned; hash stable after record
└── test_policy_frontmatter.py    # MODIFIED: wording and synced_wording validation

README.md                         # MODIFIED: add/edit fields and sync removal
```

**Structure Decision**: Extend existing scripts rather than add new ones. Storage uses the nested
mapping that `policy_frontmatter.py` already supports (one level, as with `verification`), so no
parser change is needed. Detection stays in the one sync scan (Principle IV).

## Design Notes

- **Where wording lives**: `wording` is a nested map in frontmatter, keyed by audience. The body
  keeps `**<id>**: <statement>` as the formal one-sentence rule, which `judge`, `audit` and `status`
  already read. Propagation uses `wording`, not the body. The spec did not settle this location;
  this plan does, and the choice is recorded in research R1.
- **Last-written wording**: `synced_wording` is a nested map keyed by audience, written by
  `record_sync` when it records approved IDs. After a record it holds exactly the current `wording`
  for the rule's current audiences. Keys for dropped audiences are removed at that point.
- **Content hash excludes synced_wording**: `record_sync` writes `synced_wording` after computing
  the hash, so the hash must ignore the `synced_wording` block too, or a freshly recorded rule
  would read as changed. This extends the existing `synced_hash` exclusion.
- **Detection**: for each rule and each audience in `synced_wording`:
  - If that audience is no longer in `audience`, the doc for it is a stale location. The text is
    `synced_wording.<audience>`.
  - Search that doc with the whitespace-normalized pattern (see R2). If found exactly once, propose removing that span (plus one
    adjoining newline or space). If found zero times, report `not found` (FR-002). If found more
    than once, report `ambiguous` and propose nothing.
- **Agent-only file**: `.claude/rules/<id>.md` holds exactly the agent wording plus a newline. When
  it is stale, the removal is the whole file, and only if its content still equals the stored
  wording plus a newline. Otherwise it is reported as `not found`.
- **Absent doc**: a missing doc yields no removal and is reported as absent (FR-007).
- **Approval and record**: approved removals are applied under the re-check from FR-005.
  `record_sync` then records only the approved IDs. A declined removal leaves the rule `changed`,
  and its stale locations keep being reported.
- **FR-003 already holds**: an audience change already alters the content hash, so the rule reads
  `changed: true` (verified 2026-10-04 in a scratch rule directory).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle II expansion: a rule carries one formal statement plus per-audience wordings, each one sentence with one modal verb | Propagated prose must stay audience-specific and must be derived once, and detection must be exact (clarified 2026-10-04) | Pasting the formal rule into derived docs was rejected in clarify; agent-judged sections violate Principle IV |

The expansion needs a MINOR amendment to Principle II through `/speckit-constitution`. This plan
does not perform it.
