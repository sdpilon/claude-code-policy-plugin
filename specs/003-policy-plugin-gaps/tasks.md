# Tasks: Policy Plugin Gaps

**Input**: Design documents from `/specs/003-policy-plugin-gaps/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: included. The plan names a test module for each new script (`tests/test_record_sync.py`, `tests/test_edit_rule.py`, `tests/test_audit_checks.py`), and every story's Independent Test needs a verifiable check. Write each test first and confirm it fails before implementing.

**Organization**: grouped by user story. Phase 1 (Setup) has no tasks: the branch exists and the plan is committed. Its work is the branch's own commits.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 to US6, mapped to spec.md
- Every task names an exact file path

## Path Conventions

Plugin layout: `skills/<skill>/SKILL.md` with scripts in `skills/<skill>/scripts/`, shared
modules in `scripts/`, tests in `tests/`.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the shared statement check that both `add` and `edit` enforce (research R5).

**⚠️ CRITICAL**: no user story work may begin until this phase is complete.

- [X] T001 Add `validate_statement(text) -> list[str]` to `scripts/policy_frontmatter.py`: one sentence, exactly one modal verb (MUST, SHOULD, MUST NOT, MAY). Add unit cases to `tests/test_policy_frontmatter.py`.
- [X] T002 Switch the statement check in `skills/add/scripts/add_rule.py` to call `validate_statement`. `tests/test_add_rule.py` must still pass unchanged.

**Checkpoint**: shared statement check in place; `add` behavior unchanged.

---

## Phase 3: User Story 1 - Record a sync without hand-written hashes (Priority: P1) 🎯 MVP

**Goal**: one command writes `synced_hash` for the rules a sync applied (FR-001 to FR-003, FR-019).

**Independent Test**: in a scratch repo with two rules, record a sync for both, then confirm `sync_status.py` reports neither as changed, and a second record run writes nothing (quickstart scenario 1).

### Tests for User Story 1 ⚠️

> **Write these first and confirm they FAIL before T005.**

- [X] T003 [P] [US1] Write `tests/test_record_sync.py`: records the hash for named rules; a second run leaves files byte-identical; an unknown ID exits 2 and writes nothing; body and other frontmatter fields are unchanged byte for byte.

### Implementation for User Story 1

- [X] T004 [US1] Implement `skills/sync/scripts/record_sync.py` per `specs/003-policy-plugin-gaps/contracts/record_sync.md`. Reuse `content_hash` from `skills/sync/scripts/sync_status.py` and `atomic_write_bytes` from `scripts/policy_manifest.py`.
- [X] T005 [US1] Replace the manual `synced_hash` write-back in step 6 of `skills/sync/SKILL.md` with a call to `record_sync.py` (FR-019).

**Checkpoint**: US1 works alone. A sync can be recorded with one command.

---

## Phase 4: User Story 2 - Edit a rule without stale dates or hashes (Priority: P2)

**Goal**: one edit operation updates a rule, sets `modified`, and rejects invalid edits with the file unchanged (FR-004 to FR-006).

**Independent Test**: edit one rule's statement, confirm `modified` moves forward, confirm an invalid edit changes nothing, and confirm the rule shows as changed in `sync_status.py` until recorded (quickstart scenario 2).

### Tests for User Story 2 ⚠️

> **Write these first and confirm they FAIL before T007.**

- [X] T006 [P] [US2] Write `tests/test_edit_rule.py` (single-rule cases): `modified` is set to now; `synced_hash` is untouched; a disallowed field is rejected by name; a statement with two modal verbs is rejected; a rejected edit leaves the file byte-identical; `--preview` writes nothing.

### Implementation for User Story 2

- [X] T007 [US2] Implement the single-rule path of `skills/edit/scripts/edit_rule.py` per `specs/003-policy-plugin-gaps/contracts/edit_rule.md`. Validate with `fm.validate` and `validate_statement`, and write with `atomic_write_bytes`.
- [X] T008 [US2] Create `skills/edit/SKILL.md`. Its description must cover rule-changing requests and exclude add, retire, and sync requests. Its body runs `--preview` first, shows the diff, and applies only after the person confirms (constitution principle III).
- [X] T009 [US2] Run the trigger tests from research R8 on the `edit` skill description: fresh-context subagents, positive cases ("change the statement of rule 004", "bump the audience on these three rules") and negative cases ("add a rule", "retire rule 004", "sync the docs"). Record the results in `specs/003-policy-plugin-gaps/checklists/trigger-tests.md`.

**Checkpoint**: US2 works alone. A single rule can be edited, dated, and validated.

---

## Phase 5: User Story 3 - Apply one change to many rules (Priority: P2)

**Goal**: one command applies the same change to several rules, all or nothing, with a preview (FR-007 to FR-009).

**Independent Test**: a bulk change valid for every listed rule changes all of them; a bulk change invalid for one rule changes none (quickstart scenario 3).

**Depends on**: US2, since the bulk path extends the same script.

### Tests for User Story 3 ⚠️

> **Write these first and confirm they FAIL before T011.**

- [X] T010 [US3] Add bulk cases to `tests/test_edit_rule.py`: all-or-none when one rule fails validation; restore of already-written files when a write fails partway (inject the failure with a patched writer); `--preview` across several IDs writes nothing.

### Implementation for User Story 3

- [X] T011 [US3] Add the bulk path to `skills/edit/scripts/edit_rule.py`: validate every target first, write only if all pass, restore from in-memory originals on a write failure (research R3).
- [X] T012 [US3] Document bulk usage and the all-or-none rule in `skills/edit/SKILL.md`.

**Checkpoint**: US3 works with US2. A bulk change is one command and never half-applies on validation failure.

---

## Phase 6: User Story 4 - Run the CI audit and file missing checks (Priority: P2)

**Goal**: the audit runs `ci-checked` checks from a consumer registry, dedupes by label, and files issues for failing and unbuilt checks (FR-010 to FR-016).

**Independent Test**: with one passing check, one failing check that already has an open issue, and one check that does not exist, a single run files exactly one new issue (quickstart scenario 4).

### Tests for User Story 4 ⚠️

> **Write these first and confirm they FAIL before T015.**

- [X] T013 [US4] Write `tests/test_audit_checks.py` using an in-memory fake tracker: passing check logs `pass`; failing check files one issue; unbuilt check files `Build policy check`; an open issue with the label prevents a second filing; `defect` rules are skipped; a check that raises counts as failing; a second run files nothing; a registry without `CHECKS` exits 2.

### Implementation for User Story 4

- [X] T014 [P] [US4] Implement `skills/audit/scripts/github_tracker.py`: search open issues by label, and create an issue, both through `gh`. It has no close operation (FR-016).
- [X] T015 [US4] Implement `skills/audit/scripts/audit_checks.py` per `specs/003-policy-plugin-gaps/contracts/audit_checks.md`: load the registry, dispatch checks, stamp the label `policy-audit:<via>` and the body marker, and file through the tracker interface. Depends on T013 and T014.
- [X] T016 [P] [US4] Update `skills/audit/SKILL.md`: the registry contract, the tracker choice, the dedupe key, and the no-close guardrail. Different file from T015, so it can run alongside it.

**Checkpoint**: US4 works alone with the dry-run tracker and the fake in tests.

---

## Phase 7: User Story 5 - Find the plugin's scripts without searching (Priority: P3)

**Goal**: an agent resolves the plugin root and runs a bundled script by a documented method (FR-017).

**Independent Test**: from a fresh session, resolve the plugin root by the documented method and run one script by its resolved path, with no search (quickstart scenario 5 points at the path).

- [X] T017 [US5] Resolve research R7 by checking whether `${CLAUDE_PLUGIN_ROOT}` is substituted in skill content (Claude Code plugin docs or `claude-code-guide`). Record the decision in `specs/003-policy-plugin-gaps/research.md` under R7.
- [X] T018 [US5] Apply the R7 decision. If substituted: rewrite script paths in `skills/*/SKILL.md` to `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/...`. If not: create `scripts/plugin_root.py` that prints the root by walking up from its own path, with `tests/test_plugin_root.py`.
- [X] T019 [US5] Update the "Paths in skills" section of `README.md` so it describes the one documented method. Remove the "two levels up" rule if T018 made it unnecessary.

**Checkpoint**: US5 works alone. An agent finds the root by one method.

---

## Phase 8: User Story 6 - Know what the frontmatter parser returns (Priority: P3)

**Goal**: the parser's return type, error, and empty-value behavior are documented in the contract and the code (FR-018).

**Independent Test**: a reader with only the contract doc states the return type and error for a file with no frontmatter (quickstart scenario 5).

- [X] T020 [P] [US6] Document `parse()` in `specs/001-rule-per-file-restructure/contracts/policy_frontmatter.md`: returns a `dict` of `str` keys; values are `str`, `list`, or a nested dict of scalars; no frontmatter block raises `FrontmatterError`; an empty value is `""` or `[]`.
- [X] T021 [US6] Update the `parse()` docstring in `scripts/policy_frontmatter.py` to match T020. It touches the same file as T001, so it runs after T001.

**Checkpoint**: US6 works alone. The documented behavior matches the code.

---

## Final Phase: Polish & cross-cutting

- [X] T022 Update the skill list in `README.md` to include `edit` and the audit's usage.
- [X] T023 Run `tools/check.sh`. Lint, format, markdown, shell, and all unit tests must pass.
- [X] T024 Run quickstart scenarios 1 to 5 on a scratch repo and record each result in `specs/003-policy-plugin-gaps/quickstart.md`, or report any scenario that fails.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: no dependency. Blocks US2 and US3 (they need `validate_statement`). US1 is not blocked by it.
- **US1, US4, US5, US6**: start after Phase 2. They do not depend on each other.
- **US2**: starts after Phase 2.
- **US3**: starts after US2 (same script).
- **Polish**: starts after all stories.

### Story Dependencies

- US1: independent. MVP.
- US2: depends on Phase 2 only.
- US3: depends on US2.
- US4: independent of the others.
- US5: independent, but T018 depends on T017.
- US6: T021 depends on T001.

### Parallel Opportunities

- T003 (US1 tests) can run alongside T006 (US2 tests): different files.
- T014 (tracker) and T016 (audit SKILL.md) are marked [P]; T015 waits on T013 and T014.
- US1, US4, and US5 can run in parallel with US2 once Phase 2 is done.

### Parallel Example: after Phase 2

```text
Task: "T003 [P] [US1] Write tests/test_record_sync.py"
Task: "T006 [P] [US2] Write tests/test_edit_rule.py (single-rule cases)"
Task: "T014 [P] [US4] Implement skills/audit/scripts/github_tracker.py"
Task: "T020 [P] [US6] Document parse() in specs/001-.../contracts/policy_frontmatter.md"
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 2: Foundational (T001 to T002). It is small, and US2 needs it.
2. Phase 3: US1 (T003 to T005).
3. **Stop and validate** with quickstart scenario 1.

### Incremental delivery

1. Foundational, then US1 (MVP: sync recording).
2. US2, then US3 (edit path, bulk).
3. US4 (audit).
4. US5 and US6 (discovery and docs).
5. Polish.

---

## Notes

- [P] = different files, no dependency on an incomplete task
- Commit after each phase, using the speckit hooks as already configured in this project
- Every test is written and seen to fail before its implementation
- Do not touch derived docs (`CONTRIBUTING.md`, `CLAUDE.md`, `.claude/rules/`) from any script
- The branch is behind `main` (PR #5 merged after it was cut). Merge `main` before T001

## Phase 9: Convergence

- [X] T025 Verify in a fresh session that `${CLAUDE_PLUGIN_ROOT}` resolves inside SKILL.md text, and record the result in `specs/003-policy-plugin-gaps/research.md` under R7 per FR-017, SC-006 (partial)
- [X] T026 Make `record_sync` in `skills/sync/scripts/record_sync.py` refuse to write a rule that changed between its read and its write, so a concurrent edit is not lost per Edge Cases (concurrent syncs) (partial)
- [X] T027 Make `run_audit` in `skills/audit/scripts/audit_checks.py` keep checking the remaining rules after a tracker failure, log each failure, and exit 1 at the end per Edge Cases (tracker unavailable) (partial)
- [X] T028 Document `title` and `rationale` as intentional `edit` fields in `specs/003-policy-plugin-gaps/spec.md` FR-004, or remove them from `skills/edit/scripts/edit_rule.py` per FR-004 (unrequested)

## Phase 10: Convergence

- [X] T029 Hold an exclusive lock across the read, compare, and write in `write_if_unchanged` in `skills/sync/scripts/record_sync.py`, so a concurrent edit cannot land between the check and the replace per Edge Cases (concurrent syncs) (partial)

## Phase 11: Convergence

- [X] T030 Add the lock-timeout case (exit 1, nothing written) to the exit-code tables in `specs/003-policy-plugin-gaps/contracts/record_sync.md` and `specs/003-policy-plugin-gaps/contracts/edit_rule.md` per T029 (partial)
- [X] T031 Document the `.write.lock` file in `specs/003-policy-plugin-gaps/data-model.md`, and in the Conventions section of `README.md`, including that the lock is advisory and that consuming repos may want to gitignore it per T029 (unrequested)
