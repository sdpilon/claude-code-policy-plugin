# Tasks: Sync Removal When Audience Drops a Target

**Input**: Design documents from `/specs/005-sync-audience-removal/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the approved plan lists test modifications for each script, and the quickstart defines the acceptance scenarios. No TDD ordering is required.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Baseline)

**Purpose**: Record the state before any change

- [X] T001 Run `tools/check.sh` and the unittest suite as CI runs them (see `.github/workflows/checks.yml`) from the repository root, and record any failures that already exist on `main` in the PR description. Do not fix them in this feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wording storage, validation, and the content hash. Every user story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Extend `KEY_ORDER` in `scripts/policy_frontmatter.py` to `title, tags, created, modified, audience, verification, wording, synced_hash, synced_wording`
- [X] T003 Add `normalize_wording(text)` to `scripts/policy_frontmatter.py`: collapse each run of `[ \t\r\n]+` into one space and trim both ends; a pure function that returns a `str`
- [X] T004 Extend `validate()` in `scripts/policy_frontmatter.py`: `wording` is required and must be a map whose keys equal the set of `audience` values; each value is non-empty and contains no `\n` or `\r`; `synced_wording`, when present, is a map whose keys are a subset of `{human, agent}`, with non-empty single-line values (FR-010)
- [X] T005 Update `content_hash` in `skills/sync/scripts/sync_status.py` to remove the `synced_hash:` line and the `synced_wording:` block (the key line plus its indented children) before hashing, so writing `synced_wording` does not change the hash
- [X] T006 Add `--wording AUDIENCE=TEXT` (repeatable) to `skills/add/scripts/add_rule.py`: each audience in `--audience` needs exactly one wording; a wording for an audience not in `--audience` exits `2`; each `TEXT` is normalized with `normalize_wording` and an empty result exits `2`; writes `wording` in frontmatter and does not write `synced_wording` or `synced_hash` (FR-010)
- [X] T007 Extend `skills/edit/scripts/edit_rule.py`: `EDITABLE` gains `wording.human` and `wording.agent`; each value is normalized; setting `wording.<audience>` for an audience not in the rule exits `2`; editing `wording` or `audience` never changes `synced_wording`; when `statement` is edited, the output lists each audience wording for review (constitution Principle II) (FR-009, FR-010)
- [X] T008 [P] Update `skills/add/SKILL.md`: require one wording per audience, show each wording for approval under the Principle III checkpoint before writing the file (FR-009)
- [X] T009 [P] Update `skills/edit/SKILL.md`: `wording.<audience>` is editable; for a `statement` edit, run `edit_rule.py --preview` first, show each audience wording for re-approval, and write only after approval (FR-009)
- [X] T010 Add a `wording` map matching each `audience` to every test fixture that writes a rule file, in `tests/test_policy_frontmatter.py`, `tests/test_sync_status.py`, `tests/test_record_sync.py`, `tests/test_edit_rule.py`, `tests/test_policy_status.py`, `tests/test_retire_rule.py`, `tests/test_audit_checks.py`, and `tests/test_write_lock.py`
- [X] T011 Add unit tests in `tests/test_policy_frontmatter.py` for `normalize_wording` (runs of spaces, tabs, newlines, leading and trailing whitespace) and for `validate()` rejecting a missing `wording`, a key mismatch, a newline in a value, and an invalid `synced_wording` key
- [X] T012 Add unit tests in `tests/test_add_rule.py` and `tests/test_edit_rule.py` for `--wording` and `wording.<audience>` behavior listed in T006 and T007. Update `tests/test_init_policy.py`, whose `add` call must pass `--wording` for each audience.
- [X] T013 Add a unit test in `tests/test_sync_status.py`: `content_hash` is unchanged when `synced_wording` is added or changed, and changes when `wording` changes
- [X] T014 Update `skills/status/scripts/policy_status.py` so that a rule whose `wording` is missing, or whose `wording` keys do not match its `audience`, gets a `defect` in the status output, as `audience missing` already does (FR-010)
- [X] T015 Add a test in `tests/test_policy_status.py` for a rule with no `wording` and for a rule whose `wording` keys differ from its `audience`; both must show a defect (FR-010)

**Checkpoint**: Foundation ready. Rules store, validate, and hash wording correctly.

---

## Phase 3: User Story 1 - Sync reports text that must leave a derived doc (Priority: P1) 🎯 MVP

**Goal**: Sync finds the last-written wording of a dropped audience by exact-once match and proposes its removal. Sync also reports text it cannot match, and states placement for every addition.

**Independent Test**: Quickstart Scenarios 1, 4, 5, and 6 in a scratch directory. Scenario 1 must list `CONTRIBUTING.md` as `found`, and no removal may be proposed for a `not_found`, `ambiguous`, or `absent` entry.

### Tests for User Story 1

- [X] T016 [US1] Add `--root` (default `.`) to `skills/sync/scripts/sync_status.py`; derived-doc paths resolve against it
- [X] T017 [US1] Add `missing_wording` to each row in `skills/sync/scripts/sync_status.py`: active audiences with no `wording` entry
- [X] T018 [US1] Add `stale_in` to each row in `skills/sync/scripts/sync_status.py`: for each audience key in `synced_wording` that is not in `audience`, locate the derived doc (human → `CONTRIBUTING.md`; agent → `CLAUDE.md`, plus `.claude/rules/<id>.md` as `kind: "file"`); `status` is `absent` if the doc is missing
- [X] T019 [US1] In `stale_in` in `skills/sync/scripts/sync_status.py`, for each present doc, search for the stored text as a pattern built from its words joined by `[ \t\r\n]+`; `status` is `not_found` (0 matches), `ambiguous` (more than 1), or `found` (exactly 1, with the matched span as `text`)
- [X] T020 [US1] In `stale_in` in `skills/sync/scripts/sync_status.py`, for `kind: "file"`, `status` is `found` only when the file content equals the stored text plus `\n`; otherwise `not_found`
- [X] T021 [US1] Set `changed` to `true` in `skills/sync/scripts/sync_status.py` whenever `stale_in` or `missing_wording` is non-empty
- [X] T022 [US1] Add tests in `tests/test_sync_status.py` covering every audience transition: `[human]`→`[agent]`, `[agent]`→`[human]`, `[human, agent]`→`[agent]`, `[human, agent]`→`[human]`, `[agent]`→`[human, agent]`, and `[human]`→`[human, agent]`; for each transition, every dropped audience is listed in `stale_in`, and no added audience produces a removal
- [X] T023 [US1] Add tests in `tests/test_sync_status.py` for stale-location outcomes: reworded text gives `not_found`; duplicated text gives `ambiguous`; missing doc gives `absent`; agent-only file with exact content gives `found` with `kind: "file"`
- [X] T024 [US1] Add tests in `tests/test_sync_status.py` for targeting and missing wording: a still-targeted audience is never listed in `stale_in`; a missing wording is reported in `missing_wording`

### Implementation for User Story 1

- [X] T025 [US1] Update step 4 of `skills/sync/SKILL.md`: propose removals only for `stale_in` entries with `status: "found"`; report `not_found`, `ambiguous`, and `absent` entries by document and rule ID with no removal proposed (FR-002) Cites FR-006.
- [X] T026 [US1] Update step 4 of `skills/sync/SKILL.md` for additions: each proposed addition states the target section and the position within it (FR-008); a rule listed in `missing_wording` is reported as a defect and not proposed; each addition writes only the `wording` for that document's audience, copied verbatim (FR-011)
- [X] T027 [US1] Confirm the `description` in the frontmatter of `skills/sync/SKILL.md`, `skills/add/SKILL.md`, and `skills/edit/SKILL.md` is unchanged; none changed, so no fresh-context trigger tests were needed (constitution Plugin Constraints)

**Checkpoint**: User Story 1 is independently testable. Quickstart Scenarios 1, 4, 5, and 6 pass.

---

## Phase 4: User Story 2 - Removals are applied only after approval and the record stays consistent (Priority: P2)

**Goal**: Approved changes are applied after a re-check, and `record_sync` records what was applied. A declined removal leaves the rule changed.

**Independent Test**: Quickstart Scenarios 2 and 3. Scenario 2 must show `changed: false` and no `human` key in `synced_wording` after recording. Scenario 3 must show `changed: true` with the stale location still listed.

### Tests for User Story 2

- [X] T028 [US2] Add tests in `tests/test_record_sync.py`: `synced_wording` is written for current audiences; a dropped audience key is pruned; a recorded rule reads `changed: false`; the body is byte-identical after recording; a declined removal (no record) keeps `changed: true` and the stale location `found`

### Implementation for User Story 2

- [X] T029 [US2] Update `skills/sync/scripts/record_sync.py` so that for each approved ID it sets `synced_wording` to the current `wording` for the rule's current audiences, verbatim, and removes `synced_wording` entirely when no audience remains (FR-004)
- [X] T030 [US2] Update `skills/sync/scripts/record_sync.py` to compute `synced_hash` with the updated `content_hash` (T005) before writing `synced_hash` and `synced_wording`, and to write only those two fields (FR-004)
- [X] T031 [US2] Update steps 5 and 6 of `skills/sync/SKILL.md`: before applying each approved removal or addition, re-read the target document and stop for that item if it changed since the proposal (FR-005); record only the approved IDs and say which were declined

**Checkpoint**: User Story 2 is independently testable. Quickstart Scenarios 2 and 3 pass.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, full checks, and end-to-end validation

- [X] T032 Update `README.md` to describe the current behavior: `/policy:add` and `/policy:edit` take a wording per audience; `/policy:sync` proposes removals of last-written wording and states placement for additions; existing prose in a repo is copied into rule files by hand once
- [X] T033 Run `tools/check.sh` and the unittest suite; all checks pass, and any failure from T001 is either unchanged or noted
- [X] T034 Run quickstart Scenarios 1–6 in a scratch directory and confirm each pass condition; record the results in the PR description; also confirm that declining a proposal leaves every derived doc unchanged (SC-002)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup. Blocks both user stories. T002–T004 edit `scripts/policy_frontmatter.py` and run in order; T005 edits `skills/sync/scripts/sync_status.py`.
- **User Story 1 (Phase 3)**: Depends on Foundational
- **User Story 2 (Phase 4)**: Depends on Foundational for the hash and fixtures. Its end-to-end scenarios also need User Story 1's `stale_in` output.
- **Polish (Final Phase)**: Depends on both user stories

### Within Each User Story

- Script changes before their tests
- Script changes before the SKILL.md step that describes them
- Story complete before the Checkpoint is claimed

### Parallel Opportunities

- T008 and T009 touch different files and can run in parallel once T002–T004 are done
- T006 and T007 follow T003 and T004, so they run after the foundation's validation and normalization
- User Story 1 and User Story 2 script work touches different files (`sync_status.py` vs `record_sync.py`), so the two stories can proceed in parallel after Phase 2, with the end-to-end check at the end

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (User Story 1)
3. **STOP and VALIDATE**: quickstart Scenarios 1, 4, 5, and 6
4. The removal is proposed but not yet recorded, so User Story 2 is still needed for a complete cycle

### Incremental Delivery

1. Phase 1 + Phase 2 → wording stored and hashed correctly
2. Add User Story 1 → proposals show removals and placement
3. Add User Story 2 → approved changes are recorded and declined ones stay visible
4. Polish → docs and full checks

---

## Notes

- [P] tasks = different files from their neighbors; each still waits for the tasks it depends on (see Dependencies)
- [Story] label maps each task to a user story for traceability. Phases 5 onward are convergence and amendment phases, so their tasks carry no story label
- Constraints from data-model.md are carried into the tasks that enforce them (T002–T004, T006, T007, T018–T020)
- Commit after each phase, not each task, and only when the user asks

## Phase 5: Convergence

**Purpose**: Remaining gaps found by `/speckit-converge` against spec.md, plan.md, tasks.md, and the constitution

- [X] T035 CRITICAL: `sync` MUST re-check that the rule's source hasn't changed since its proposal before applying it: record each rule's `current_hash` in the proposal, and before applying any removal, addition, or `record_sync`, re-run `sync_status` and stop for any rule whose `current_hash` changed (the skill currently re-checks only derived docs) per Constitution III (missing)
- [X] T036 Make `sync_status` report `stale_in` and `missing_wording` as empty for a rule whose validation fails (for example an invalid `audience`), so no removal is offered for it, and add a test in `tests/test_sync_status.py` per spec Edge Cases and `contracts/sync_status.md` error behavior (contradicts)

## Phase 6: Convergence

**Purpose**: Remaining gaps found by `/speckit-converge` against spec.md, plan.md, tasks.md, and the constitution

- [X] T037 Add a test in `tests/test_sync_status.py` that an audience change (for example `[human]` to `[agent]`) after a record reads `changed: true`, and that a rule with no audience change reads `changed: false` after a record, per FR-003 and plan decision R8 (missing)

## Phase 7: Convergence

**Purpose**: Remaining gaps found by `/speckit-converge` against spec.md, plan.md, tasks.md, and the constitution

- [X] T038 Document the `--expect ID=HASH` option of `record_sync.py` in the `record_sync.py` section of `contracts/rule_wording.md`, including its exit code 1 on a changed source, per Constitution III and T035 (partial)

## Phase 8: Spec amendment (FR-012)

**Purpose**: Reject an audience drop that would silently discard an unrecorded wording edit

- [X] T039 In `skills/edit/scripts/edit_rule.py`, reject an audience change that drops an audience whose `wording.<audience>` differs from its `synced_wording.<audience>`, exiting 2 with a message that names the audience and says to run sync first or revert the wording; a drop with no such difference, or for an audience never recorded, still succeeds; add tests in `tests/test_edit_rule.py` per FR-012 (missing)
- [X] T040 Update the guardrails in `skills/edit/SKILL.md` to describe the rejected drop and the sync-first path, per FR-012 (missing)
- [X] T041 Document the rejected drop in the `edit_rule.py` section of `contracts/rule_wording.md`, per FR-012 (missing)

## Phase 9: Plan revision (widened spec)

**Purpose**: Work added by the revised plan for the rewording, review-flag, and source re-check decisions (R9 to R13)

- [X] T042 In `skills/sync/scripts/sync_status.py`, add `stale_in` entries for audiences still targeted whose `wording` differs from `synced_wording`, with `reason: "reworded"`, matched by the same exact-once search; give the existing dropped-audience entries `reason: "dropped"`; mark the row `changed` for either reason, per FR-001, FR-002, R9, and the data-model stale location
- [X] T043 Add tests in `tests/test_sync_status.py` for a reworded still-targeted audience (`found`, `not_found`, `ambiguous`), the `reason` value on dropped entries, and a reworded agent-only file (`kind: "file"`), per quickstart Scenarios 7 and 9 and R9 and R12
- [X] T044 Update step 4 of `skills/sync/SKILL.md` so each reworded removal is proposed together with an addition of the current wording to the same doc, and a reworded agent-only file is overwritten only when its content equals the last-written wording plus a newline, per FR-002 and R12
- [X] T045 In `skills/edit/scripts/edit_rule.py`, require `--reviewed-wording` on any non-preview run whose `--set` list includes `statement`; without it, exit 2 and write nothing; `--preview` needs no flag, per FR-009 and R11
- [X] T046 Add tests in `tests/test_edit_rule.py` for the review flag: a statement change without the flag is refused with nothing written, one with the flag is written, and preview works without it, per quickstart Scenario 10 and R11
- [X] T047 Update `skills/edit/SKILL.md` so the skill passes `--reviewed-wording` only after the person approves each `review wording.<audience>` line, per FR-009
- [X] T048 Update the sync bullet in `README.md` to say that a reworded still-targeted audience gets its old text removed and the new wording added, keeping README to the current state, per the constitution's README rule
- [X] T049 Run quickstart Scenarios 1 to 10 in a scratch directory, and record which pass in the PR description, per quickstart and SC-001 to SC-003

## Phase 10: Convergence

**Purpose**: Remaining gaps found by `/speckit-converge` against spec.md, plan.md, tasks.md, and the constitution

- [X] T050 Update the `/policy:edit` bullet in `README.md` to say that a statement change needs `--reviewed-wording` after the person approves each audience wording, and that an audience drop is rejected while its wording has an edit sync has not recorded, per FR-009, FR-012, and the constitution's README current-state rule (partial)

## Phase 11: Amendment (partial approval and re-proposal)

**Purpose**: Work added by the 2026-10-04 clarifications and plan notes for partial approval and already-applied changes (FR-004, R14, R15)

- [X] T051 Update step 4 of `skills/sync/SKILL.md` so additions come only from the script's `pending` list, not from every target, and an addition already in place is not proposed, per FR-004 and R15
- [X] T052 Update step 6 and step 7 of `skills/sync/SKILL.md` so a rule is passed to `record_sync` only when every proposed change for it was applied; any declined or failed change leaves the rule out of the call and reported as changed, replacing "only the IDs that were approved and applied", per FR-004 and R14
- [X] T053 In `skills/sync/scripts/sync_status.py`, add a per-rule `pending` list (each target whose current `wording` is not present exactly once, with `kind` and `path`; `kind: "file"` requires content equal to the wording plus a newline), and drop a `reworded` stale entry with `status: "not_found"` when the new wording is present once in the same doc, per FR-004, R15, and `contracts/sync_status.md`
- [X] T054 Add tests in `tests/test_sync_status.py` for `pending` (present, absent, and ambiguous targets, and a present agent-only file) and for a reworded removal already applied (new wording present once, old text absent, entry omitted), per R15; plus an absent doc that is never created (FR-007) and stale entries that name document, rule, and text (SC-004)
- [X] T055 Add a quickstart scenario in `quickstart.md` for partial approval: an approved addition plus a declined removal leaves the rule `changed`, and the next run does not re-propose the addition, per FR-004 and R14
- [X] T056 Run `tools/check.sh` and the unittest suite, and record the results, per the constitution's checks

## Phase 12: Analysis remediation (2026-10-04)

**Purpose**: Work from the second `/speckit-analyze` run: K1 (script-enforced record), K2 to K5 (doc consistency)

- [X] T057 In `skills/sync/scripts/sync_status.py`, extract `build_row(text, rule_id, doc_root)` so `record_sync` and `sync_status` share one row builder, and add `unapplied(row)` for pending additions and found removals, per FR-004, R14 (K1)
- [X] T058 In `skills/sync/scripts/record_sync.py`, add `--root` and refuse (exit 1, nothing written) any rule with an unapplied change, per FR-004 and R14 (K1)
- [X] T059 Add `RecordSyncUnappliedTests` in `tests/test_record_sync.py`: a pending addition is refused, Scenario 11 partial approval is refused and then recorded, and a hand-edited not_found report does not block, per FR-004, R14 (K1, K3)
- [X] T060 Make the record and sync test fixtures write the derived docs a sync would leave, and pass `--root` to each record call, so record tests check the refusal rules rather than the repo's own files (K1)
- [X] T061 Update step 6 and step 7 of `skills/sync/SKILL.md` and the `record_sync.py` section of `contracts/rule_wording.md` for the script-enforced refusal and `--root`, per FR-004 (K1)
- [X] T062 Resolve the R12 open point in `research.md` (FR-002 covers it), update the Scenario 11 pass condition and the automated-coverage line in `quickstart.md` (K2, K3)
- [X] T063 Correct the T027 trigger-test path (no description changed, so no trigger tests were needed), and cite FR-006 in T025 (K4, K5)
- [X] T064 Run `tools/check.sh` and the unittest suite, and record the results (verification)

## Phase 13: Convergence

**Purpose**: Remaining gaps found by `/speckit-converge` against spec.md, plan.md, tasks.md, and the constitution

- [X] T065 Make `build_row` in `skills/sync/scripts/sync_status.py` report a `kind: "file"` target that already exists with content other than its wording plus a newline under a new `held` list, and leave it out of `pending`, so sync never proposes overwriting a hand-edited file (per Assumptions: hand-edited derived text is reported, not removed; FR-002) (contradicts)
- [X] T066 Add tests in `tests/test_sync_status.py` for a hand-edited `.claude/rules/<id>.md` (listed in `held`, absent from `pending`, file bytes unchanged) and for one that equals its wording plus a newline (not held, not pending), per Assumptions and FR-002 (missing)
- [X] T067 Update step 4 of `skills/sync/SKILL.md` so `held` files are reported by path and rule ID and are never proposed for overwrite, per Assumptions and FR-002 (partial)
- [X] T068 Update the `/policy:sync` bullet in `README.md` to describe the current behavior: `record_sync` refuses a rule with an outstanding addition or removal, and held files are reported, not overwritten, per FR-004, Constitution Development Workflow (README describes current state) (partial)

## Phase 14: Convergence

**Purpose**: Remaining gaps found by `/speckit-converge` after Phase 13 (held files), in the plan's contract, data model, and quickstart

- [X] T069 Add `held` to the output contract in `specs/005-sync-audience-removal/contracts/sync_status.md`: its meaning, its entry shape, that it is never proposed for overwrite, and that the "New fields" sentence names `pending` and `held` as well as `missing_wording` and `stale_in`, per plan Phase 1 contract `sync_status.md` and Assumptions (partial)
- [X] T070 Add the `pending` and `held` row fields to the sync-row table in `specs/005-sync-audience-removal/data-model.md`, per plan Phase 1 output `data-model.md` (partial)
- [X] T071 Add a quickstart scenario to `specs/005-sync-audience-removal/quickstart.md` for a hand-edited agent-only file: it appears in `held` and is not overwritten by sync, per plan Phase 1 quickstart and Assumptions (partial)
