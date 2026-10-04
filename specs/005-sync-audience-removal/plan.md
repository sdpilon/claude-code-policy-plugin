# Implementation Plan: Sync Removal When Audience Drops a Target

**Branch**: `005-sync-audience-removal` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-sync-audience-removal/spec.md`

## Summary

Each rule stores its wording per audience in its own file, and sync writes that exact wording
into the matching derived doc. Sync also records the wording it last wrote, per audience, in the
rule's frontmatter. When an audience drops a target, or its wording changes while it is still
targeted, sync finds the last-written wording by a whitespace-normalized, exact-once match in the
affected doc and proposes removing it. A reworded audience's removal is paired with an addition of
the new wording. `edit` rejects an audience drop that would discard an unrecorded wording edit, and
requires an explicit review flag for statement changes. Detection is a script; the agent only drafts
wording at `add`/`edit` time and drafts proposal text at sync time. Hand-edited text that no longer
matches is reported, never removed.

## Technical Context

**Language/Version**: Python 3 (stdlib only, matching the existing scripts)

**Primary Dependencies**: None beyond the standard library and the existing `scripts/` helpers (`policy_ids`, `policy_frontmatter`, `policy_lock`, `policy_manifest`)

**Storage**: `.policy/rule/*.md` (source, now with per-audience wording and last-written wording in frontmatter) and derived docs `CONTRIBUTING.md`, `CLAUDE.md`, `.claude/rules/<id>.md` (outputs)

**Testing**: `unittest` through `tests/_cli.py`; `tools/check.sh` (ruff, markdown, shell checks)

**Target Platform**: macOS and Linux, invoked from a consuming repo's root via `${CLAUDE_PLUGIN_ROOT}`

**Project Type**: Claude Code plugin (skills plus supporting scripts)

**Performance Goals**: N/A. Each rule and each derived doc is read once per sync.

**Constraints**: Detection is a whitespace-normalized, exact-once match over `[ \t\r\n]`, so it is deterministic. No write without approval. Output is deterministic for the same inputs.

**Scale/Scope**: Up to about 100 rules per repo (clarified 2026-10-04). A full re-scan of the three derived docs on each run is acceptable, so no index or cache is needed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` (version 2.3.0):

- **I. Mechanism, Never Content**: PASS. The plugin adds mechanism only. Riposte's prose is migrated into riposte's own rule files, not shipped.
- **II. Single Source of Truth**: PASS. The rule file remains the only source, and derived docs are copies. The formal statement is one sentence with one modal verb. Audience wordings are single lines, approved by a person at `add`/`edit`, re-reviewed when the statement changes (enforced by the script's review flag, R11), copied verbatim, and matched with whitespace normalized (constitution 2.3.0).
- **III. Checkpointed Steps**: PASS. Removals and additions are proposed in sync step 4 and written only after approval (step 5). Step 5 re-checks the target documents (FR-005) and the rule's source hash (R13). `record_sync --expect` refuses to record a rule whose source changed since the proposal.
- **IV. Deterministic Before Generative**: PASS. Detection (whitespace-normalized match, last-written lookup, reworded and dropped classification, content hash, source hash) is computed by scripts. The agent drafts wording only at `add`/`edit` time, which Principle IV reserves for LLM judgment.
- **V. Honest Enforcement Reporting**: PASS (not applicable). Enforcement tiers are unchanged.
- **Plugin Constraints, skill layout**: PASS. Changes stay in `skills/{add,edit,sync,status}/` with their scripts beside them.
- **Plugin Constraints, skill descriptions**: PASS, with a condition. `add`, `edit`, and `sync` descriptions are not expected to change materially. If `add` or `edit` gains wording triggers, fresh-context trigger tests are required before merge (tracked in tasks).
- **Plugin Constraints, optional pieces degrade gracefully**: PASS. A missing derived doc yields no removal (FR-007). A rule with no wording for an active audience is a defect, reported like any other.
- **Development Workflow, README current state**: PASS. README gets updated for the new `add`/`edit` fields and sync removal.
- **Development Workflow, deferred phases in ROADMAP.yaml**: PASS. Riposte's one-time migration is an ops step, not a deferred phase in this repo.

**Result**: No gate violations. One justified expansion (Principle II) recorded in Complexity Tracking.

**Re-check after Phase 1 design**: PASS under constitution 2.3.0. One open point is recorded in R12 (overwrite of a reworded agent-only file), which the spec does not state.

## Project Structure

### Documentation (this feature)

```text
specs/005-sync-audience-removal/
├── plan.md              # This file
├── research.md          # Phase 0 output: R1 to R15
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output: Scenarios 1 to 10
├── contracts/
│   ├── rule_wording.md  # Phase 1 output: frontmatter wording, edit and record_sync behavior
│   └── sync_status.md   # Phase 1 output: extended sync row, stale_in reason
├── checklists/
│   └── requirements.md
└── tasks.md             # Generated by /speckit-tasks; convergence and amendment phases appended
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
├── SKILL.md                      # MODIFIED: wording.<audience> editable; review flag; rejected drop
└── scripts/edit_rule.py          # MODIFIED: EDITABLE gains wording.human, wording.agent;
                                  #   --reviewed-wording for statement changes; reject drop with unrecorded wording

skills/status/
└── scripts/policy_status.py      # MODIFIED: missing or mismatched wording reported as a defect

skills/sync/
├── SKILL.md                      # MODIFIED: removal, addition pairing for reworded, source re-check, record --expect
└── scripts/
    ├── sync_status.py            # MODIFIED: --root; stale_in with reason dropped or reworded; content hash ignores synced_wording
    └── record_sync.py            # MODIFIED: write synced_wording for active audiences, drop others; --expect ID=HASH

tests/
├── test_add_rule.py              # MODIFIED: fixtures and wording validation
├── test_edit_rule.py             # MODIFIED: wording.<audience> edits; reject drop; reviewed-wording flag
├── test_sync_status.py           # MODIFIED: stale_in cases, reworded and dropped, audience-change record
├── test_record_sync.py           # MODIFIED: synced_wording written and pruned; hash stable; --expect
├── test_policy_frontmatter.py    # MODIFIED: wording and synced_wording validation
├── test_policy_status.py         # MODIFIED: fixtures carry wording
├── test_retire_rule.py           # MODIFIED: fixtures carry wording
├── test_init_policy.py           # MODIFIED: add call passes --wording
├── test_audit_checks.py          # MODIFIED: fixtures carry wording
└── test_write_lock.py            # MODIFIED: fixtures carry wording

README.md                         # MODIFIED: add/edit fields and sync removal
```

**Structure Decision**: Extend existing scripts rather than add new ones. Storage uses the nested
mapping that `policy_frontmatter.py` already supports (one level, as with `verification`), so no
parser change is needed. Detection stays in the one sync scan (Principle IV).

## Design Notes

- **Where wording lives**: `wording` is a nested map in frontmatter, keyed by audience. The body
  keeps `**<id>**: <statement>` as the formal one-sentence rule, which `judge`, `audit` and `status`
  already read. Propagation uses `wording`, not the body. (R1)
- **Last-written wording**: `synced_wording` is a nested map keyed by audience, written by
  `record_sync` when it records approved IDs. After a record it holds exactly the current `wording`
  for the rule's current audiences. Keys for dropped audiences are removed at that point. (R4)
- **Content hash excludes synced_wording**: `record_sync` writes `synced_wording` after computing
  the hash, so the hash must ignore the `synced_wording` block too, or a freshly recorded rule
  would read as changed. (R3)
- **Detection**: for each rule and each audience in `synced_wording`, a stale location is reported
  when either:
  - the audience is no longer in `audience` (`reason: "dropped"`), with text `synced_wording.<audience>`; or
  - the audience is still targeted and `wording.<audience>` differs from `synced_wording.<audience>`
    (`reason: "reworded"`), with the same text (R9).

  Each location is searched with the whitespace-normalized pattern (R2). Exactly one match is
  `found` and is a removal candidate, with the span plus one adjoining newline or space. Zero is
  `not_found`. More than one is `ambiguous`. Neither proposes a removal.
- **Reworded removal pairs with an addition**: a `reworded` removal is proposed with the new
  wording as an addition to the same doc, placed as the proposal states (FR-002, FR-008).
- **Agent-only file**: `.claude/rules/<id>.md` holds exactly the agent wording plus a newline.
  When the agent audience is dropped, the removal is deleting the file, only if its content equals
  the stored wording plus a newline (R5). When it is reworded and still targeted, the file is
  overwritten with the new wording under the same exact-match gate (R12). Otherwise it is reported
  as `not_found`.
- **Absent doc**: a missing doc yields no removal and is reported as absent (FR-007).
- **Reject drop with unrecorded wording**: `edit` checks, before dropping `wording.<audience>`,
  whether a recorded `synced_wording.<audience>` differs from it. If so, the edit exits `2` and
  writes nothing (FR-012, R10). An audience never recorded, or recorded with equal text, is dropped
  as before, so quickstart Scenario 1 is unchanged.
- **Review flag for statement changes**: a run whose `--set` list includes `statement` requires
  `--reviewed-wording`, or it exits `2` and writes nothing. Preview prints `review wording.<audience>`
  lines and needs no flag (FR-009, R11).
- **Approval, source re-check and record**: the proposal records each rule's `current_hash`. Before
  applying, sync re-checks the target docs (FR-005) and re-runs `sync_status` to confirm each
  approved rule's hash is unchanged (R13). `record_sync --expect ID=HASH` refuses with exit `1` if
  a rule's source changed since the proposal. A declined removal leaves the rule `changed`, and its
  stale locations keep being reported.
- **FR-003 already holds**: an audience change already alters the content hash, so the rule reads
  `changed: true`. A test pins it (R8).
- **Partial approval (FR-004, clarified 2026-10-04)**: a rule is recorded only when every proposed
  change for it was applied. `record_sync` enforces this. It refuses a rule while the rule has a pending
  addition or a found removal, computed by the same `build_row` that `sync_status` uses, so a
  declined or failed change keeps the rule `changed` (R14).
- **Already-applied changes are not re-proposed (FR-004, clarified 2026-10-04)**: `sync_status`
  computes, by script, which additions are still pending: a target is pending only when the current
  wording is not present in it, matched as `found` (exact once, whitespace normalized). A reworded
  removal whose old text is not found, while the new wording is present once, is already applied and
  is not reported. (R15)

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle II expansion: a rule carries one formal statement plus per-audience single-line wordings, approved by a person and matched with whitespace normalization | Propagated prose must stay audience-specific and must be derived once, and detection must be deterministic (clarified 2026-10-04) | Pasting the formal rule into derived docs was rejected in clarify; agent-judged sections violate Principle IV |

The MINOR amendment to Principle II is in place (constitution 2.3.0).
