---

description: "Task list template for feature implementation"
---

# Tasks: One-Rule-Per-File Restructuring

**Input**: Design documents from `/specs/001-rule-per-file-restructure/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context and research.md Decision 4 already
commit this feature to `unittest` coverage for its new deterministic logic; this is
the plugin's first test suite.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- File paths are exact, matching plan.md's Project Structure

## Path Conventions

Single project. Shared logic lives in repo-root `scripts/`; each skill keeps its own
`skills/<name>/scripts/`; tests live in repo-root `tests/`. See plan.md's Project
Structure for the full tree.

---

## Phase 1: Setup

**Purpose**: Directory scaffolding this feature's scripts land in.

- [ ] T001 Create the shared `scripts/` directory and `tests/` directory (with
  `tests/__init__.py`). Decide and document, as a short comment at the top of
  `scripts/policy_ids.py` and `scripts/policy_frontmatter.py` (written in T003/T004),
  how a script under `skills/<name>/scripts/` locates and imports the shared
  `scripts/` library (e.g. walking up from the script's own path to find the repo
  root, the same pattern `.specify/extensions/git/scripts/bash/create-new-feature-branch.sh`
  already uses to locate `common.sh`).
- [ ] T002 [P] Create empty `skills/add/scripts/`, `skills/sync/scripts/`, and
  `skills/migrate/scripts/` directories.

**Checkpoint**: Directory layout matches plan.md's Project Structure.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two shared scripts every story's implementation calls into.

**⚠️ CRITICAL**: No user story task can begin until this phase is complete.

- [ ] T003 [P] Implement `scripts/policy_frontmatter.py` per
  `contracts/policy_frontmatter.md` — `parse`, `validate`, `render`, and the `read`/
  `validate` CLI subcommands. Enforce data-model.md's Rule frontmatter schema exactly:
  `title` required string; `tags` optional list of strings, default `[]`; `created`
  and `modified` required ISO 8601 timestamps; `audience` required **non-empty** list
  restricted to `{human, agent}`; `verification` required mapping whose `method` is
  restricted to `{ci-blocking, ci-checked, human-verified, written-only}` with a
  free-text `via`; `synced_hash` optional sha256-hex string or absent. No third-party
  dependency (research.md Decision 1).
- [ ] T004 [P] Implement `scripts/policy_ids.py` per `contracts/policy_ids.md` —
  `highest_id(rule_root, retired_root)` (recursive scan of both directories, tombstones
  included, returns `0` on an empty/missing tree), `format_id` (zero-pad to a minimum of
  three digits, growing beyond that as needed, e.g. `47 -> "047"`, `1000 -> "1000"`),
  `parse_id` (inverse of `format_id`, tolerating padded or unpadded input),
  `allocate_id(rule_root, retired_root, reserve)` (scan-then-recheck-before-write with
  bounded retry, skipping any ID that has a tombstone, no lock file), and the `highest`
  CLI subcommand with `--dir`, `--retired-dir`, and a `highest_formatted` field in its
  output.
- [ ] T005 [P] Write `tests/test_policy_frontmatter.py`: round-trip `parse` → `render`
  preserves key order; `validate` fails when `audience` is missing or empty; `validate`
  fails when `audience` contains a value outside `{human, agent}`; `validate` fails
  when `verification.method` is outside the four enumerated values; `parse` raises
  `FrontmatterError` on a file with no frontmatter block (CLI exit code `2`).
- [ ] T006 [P] Write `tests/test_policy_ids.py`: `highest_id` returns `0` on an empty or
  missing tree; finds the correct maximum regardless of organizational-subdirectory depth
  (FR-005) and zero-padding width; counts tombstones, so the maximum never drops after a
  retirement (FR-004); `format_id` zero-pads to three digits and grows without re-padding
  (`1000 -> "1000"`); `parse_id` round-trips `format_id`'s output and accepts unpadded
  digits; `allocate_id` skips any ID that has a tombstone; `allocate_id` retries past a
  reservation collision and raises after a bounded number of failed attempts.

**Checkpoint**: Both shared scripts exist and pass their tests — every user story can
now proceed.

---

## Phase 3: User Story 1 - Add a rule without picking a topic file (Priority: P1) 🎯 MVP

**Goal**: `/policy:add` writes a new rule to its own file with a permanent, unique ID,
never requiring a topic-file decision.

**Independent Test**: Run `add_rule.py` twice for two unrelated rules; confirm two
separate files with different IDs, neither modifying the other.

### Tests for User Story 1

- [ ] T007 [P] [US1] Write `tests/test_add_rule.py`: a successful call returns
  `{"id", "path"}` matching `contracts/add_rule.md`; a missing or invalid `--audience`
  exits `2` and writes no file; an invalid `--verification-method` exits `2` and
  writes no file; two sequential calls never collide on ID.

### Implementation for User Story 1

- [ ] T008 [US1] Implement `skills/add/scripts/add_rule.py` per
  `contracts/add_rule.md`, using `policy_ids.allocate_id` and
  `policy_frontmatter.render` (depends on T003, T004).
- [ ] T009 [US1] Update `skills/add/SKILL.md`: describe writing to
  `.policy/rule/<id>.md` via `add_rule.py` instead of appending to a shared topic
  file; document the required `audience` field and the four `verification.method`
  values; rename "obligation" → "rule" throughout (research.md Decision 5).

**Checkpoint**: Adding a rule never requires a topic decision — User Story 1 is fully
functional and independently testable.

---

## Phase 4: User Story 2 - Sync a rule to the right derived document (Priority: P2)

**Goal**: `/policy:sync` propagates each rule only to the derived document(s) matching
its declared `audience`, and skips rules unchanged since the last sync.

**Independent Test**: One rule with `audience: [human]`, one with `audience: [agent]`;
run sync; confirm each appears only in its matching derived document.

### Tests for User Story 2

- [ ] T010 [P] [US2] Write `tests/test_sync_status.py`: a rule with no `synced_hash` is
  always `"changed": true`; `"changed"` is `false` only when `current_hash == synced_hash`;
  `targets` follows `audience` exactly (`human` → `CONTRIBUTING.md`; `agent` → `CLAUDE.md`
  and `.claude/rules/<id>.md`; both audiences → both sets, and a human-only rule never
  lists an agent target); a rule that fails frontmatter validation is included with
  `"changed": true` and an added `"error"` field (per `contracts/sync_status.md`).

### Implementation for User Story 2

- [ ] T011 [US2] Implement `skills/sync/scripts/sync_status.py` per
  `contracts/sync_status.md`, including the mechanically derived `targets` list
  (depends on T003, T004).
- [ ] T012 [US2] Update `skills/sync/SKILL.md`: read `sync_status.py`'s output and use each
  rule's `targets` list as the only source for which derived documents it updates (no
  inferring from `audience`); skip any rule reported `"changed": false` (FR-008); after an
  approved propagation, write the new `synced_hash` back into that rule's frontmatter via
  `policy_frontmatter.render`; rename "obligation" → "rule" throughout.

**Checkpoint**: Sync no longer infers audience — User Story 2 is independently
testable without User Story 1 being complete.

---

## Phase 5: User Story 3 - See what a rule is without opening it (Priority: P3)

**Goal**: `/policy:status` and `/policy:audit` show each rule's human-readable title
and read its enforcement tier from frontmatter instead of an inline comment.

**Independent Test**: Run status against a tree of numbered rule files with titles;
confirm the output lists ID and title together, with tier sourced from frontmatter.

### Tests for User Story 3

- [ ] T013 [P] [US3] Write `tests/test_policy_status.py`: the scan finds rules nested under
  organizational subdirectories and also works on a flat `.policy/rule/` (FR-014); a
  zero-padded bare-integer line (`**047**:`) matches, an old-style prefixed line
  (`**SEC-7**:`) does not, and files directly under `.policy/` are ignored; a captured ID
  string parses to a plain integer regardless of leading zeros; `tier`/`via` come from the
  `verification` frontmatter field, not an inline comment; a rule with no `verification`
  field (or an out-of-enum `method`) reports `tier: "unclassified"`; a rule with no
  `audience` is reported as `"defect": "audience missing"`; an ID gap with no tombstone is
  listed under `"gaps"`, and a gap covered by a tombstone is not (FR-017); every output row
  includes `title` (per `contracts/policy_status.md`).

### Implementation for User Story 3

- [ ] T014 [US3] Update `skills/status/scripts/policy_status.py`: recursive walk of
  `.policy/rule/`; replace `OBLIGATION_RE` with a bare-integer pattern and parse the
  captured digits via `scripts/policy_ids.py`'s `parse_id`; replace the inline
  `<!-- tier: ...; via: ... -->` read with `policy_frontmatter.parse`'s `verification`
  field; add `title` to each output row; report missing-audience defects and ID gaps
  (checking `.policy/retired/` as well) per `contracts/policy_status.md` (depends on T003,
  T004). `policy-status.sh`'s wrapper shape is unchanged.
- [ ] T015 [US3] Update `skills/status/SKILL.md` and `skills/audit/SKILL.md`:
  describe the new `.policy/rule/` layout, the frontmatter-sourced `verification`
  field, and `title` appearing in status output; rename "obligation" → "rule"
  throughout both.

**Checkpoint**: A numbered rule file is identifiable without opening it — User Story 3
is independently testable.

---

## Phase 6: User Story 4 - Migrate an existing repo's rules (Priority: P2)

**Goal**: `/policy:migrate` mechanically splits an existing repo's topic files into
the new layout, flagging rather than guessing at anything that needs a human decision.

**Independent Test**: A sample repo with two topic files / five obligations,
including one pair that shared a rationale; confirm five new files, with the shared
pair flagged rather than silently duplicated or dropped.

### Tests for User Story 4

- [ ] T016 [P] [US4] Write `tests/test_migrate_rules.py`: every bolded obligation in a
  sample topic file produces exactly one new rule file with a freshly allocated ID;
  a pair that shared one rationale paragraph is reported under one
  `shared_rationale_group` in `needs_review` rather than duplicated or dropped; every
  migrated rule appears in `needs_review` for missing `audience`; `--dry-run`
  produces the same report without writing any file; a source file with no
  detectable `##` section boundaries still migrates its rules and adds the
  "could not determine section boundaries" reason (per `contracts/migrate_rules.md`).

### Implementation for User Story 4

- [ ] T017 [US4] Implement `skills/migrate/scripts/migrate_rules.py` per
  `contracts/migrate_rules.md` (depends on T003, T004).
- [ ] T018 [US4] Create `skills/migrate/SKILL.md` (new skill, exposed as
  `/policy:migrate`): run `migrate_rules.py`, then walk the user through every
  `needs_review` entry as a guided cleanup pass (Constitution Principle III) rather
  than treating a successful mechanical split as the finished job.

**Checkpoint**: An existing topic-file repo can be migrated with nothing lost and
every ambiguous case flagged — User Story 4 is independently testable.

---

## Phase 7: User Story 5 - Retire a rule without losing its ID (Priority: P2)

**Goal**: `/policy:retire` removes a rule from the live set and leaves a tombstone, so its
ID is never reissued (FR-004, FR-016) and the retirement is recorded with a reason.

**Independent Test**: Retire one rule with a reason. Confirm its file is gone from
`.policy/rule/`, a tombstone exists at `.policy/retired/<id>.md`, and the next allocation
returns an ID above the retired one.

### Tests for User Story 5

- [ ] T019 [P] [US5] Write `tests/test_retire_rule.py`: retiring an existing rule writes
  `.policy/retired/<fmt>.md` with frontmatter `id`, `title` (copied), `retired` (ISO date),
  `reason`, and optional `superseded_by`, then removes the rule file; a missing rule exits
  `1` with no writes; an existing tombstone for the ID exits `1` with no writes; an empty
  `--reason` exits `2`; the tombstone is written before the rule file is removed, so a
  failure between the two steps leaves a duplicate rather than a gap (per
  `contracts/retire_rule.md`).

### Implementation for User Story 5

- [ ] T020 [US5] Implement `skills/retire/scripts/retire_rule.py` per
  `contracts/retire_rule.md`, using `policy_frontmatter.render` and `policy_ids.format_id`
  (depends on T003, T004).
- [ ] T021 [US5] Create `skills/retire/SKILL.md` (new skill, exposed as `/policy:retire`):
  before running `retire_rule.py`, ask the person for the reason and any `superseded_by`
  via `AskUserQuestion` (Constitution Principle III checkpoint); report the tombstone path
  afterward. Use "rule" terminology throughout.

**Checkpoint**: A retired rule's ID is never reissued, and the retirement is recorded —
User Story 5 is independently testable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Work that spans every story rather than belonging to one.

- [ ] T022 [P] Replace `templates/policy-template.md` with `templates/rule-template.md`:
  a zero-padded bare-numeric-ID placeholder (e.g. `047`, no alphabetic prefix), the
  full frontmatter block, a short `#` title heading, and room for "See also" links in
  the rationale, matching data-model.md's Rule schema.
- [ ] T023 [P] Update `skills/judge/SKILL.md` to describe the new
  `.policy/rule/<id>.md` convention when handing a judged-as-policy rule off to
  `/policy:add`.
- [ ] T024 [P] Update `README.md`'s remaining "obligation" references (the Skills
  list and Conventions section) to "rule" and the `.policy/rule/<id>.md` layout.
- [ ] T025 [P] Update `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
  descriptions to drop "obligation" and the old topic-file wording.
- [ ] T026 Run a repo-wide `grep -ri obligation` sweep (excluding
  `.specify/memory/constitution.md` and this feature's own `spec.md`, both
  intentionally excluded per research.md Decision 5) and confirm zero remaining
  matches in plugin-owned files (FR-013). Depends on T009, T012, T015, T018, T022,
  T023, T024, T025.
- [ ] T027 Validate the five changed skill descriptions (`add`, `sync`, `status`,
  `audit`, `judge`) with fresh, context-free subagents against the Constitution's
  Plugin Constraints gate — at least one positive-trigger case per skill and one
  adjacent negative case — before considering the description changes done. Depends
  on T009, T012, T015, T023.
- [ ] T028 Run `quickstart.md`'s five scenarios end-to-end in a scratch directory and
  confirm every pass condition, including the cross-story one (a rule moved into an
  organizational subdirectory is still found by the updated `policy_status.py`).
  Depends on T008, T011, T014, T017.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS every user story.
- **User Stories (Phases 3–7)**: All depend on Foundational completion. US1, US2, and
  US3 have no dependency on each other. US4 and US5 depend only on Foundational, not on
  US1–US3.
- **Polish (Phase 8)**: T022–T025 can start anytime after Setup. T026–T028 depend on
  the relevant story/skill tasks finishing first (see each task's explicit
  dependency line above).

### Within Each User Story

- Tests are written before implementation (T007 before T008, T010 before T011, T013
  before T014, T016 before T017).
- Script implementation before its SKILL.md update (the SKILL.md describes behavior
  the script must already provide).

### Parallel Opportunities

- T003 and T004 (Foundational scripts) in parallel; T005 and T006 (their tests) in
  parallel once written against the contracts (they don't need the implementation to
  exist first, since they test against the documented contract).
- Once Foundational is complete, US1 (T007–T009), US2 (T010–T012), US3 (T013–T015),
  US4 (T016–T018), and US5 (T019–T021) can all proceed in parallel — none depends on another.
- T022–T025 in Polish are mutually independent and parallelizable.

---

## Parallel Example: Foundational Phase

```bash
Task: "Implement scripts/policy_frontmatter.py per contracts/policy_frontmatter.md"
Task: "Implement scripts/policy_ids.py per contracts/policy_ids.md"
# Once both exist:
Task: "Write tests/test_policy_frontmatter.py"
Task: "Write tests/test_policy_ids.py"
```

## Parallel Example: After Foundational Completes

```bash
Task: "US1 — tests/test_add_rule.py + skills/add/scripts/add_rule.py + skills/add/SKILL.md"
Task: "US2 — tests/test_sync_status.py + skills/sync/scripts/sync_status.py + skills/sync/SKILL.md"
Task: "US3 — tests/test_policy_status.py + policy_status.py update + SKILL.md updates"
Task: "US4 — tests/test_migrate_rules.py + skills/migrate/scripts/migrate_rules.py + skills/migrate/SKILL.md"
Task: "US5 — tests/test_retire_rule.py + skills/retire/scripts/retire_rule.py + skills/retire/SKILL.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational — CRITICAL, blocks every story.
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: `add_rule.py` produces unique, never-colliding files with no
   topic decision required.

### Incremental Delivery

1. Setup + Foundational → shared scripts exist and are tested.
2. Add US1 → test independently (MVP: adding a rule needs no topic decision).
3. Add US2 → test independently (sync respects `audience`).
4. Add US3 → test independently (status shows a title and a frontmatter-sourced tier).
5. Add US4 → test independently (an existing repo can be migrated, nothing silently
   resolved).
6. Add US5 → test independently (retiring a rule never lets its ID be reissued).
7. Polish: terminology rename sweep, trigger validation, full quickstart run.

### Parallel Team Strategy

After Foundational is done, five people could take US1 through US5 independently —
no story touches a file another one owns.

---

## Notes

- [P] tasks touch different files and have no incomplete dependency.
- [Story] labels map each task to its spec.md user story for traceability.
- This plugin ships zero tests today; T005/T006/T007/T010/T013/T016/T019 are its first.
- `.specify/memory/constitution.md` is **not** touched by any task here. Its Principle II
  amendment shipped separately as v2.0.0 and v2.0.1 through `/speckit-constitution`.
- Avoid: vague tasks, two stories editing the same file, a story depending on another
  story's completion.
