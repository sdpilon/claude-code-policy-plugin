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

- [ ] T001 Run `tools/check.sh` and the unittest suite as CI runs them (see `.github/workflows/checks.yml`) from the repository root, and record any failures that already exist on `main` in the PR description. Do not fix them in this feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wording storage, validation, and the content hash. Every user story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 Extend `KEY_ORDER` in `scripts/policy_frontmatter.py` to `title, tags, created, modified, audience, verification, wording, synced_hash, synced_wording`
- [ ] T003 Add `normalize_wording(text)` to `scripts/policy_frontmatter.py`: collapse each run of `[ \t\r\n]+` into one space and trim both ends; a pure function that returns a `str`
- [ ] T004 Extend `validate()` in `scripts/policy_frontmatter.py`: `wording` is required and must be a map whose keys equal the set of `audience` values; each value is non-empty and contains no `\n` or `\r`; `synced_wording`, when present, is a map whose keys are a subset of `{human, agent}`, with non-empty single-line values
- [ ] T005 Update `content_hash` in `skills/sync/scripts/sync_status.py` to remove the `synced_hash:` line and the `synced_wording:` block (the key line plus its indented children) before hashing, so writing `synced_wording` does not change the hash
- [ ] T006 [P] Add `--wording AUDIENCE=TEXT` (repeatable) to `skills/add/scripts/add_rule.py`: each audience in `--audience` needs exactly one wording; a wording for an audience not in `--audience` exits `2`; each `TEXT` is normalized with `normalize_wording` and an empty result exits `2`; writes `wording` in frontmatter and does not write `synced_wording` or `synced_hash`
- [ ] T007 [P] Extend `skills/edit/scripts/edit_rule.py`: `EDITABLE` gains `wording.human` and `wording.agent`; each value is normalized; setting `wording.<audience>` for an audience not in the rule exits `2`; editing `wording` or `audience` never changes `synced_wording`; when `statement` is edited, the output lists each audience wording for review (constitution Principle II)
- [ ] T008 [P] Update `skills/add/SKILL.md`: require one wording per audience, show each wording for approval under the Principle III checkpoint before writing the file
- [ ] T009 [P] Update `skills/edit/SKILL.md`: `wording.<audience>` is editable; after a `statement` edit, show each audience wording for re-approval before the edit is final
- [ ] T010 Add a `wording` map matching each `audience` to every test fixture that writes a rule file, in `tests/test_policy_frontmatter.py`, `tests/test_sync_status.py`, `tests/test_record_sync.py`, `tests/test_edit_rule.py`, `tests/test_policy_status.py`, and `tests/test_retire_rule.py`
- [ ] T011 Add unit tests in `tests/test_policy_frontmatter.py` for `normalize_wording` (runs of spaces, tabs, newlines, leading and trailing whitespace) and for `validate()` rejecting a missing `wording`, a key mismatch, a newline in a value, and an invalid `synced_wording` key
- [ ] T012 Add unit tests in `tests/test_add_rule.py` and `tests/test_edit_rule.py` for `--wording` and `wording.<audience>` behavior listed in T006 and T007
- [ ] T013 Add a unit test in `tests/test_sync_status.py`: `content_hash` is unchanged when `synced_wording` is added or changed, and changes when `wording` changes

**Checkpoint**: Foundation ready. Rules store, validate, and hash wording correctly.

---

## Phase 3: User Story 1 - Sync reports text that must leave a derived doc (Priority: P1) 🎯 MVP

**Goal**: Sync finds the last-written wording of a dropped audience by exact-once match and proposes its removal. Sync also reports text it cannot match, and states placement for every addition.

**Independent Test**: Quickstart Scenarios 1, 4, 5, and 6 in a scratch directory. Scenario 1 must list `CONTRIBUTING.md` as `found`, and no removal may be proposed for a `not_found`, `ambiguous`, or `absent` entry.

### Tests for User Story 1

- [ ] T014 [US1] Add `--root` (default `.`) to `skills/sync/scripts/sync_status.py`; derived-doc paths resolve against it
- [ ] T015 [US1] Add `missing_wording` to each row in `skills/sync/scripts/sync_status.py`: active audiences with no `wording` entry
- [ ] T016 [US1] Add `stale_in` to each row in `skills/sync/scripts/sync_status.py`: for each audience key in `synced_wording` that is not in `audience`, locate the derived doc (human → `CONTRIBUTING.md`; agent → `CLAUDE.md`, plus `.claude/rules/<id>.md` as `kind: "file"`); `status` is `absent` if the doc is missing; otherwise search for the stored text as a pattern built from its words joined by `[ \t\r\n]+`, and set `status` to `not_found` (0 matches), `ambiguous` (more than 1), or `found` (exactly 1, with the matched span as `text`); for `kind: "file"`, `found` requires the file content to equal the stored text plus `\n`
- [ ] T017 [US1] Set `changed` to `true` in `skills/sync/scripts/sync_status.py` whenever `stale_in` or `missing_wording` is non-empty
- [ ] T018 [US1] Add tests in `tests/test_sync_status.py`: dropped human audience gives `found` in `CONTRIBUTING.md`; reworded text gives `not_found`; duplicated text gives `ambiguous`; missing doc gives `absent`; agent-only file with exact content gives `found` with `kind: "file"`; a still-targeted audience is never listed in `stale_in`; a missing wording is reported in `missing_wording`

### Implementation for User Story 1

- [ ] T019 [US1] Update step 4 of `skills/sync/SKILL.md`: propose removals only for `stale_in` entries with `status: "found"`; report `not_found`, `ambiguous`, and `absent` entries by document and rule ID with no removal proposed (FR-002)
- [ ] T020 [US1] Update step 4 of `skills/sync/SKILL.md` for additions: each proposed addition states the target section and the position within it (FR-008); a rule listed in `missing_wording` is reported as a defect and not proposed
- [ ] T021 [US1] Confirm the `description` in `skills/sync/SKILL.md` frontmatter is unchanged; if it changed, run fresh-context trigger tests (constitution Plugin Constraints) and record them in `specs/005-sync-audience-removal/checklists/trigger-tests.md`

**Checkpoint**: User Story 1 is independently testable. Quickstart Scenarios 1, 4, 5, and 6 pass.

---

## Phase 4: User Story 2 - Removals are applied only after approval and the record stays consistent (Priority: P2)

**Goal**: Approved changes are applied after a re-check, and `record_sync` records what was applied. A declined removal leaves the rule changed.

**Independent Test**: Quickstart Scenarios 2 and 3. Scenario 2 must show `changed: false` and no `human` key in `synced_wording` after recording. Scenario 3 must show `changed: true` with the stale location still listed.

### Tests for User Story 2

- [ ] T022 [US2] Add tests in `tests/test_record_sync.py`: `synced_wording` is written for current audiences; a dropped audience key is pruned; a recorded rule reads `changed: false`; the body is byte-identical after recording; a declined removal (no record) keeps `changed: true` and the stale location `found`

### Implementation for User Story 2

- [ ] T023 [US2] Update `skills/sync/scripts/record_sync.py` so that for each approved ID it sets `synced_wording` to the current `wording` for the rule's current audiences, verbatim, and removes `synced_wording` entirely when no audience remains (FR-004)
- [ ] T024 [US2] Update `skills/sync/scripts/record_sync.py` to compute `synced_hash` with the updated `content_hash` (T005) before writing `synced_hash` and `synced_wording`, and to write only those two fields (FR-004)
- [ ] T025 [US2] Update steps 5 and 6 of `skills/sync/SKILL.md`: before applying each approved removal or addition, re-read the target document and stop for that item if it changed since the proposal (FR-005); record only the approved IDs and say which were declined

**Checkpoint**: User Story 2 is independently testable. Quickstart Scenarios 2 and 3 pass.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, full checks, and end-to-end validation

- [ ] T026 Update `README.md` to describe the current behavior: `/policy:add` and `/policy:edit` take a wording per audience; `/policy:sync` proposes removals of last-written wording and states placement for additions; existing prose in a repo is copied into rule files by hand once
- [ ] T027 Run `tools/check.sh` and the unittest suite; all checks pass, and any failure from T001 is either unchanged or noted
- [ ] T028 Run quickstart Scenarios 1–6 in a scratch directory and confirm each pass condition; record the results in the PR description

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup. Blocks both user stories. T002–T005 all edit shared files and run in order.
- **User Story 1 (Phase 3)**: Depends on Foundational
- **User Story 2 (Phase 4)**: Depends on Foundational for the hash and fixtures. Its end-to-end scenarios also need User Story 1's `stale_in` output.
- **Polish (Final Phase)**: Depends on both user stories

### Within Each User Story

- Script changes before their tests
- Script changes before the SKILL.md step that describes them
- Story complete before the Checkpoint is claimed

### Parallel Opportunities

- T006, T007, T008, T009 touch different files and can run in parallel once T002–T004 are done
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
- [Story] label maps each task to a user story for traceability
- Constraints from data-model.md are carried into the tasks that enforce them (T002–T004, T006, T007, T016)
- Commit after each phase, not each task, and only when the user asks
