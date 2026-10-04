# Tasks: Remove the Migration Feature

**Input**: Design documents from `/specs/004-remove-migration/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, quickstart.md

**Tests**: Not requested. No new test tasks are generated. Existing migration tests are removed under User Story 2, and the existing test suite is run as verification.

**Organization**: Tasks are grouped by user story to enable independent verification of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project: plugin files at the repository root (`skills/`, `tests/`, `.claude-plugin/`, `README.md`).

---

## Phase 1: Setup (Baseline)

**Purpose**: Record the test results before any change, so later failures can be attributed to this change

- [X] T001 Run `uv run python -m unittest discover -s tests` on the untouched `004-remove-migration` branch and note the pass count and any existing failures

---

## Phase 2: Foundational (Blocking Prerequisites)

No foundational tasks. Removal has no shared prerequisites, so the user story phases can start as soon as the baseline is recorded.

---

## Phase 3: User Story 1 - Plugin no longer offers migration (Priority: P1) 🎯 MVP

**Goal**: The `/policy:migrate` command, its skill, and every user-facing description of migration are gone.

**Independent Test**: The grep in `quickstart.md` step 2 returns nothing outside `specs/001-*` through `specs/003-*`, and the plugin metadata still parses with its version unchanged.

### Implementation for User Story 1

- [X] T002 [US1] Remove the migration skill with `git rm -r skills/migrate`, then delete any leftover untracked files in that directory with `rm -rf skills/migrate` (covers `skills/migrate/SKILL.md`, `skills/migrate/scripts/migrate_rules.py`, and the local `skills/migrate/scripts/__pycache__/`)
- [X] T003 [P] [US1] Remove the `/policy:migrate` bullet at `README.md` line 45, keeping the surrounding list valid
- [X] T004 [P] [US1] Remove "migrating" from the description string in `.claude-plugin/plugin.json`; leave `"version": "0.2.0"` unchanged
- [X] T005 [P] [US1] Remove "migrating" from the description string in `.claude-plugin/marketplace.json`; leave the version unchanged
- [X] T006 [US1] Run the grep in `quickstart.md` step 2 (excluding `specs/001-*` through `specs/003-*`) and fix any remaining match; depends on T002–T005

**Checkpoint**: No live file advertises or defines the migration command (SC-001, SC-003)

---

## Phase 4: User Story 2 - Test suite and CI stay green (Priority: P2)

**Goal**: The migration tests are removed, and every other test and CI check still passes.

**Independent Test**: The unit tests and the lint, format, markdown, and shell checks all pass, and no migration test is collected.

### Implementation for User Story 2

- [X] T007 [P] [US2] Remove the migration unit tests with `git rm tests/test_migrate_rules.py`
- [X] T008 [US2] Run `uv run python -m unittest discover -s tests`; confirm it passes, that every test passing at T001 still runs, and that no `test_migrate_rules` test is collected; depends on T007
- [X] T009 [US2] Run the lint, format, markdown, and shell checks from `quickstart.md` step 6; depends on T003 because the markdown scan must see the edited README

**Checkpoint**: The unit test suite and CI checks pass without any migration test (FR-005, SC-002)

---

## Phase 5: User Story 3 - Historical specs are preserved (Priority: P3)

**Goal**: The earlier spec directories are byte-identical to their state before this change.

**Independent Test**: The diff in `quickstart.md` step 3 is empty.

### Implementation for User Story 3

- [X] T010 [US3] Run the diff in `quickstart.md` step 3 against `main` for `specs/001-rule-per-file-restructure`, `specs/002-policy-init-update`, and `specs/003-policy-plugin-gaps`; confirm it prints nothing

**Checkpoint**: Historical spec records are untouched (FR-007, SC-004)

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Confirm the change set matches the plan and nothing is committed without a request

- [X] T011 Run `git status` and confirm the changes are limited to the deletions from T002 and T007, the edits from T003–T005, and the new `specs/004-remove-migration/` directory, matching the Source Code list in `plan.md`; leave everything uncommitted
- [X] T012 Run `quickstart.md` steps 1 and 4 (file absence and metadata validity with version unchanged)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. Runs first to capture the baseline.
- **Foundational (Phase 2)**: Empty.
- **User Stories (Phases 3–5)**: Each depends only on Setup. US2's verification needs the README edit (T003) and the test deletion (T007), so run it after those.
- **Polish (Final Phase)**: Depends on all user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Independent. This is the MVP.
- **User Story 2 (P2)**: Its deletion (T007) is independent. Its verification (T008, T009) needs T003 and T007.
- **User Story 3 (P3)**: Independent. It only verifies that nothing in the historical specs changed.

### Within Each User Story

- Edits and deletions come before the verification task that checks them (T002–T005 before T006; T007 and T003 before T008 and T009).

### Parallel Opportunities

- T003, T004, and T005 touch different files and can run in parallel.
- T007 can run in parallel with the User Story 1 tasks, since it touches a different file.
- User Story 3 (T010) can run in parallel with everything else.

---

## Parallel Example: User Story 1

```bash
# Different files, no dependencies between them:
Task: "Remove the /policy:migrate bullet in README.md line 45"
Task: "Remove 'migrating' from the description in .claude-plugin/plugin.json"
Task: "Remove 'migrating' from the description in .claude-plugin/marketplace.json"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline)
2. Complete Phase 3: User Story 1 (command, skill, and descriptions removed)
3. **STOP and VALIDATE**: run the grep in `quickstart.md` step 2

### Full Removal

1. Complete User Story 1
2. Complete User Story 2 (tests removed, CI verified)
3. Complete User Story 3 (historical specs verified)
4. Complete Polish (change set confirmed)

---

## Notes

- [P] tasks touch different files and have no dependencies on each other
- [Story] labels map each task to its user story for traceability
- Use `git rm` for deletions so they show up in the diff (FR-008)
- Leave the change uncommitted unless asked
