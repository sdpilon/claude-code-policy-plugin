# Tasks: Policy Init and Safe Update

**Input**: Design documents from `/specs/002-policy-init-update/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Execution is inline with TDD: write the failing test first, see it fail, then implement.

**Run tests with**: `python3 -m unittest discover -s tests` from the repo root. pytest is not installed; do not install it.

**Organization**: Tasks are grouped by user story. Foundational work (the shared manifest module) blocks all stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (init), US2 (update), US3 (fail closed)
- Every description names an exact file path

## Path Conventions

- Shared logic: `scripts/policy_manifest.py`
- Skill scripts: `skills/init/scripts/init_policy.py`, `skills/update/scripts/update_policy.py`
- Skills: `skills/init/SKILL.md`, `skills/update/SKILL.md`
- Shipped template: `templates/policy-readme.md`
- Tests: `tests/test_policy_manifest.py`, `tests/test_init_policy.py`, `tests/test_update_policy.py`

## Phase 1: Setup

**Purpose**: Confirm the baseline before changing anything.

- [X] T001 Run `python3 -m unittest discover -s tests` from the repo root and confirm it passes (47 tests) before any change. Record the count in the commit message of the first implementation commit.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared module every skill script imports. No user story can start until this phase is green.

**Constraints quoted from `data-model.md` and `contracts/manifest.md`**:
- `format_version` is an integer; this feature writes `1`; a value greater than `1` is "needs a newer plugin"; missing or non-integer is "corrupt".
- `sha256` is "64 lowercase hex characters".
- `files` keys are "project-relative paths using forward slashes".
- Classification states are exactly: `current`, `stale`, `customized`, `missing`, `no-longer-shipped`, `new`, `user-owned`.

- [X] T002 [P] Write failing tests in `tests/test_policy_manifest.py` for `fingerprint(path)`: a file with LF and the same content with CRLF produce identical digests; the digest is 64 lowercase hex characters; a non-UTF-8 file's digest is taken over its raw bytes.
- [X] T003 Implement `fingerprint(path)` in `scripts/policy_manifest.py` using `hashlib.sha256`, replacing every `\r\n` with `\n` after a UTF-8 decode, and falling back to raw bytes on `UnicodeDecodeError`. Make T002 pass.
- [X] T004 [P] Write failing tests in `tests/test_policy_manifest.py` for `load_manifest(path)` and `write_manifest(path, data)`: a round trip preserves `format_version`, `plugin_version`, and `files`; a missing file raises `ManifestError` with the message naming `/policy:init`; invalid JSON raises `ManifestError` naming the manifest path; `format_version` 99 raises `ManifestError` with a "newer plugin" message; a missing `format_version` raises `ManifestError`; an entry without `sha256` raises `ManifestError`.
- [X] T005 Implement `ManifestError`, `load_manifest`, and `write_manifest` in `scripts/policy_manifest.py`. `write_manifest` writes to a temporary file in the same directory and calls `os.replace`, and writes JSON with two-space indentation and a trailing newline. Make T004 pass.
- [X] T006 [P] Write failing tests in `tests/test_policy_manifest.py` for `plugin_version()`: it returns the `version` field of `.claude-plugin/plugin.json` in the repo, not a hard-coded value.
- [X] T007 Implement `plugin_version()` in `scripts/policy_manifest.py`, resolving the plugin root from the module's own path. Make T006 pass.
- [X] T008 Write failing tests in `tests/test_policy_manifest.py` for `classify(entry, file_bytes_hash, template_hash, exists)`, one case per row of `data-model.md`'s classification table: `current`, `stale`, `customized`, `missing`, `no-longer-shipped`, `new`, `user-owned`. Include the case where an entry exists and the file's hash matches but the template hash differs, which must return `stale`.
- [X] T009 Implement `classify` in `scripts/policy_manifest.py`. Make T008 pass.
- [X] T010 [P] Write a failing test in `tests/test_policy_manifest.py` for `unified_diff(project_text, template_text, name)`: it returns a `difflib.unified_diff` string whose header names the file and "shipped" side. Implement it and make the test pass.

**Checkpoint**: `python3 -m unittest discover -s tests` is green and `scripts/policy_manifest.py` has no imports outside the standard library.

---

## Phase 3: User Story 1 - Bootstrap policy in a new project (Priority: P1) 🎯 MVP

**Goal**: `/policy:init` creates the skeleton and manifest; it never overwrites.

**Independent Test**: In an empty temp directory, run `init_policy.py`; the four skeleton paths exist, the manifest records the README's fingerprint, and `add_rule.py` can then create rule `001`.

### Tests for User Story 1

- [ ] T011 [US1] Write failing tests in `tests/test_init_policy.py`: in a fresh temp dir, `init_policy.py` creates `.policy/rule/`, `.policy/retired/`, `.policy/README.md`, and `.policy/manifest.json`, exits `0`, and the manifest has `format_version` `1`, `plugin_version` equal to `plugin_version()`, and a `.policy/README.md` entry whose `sha256` equals `fingerprint` of the written file.
- [ ] T012 [US1] Add a failing test in `tests/test_init_policy.py`: after init, running `skills/add/scripts/add_rule.py` with a valid statement creates a rule with ID `001` under `.policy/rule/`.
- [ ] T013 [US1] Add a failing test in `tests/test_init_policy.py`: running init a second time on an initialized project prints `already initialized`, exits `0`, and leaves every byte under `.policy/` unchanged (compare hashes before and after).
- [ ] T014 [US1] Add a failing test in `tests/test_init_policy.py`: when `.policy/README.md` already exists and no manifest exists, init prints `user-owned: .policy/README.md (not tracked)`, leaves the README bytes unchanged, and writes a manifest with no entry for it.

### Implementation for User Story 1

- [ ] T015 [P] [US1] Create `templates/policy-readme.md`: a short, generic description of the `.policy/` convention (rule files, IDs, tombstones, derived docs). It must contain no project-specific content (Constitution I). Tests in T011 depend on it.
- [ ] T016 [US1] Implement `skills/init/scripts/init_policy.py`: resolve the repo root as the current directory, create the directories, write the README from `templates/policy-readme.md` only when no file exists at that path, write the manifest with `format_version` `1`, and print one line per action. Make T011, T012, T013, and T014 pass.
- [ ] T017 [P] [US1] Create `skills/init/SKILL.md` with frontmatter `name: init` and a description that triggers on requests to set up or bootstrap policy in a repo, and not on adding a rule. The body runs `python3 <plugin>/skills/init/scripts/init_policy.py` as described in `README.md`'s "Paths in skills" section.

**Checkpoint**: US1 is independently testable. Stop here and run quickstart S1 and S2 by hand.

---

## Phase 4: User Story 2 - Update shipped templates without overwriting customizations (Priority: P2)

**Goal**: `/policy:update` applies unmodified stale files, reports customized, missing, and no-longer-shipped files, and exits with the contract's codes.

**Independent Test**: Init a project, change the manifest to simulate an older shipped version, run update; the spec's update table holds row by row.

### Tests for User Story 2

- [ ] T018 [US2] Write failing tests in `tests/test_update_policy.py` covering the update table, one test per row, each starting from an init'd temp project:
  - row 1 (stale): manifest `sha256` set to the current file hash and `shipped_version` set to `0.1.0`; expect `updated: .policy/README.md`, the file equal to the template, the manifest at the current `plugin_version`, exit `0`.
  - row 2 (customized): append a line to the README; expect `customized: .policy/README.md`, a unified diff in output, the file byte-identical to before, exit `1`.
  - row 3 (missing): delete the README; expect `missing: .policy/README.md`, the file still absent, exit `1`.
  - row 4 (no-longer-shipped): add a manifest entry for `.policy/old-file.md` with a valid `sha256` and create the file; expect `no-longer-shipped: .policy/old-file.md`, the file kept, exit `0`.
  - row 5 (new, absent): remove the README and its manifest entry; expect the file created and an entry added, exit `0`.
  - row 5 (new, present): remove the README's manifest entry but keep the file with edited content; expect `user-owned: .policy/README.md`, the file unchanged, exit `0`.
- [ ] T019 [US2] Add a failing test in `tests/test_update_policy.py` for SC-004: convert the init'd README to CRLF with otherwise identical content; expect `current` for the README, not `customized`, exit `0`.
- [ ] T020 [US2] Add a failing test in `tests/test_update_policy.py`: two consecutive updates with no plugin change produce no writes on the second run (compare hashes) and no `updated` lines.
- [ ] T021 [US2] Add a failing test in `tests/test_update_policy.py` that a run where a customized file exists prints a summary line `summary: ... customized` and returns exit `1`.

### Implementation for User Story 2

- [ ] T022 [US2] Implement `skills/update/scripts/update_policy.py`: load the manifest via `load_manifest`, classify every tracked entry and every shipped template with `classify`, apply only `stale` and `new`-absent actions using `write_manifest` for the manifest and atomic writes for files, print the grouped report from `contracts/commands.md`, print diffs for `customized` files via `unified_diff`, print the summary line, and exit with `0`, `1`, or `2` per `research.md` §5. Make T018 through T021 pass.
- [ ] T023 [P] [US2] Create `skills/update/SKILL.md` with frontmatter `name: update` and a description that triggers on requests to update or sync shipped policy templates, and not on adding rules or running the audit. The body invokes `python3 <plugin>/skills/update/scripts/update_policy.py` and explains the report states.

**Checkpoint**: US2 is independently testable. Run quickstart S4 through S9 by hand.

---

## Phase 5: User Story 3 - Recover safely from a broken manifest (Priority: P3)

**Goal**: A missing, corrupt, or too-new manifest stops update with exit `2` and changes nothing.

**Independent Test**: Break the manifest three ways; update exits `2` each time with the recovery message and no file changes.

### Tests for User Story 3

- [ ] T024 [US3] Write failing tests in `tests/test_update_policy.py`: with the manifest deleted, update exits `2`, prints a message naming `/policy:init`, and every file's hash is unchanged.
- [ ] T025 [US3] Add a failing test in `tests/test_update_policy.py`: with the manifest set to `{ not json`, update exits `2`, names the manifest path, and changes nothing.
- [ ] T026 [US3] Add a failing test in `tests/test_update_policy.py`: with the manifest set to `{"format_version": 99, "plugin_version": "9.9.9", "files": {}}`, update exits `2` with a "newer plugin" message and changes nothing.

### Implementation for User Story 3

- [ ] T027 [US3] Add the fail-closed path in `skills/update/scripts/update_policy.py`: catch `ManifestError` around the manifest load, print its message to stderr, and exit `2` before any classification or write. Make T024 through T026 pass.

**Checkpoint**: All three stories pass independently. Run `python3 -m unittest discover -s tests`.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [ ] T028 [P] Change `ROADMAP.yaml` entry `init-and-safe-update` from `status: deferred` to `status: in-progress`.
- [ ] T029 [P] Change `version` from `0.1.0` to `0.2.0` in `.claude-plugin/plugin.json`, and the matching plugin version in `.claude-plugin/marketplace.json`.
- [ ] T030 [P] Update `README.md`: add `/policy:init` and `/policy:update` to the Skills list; add a short "Manifest" bullet under Conventions describing `.policy/manifest.json`; update the Status line to `0.2.0`. Describe the current state only, with no changelog wording (Constitution, Development Workflow).
- [ ] T031 Run the full suite with `python3 -m unittest discover -s tests` and confirm it passes.
- [ ] T032 Validate `init` and `update` skill descriptions with fresh, context-free subagents, following the Constitution's trigger-test gate: for each skill, at least one positive request (for example "set up policy in this repo" for init; "update the policy templates" for update) and one adjacent negative request (for example "add a rule" for init; "run the audit" for update). Subagents report only whether they invoked the skill, and which one.
- [ ] T033 Run quickstart S1 through S11 end-to-end in a scratch directory (`mktemp -d`), never in a real project, and record each result.

---

## Dependencies & Execution Order

- **Phase 1** has no dependencies.
- **Phase 2** depends on Phase 1 and blocks everything else.
- **US1** depends on Phase 2. Its tests use the real `add_rule.py` from T012.
- **US2** depends on Phase 2, and its test fixtures use init from US1; start it after T016 is green.
- **US3** depends on US2's `update_policy.py` existing (T022). Its tests are independent in content, but the code path lives in the same file.
- **Polish** depends on all three stories.

### Parallel Opportunities

- Within Phase 2: T002, T004, T006, and T010 touch the same test file, so they are written in sequence; implementations T003, T005, T007, and T009 each depend on their test.
- T015 and T017 (US1) touch different files and can run together after T011 is written.
- T023 can run in parallel with the US2 implementation once T018 is written.
- T028, T029, and T030 touch different files and can run together.

## Implementation Strategy

**MVP**: Phase 1, Phase 2, and US1 (Phases 1–3). That delivers `/policy:init` and a working manifest.

**Incremental**: add US2 (safe update), then US3 (fail-closed hardening), then Polish. Each story leaves the suite green before the next begins.

**Stop points**: after each checkpoint, run the suite and the matching quickstart scenarios before continuing.
