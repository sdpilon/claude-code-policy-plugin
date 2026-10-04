# Feature Specification: Policy Plugin Gaps

**Feature Branch**: `003-policy-plugin-gaps`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Close the gaps that the riposte migration session hit in the policy plugin, excluding anything about migration: a command that writes synced_hash back after a sync, an edit path that refreshes modified and synced_hash together, a bulk-edit path, a runnable audit script that files and dedupes issues for ci-checked rules, plugin path discovery, and documentation of the frontmatter parse return type. Migration is out of scope; it is removed in a later spec."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Record a sync without hand-written hashes (Priority: P1)

After a sync proposal is approved and the derived docs are updated, the maintainer (or the agent acting for them) records that each applied rule is now in sync. The plugin writes the computed `synced_hash` into each rule's frontmatter in one step, so no one has to script the write-back or repeat it after each rule edit.

**Why this priority**: Without it, every sync leaves the rule set looking changed, and the write-back has to be scripted by hand. This is the most-repeated manual step in the feedback.

**Independent Test**: In a scratch repository with two rules, run a sync, approve the proposal, record the sync for both rules, and confirm each rule's `synced_hash` matches the hash the sync status reports and that a second status check shows neither rule as changed.

**Acceptance Scenarios**:

1. **Given** rules whose content changed since their last recorded sync, **When** the maintainer records the sync for those rules, **Then** each rule's `synced_hash` equals its current content hash and the sync status reports them as unchanged.
2. **Given** a rule that has not changed since its last sync, **When** the maintainer records a sync for it, **Then** the file is left byte-identical.
3. **Given** a rule ID that does not exist, **When** the maintainer records a sync for it, **Then** the command fails with a message naming the ID and writes nothing.

---

### User Story 2 - Edit a rule without stale dates or hashes (Priority: P2)

A maintainer changes a rule's statement, tags, audience, or verification fields through one edit operation. The operation updates `modified` to the current time and, when the edit is part of an approved sync, the `synced_hash` is handled consistently, so the modified date and sync state never disagree with the file.

**Why this priority**: Hand edits left `modified` stale and forced a manual re-sync. One edit path fixes that for every later change.

**Independent Test**: Edit one rule's statement through the edit operation and confirm `modified` moves forward, the rule still passes validation, and the sync status shows it as changed until the sync is recorded.

**Acceptance Scenarios**:

1. **Given** an existing rule, **When** the maintainer edits its statement, **Then** `modified` is set to the current UTC time and the file still validates.
2. **Given** an edit that violates the frontmatter contract (for example, an invalid `verification.method`), **When** the maintainer applies it, **Then** the edit is rejected and the file is unchanged.
3. **Given** an edit that would leave a statement with no modal verb or with two modal verbs, **When** the maintainer applies it, **Then** the edit is rejected and the file is unchanged.

---

### User Story 3 - Apply one change to many rules (Priority: P2)

A maintainer applies the same change (for example, adding a shared audience value or replacing a repeated phrase) across a set of rules in a single operation. The operation shows what would change first and applies all edits or none.

**Why this priority**: The feedback needed one change across thirteen rules and had no command for it. It is a multiplier on Story 2.

**Independent Test**: Given a set of three rules, run a bulk change that is valid for all three and confirm all three change; then run one that is invalid for one rule and confirm none change.

**Acceptance Scenarios**:

1. **Given** a set of rules and a change that is valid for each, **When** the maintainer applies the bulk change, **Then** every listed rule is updated with a fresh `modified` date and no other rule is touched.
2. **Given** a bulk change that is invalid for one rule in the set, **When** the maintainer applies it, **Then** no rule is changed and the failing rule and reason are reported.
3. **Given** a bulk change, **When** the maintainer requests a preview, **Then** the per-rule before and after values are shown and no file is written.

---

### User Story 4 - Run the CI audit and file missing checks (Priority: P2)

The CI audit runs the project's own checks for `ci-checked` rules, files one issue for each failing rule that has no open issue, and files an issue for each `ci-checked` rule whose named check does not exist yet. The plugin supplies this dispatch, dedupe, and filing mechanism; each consuming project supplies the checks themselves.

**Why this priority**: Rules without checks had no path to a tracked issue, so the gap was invisible in CI. The audit also needs to dedupe reliably, which the feedback showed depended on titles.

**Independent Test**: In a scratch repository with three `ci-checked` rules (one passing, one failing with an open issue, one with no check defined), run the audit with a fake issue tracker and confirm exactly one new issue is filed, for the rule with no check, and the failing rule is not filed twice.

**Acceptance Scenarios**:

1. **Given** a `ci-checked` rule whose named check does not exist, **When** the audit runs, **Then** exactly one issue is filed for it, and running again files nothing new.
2. **Given** a failing rule that already has an open issue carrying its dedupe key, **When** the audit runs, **Then** no new issue is filed, even if the rule's title has changed.
3. **Given** a rule marked with a `defect`, **When** the audit runs, **Then** the rule is skipped and logged, not checked or filed.
4. **Given** the audit runs, **When** it finishes, **Then** it logs one line per rule (pass, filed, or skipped) and does not fail the build because a rule is unverifiable.

---

### User Story 5 - Find the plugin's scripts without searching (Priority: P3)

An agent running a plugin skill can resolve the plugin's root directory and the path to any of its scripts from a single documented rule or command, without searching the filesystem.

**Why this priority**: It saves time on every run but does not change any output, so it follows the functional work.

**Independent Test**: From a fresh session in a repository that uses the plugin, resolve the plugin root and run one script by its resolved path, without any manual search.

**Acceptance Scenarios**:

1. **Given** the plugin is installed at project scope, **When** an agent resolves the plugin root by the documented method, **Then** the resolved path contains `skills/` and `scripts/`.
2. **Given** the resolved root, **When** the agent runs a bundled script by path, **Then** the script runs without the agent locating it by search.

---

### User Story 6 - Know what the frontmatter parser returns (Priority: P3)

A skill author or agent reading the frontmatter parser's contract can see, without reading its source, what it returns, what it raises, and how absent fields appear.

**Why this priority**: Documentation only; it removes a defensive workaround the feedback had to add.

**Independent Test**: A reader who has only the skill and contract docs can state the parse return type and the error raised for a file with no frontmatter.

**Acceptance Scenarios**:

1. **Given** the contract documentation, **When** a reader looks up the parse function, **Then** the documented return type is a dictionary of string keys, and the documented error is the frontmatter error for a missing or malformed block.

---

### Edge Cases

- A rule is edited and recorded as synced in the same run: the recorded hash must match the content after the edit, not before.
- Two sync recordings run at once on the same rule: the second must not silently overwrite a hash that a concurrent edit has changed; the rule's current content hash is what is recorded.
- A bulk change touches a rule that has a `defect` set: the rule is reported and excluded, not silently changed.
- The audit runs with no network or no issue-tracker access: it logs and exits without failing unrelated checks.
- An issue exists with the dedupe key but is closed: the audit files a new one only if the rule still fails.
- A rule's ID is retired between preview and apply of a bulk change: the apply fails for the whole set.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The plugin MUST provide a command that writes each named rule's current computed content hash into that rule's `synced_hash` field.
- **FR-002**: The record-sync command MUST NOT change any rule file whose `synced_hash` already matches its content.
- **FR-003**: The record-sync command MUST fail without writing anything when a named rule does not exist.
- **FR-004**: The plugin MUST provide an edit operation for an existing rule that updates the statement, tags, audience, or verification fields.
- **FR-005**: The edit operation MUST set `modified` to the current UTC time when it changes a rule.
- **FR-006**: The edit operation MUST reject any change that leaves the rule failing the frontmatter contract or the one-sentence, one-modal-verb rule, and MUST leave the file unchanged on rejection.
- **FR-007**: The plugin MUST provide a bulk-change operation that applies one change to a named set of rules.
- **FR-008**: The bulk-change operation MUST apply all changes or none; a failure for any rule MUST leave every rule in the set unchanged and report the failing rule and reason.
- **FR-009**: The bulk-change operation MUST offer a preview mode that prints each rule's before and after values and writes nothing.
- **FR-010**: The plugin MUST ship a runnable audit script that runs the `ci-checked` rules' checks through a project-supplied check registry; the plugin MUST NOT ship any project's check implementations.
- **FR-011**: The audit script MUST file one issue for each failing `ci-checked` rule that has no open issue carrying that rule's dedupe key.
- **FR-012**: The audit script MUST file one issue for each `ci-checked` rule whose named check does not exist in the registry.
- **FR-013**: The audit script MUST stamp every issue it files with a dedupe key that is independent of the rule's ID and title, and MUST document that key.
- **FR-014**: The audit script MUST skip and log, not check or file, any rule with a `defect` set.
- **FR-015**: The audit script MUST log one line per rule (pass, filed, or skipped) and MUST NOT fail the build because a rule is unverifiable.
- **FR-016**: The audit script MUST NOT close any issue.
- **FR-017**: The plugin's documentation MUST state one documented method for an agent to resolve the plugin root and the path to a bundled script.
- **FR-018**: The skill and contract documentation for the frontmatter parser MUST state its return type, its error for a missing or malformed frontmatter block, and how an empty value is represented.
- **FR-019**: The sync skill MUST replace its manual `synced_hash` write-back instruction with a reference to the record-sync command.
- **FR-020**: The plugin MUST keep its existing single-rule commands (add, retire, status, sync check, judge, init, update) behaving as they do today.

### Key Entities

- **Rule**: One file under `.policy/rule/`, holding one sentence, its tags, audience, verification fields, `modified`, and `synced_hash`.
- **Sync record**: The `synced_hash` value on a rule, equal to the rule's content hash at the time of its last recorded sync.
- **Check registry**: The consuming project's mapping from a `verification.via` name to the check that verifies it.
- **Audit issue**: An issue the audit files, identified by a dedupe key that survives title and ID changes.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A maintainer can record a sync for any number of rules in one step, with no hand-written scripts, and a follow-up status check shows zero rules as changed.
- **SC-002**: A rule edit through the edit operation always leaves `modified` at or after the edit time, and an invalid edit leaves the file byte-identical.
- **SC-003**: A bulk change across ten rules takes one command, and a failure on any one rule leaves all ten unchanged.
- **SC-004**: Running the audit twice in a row files zero new issues on the second run when no rule's status has changed.
- **SC-005**: Every `ci-checked` rule with no named check results in exactly one open audit issue after one audit run.
- **SC-006**: An agent resolves the plugin root and runs one bundled script in a fresh session without searching the filesystem.
- **SC-007**: A reader of the contract documentation can state the parser's return type and error without opening its source.

## Assumptions

- The migrate feature is out of scope and is removed in a later spec; no requirement here depends on it.
- The cutover of any consuming repository is out of scope; this spec changes only the plugin.
- Per-consumer retitling of existing issues is out of scope; the new dedupe key makes it unnecessary for new issues.
- Each consuming project supplies its own check registry, consistent with Principle I (no project content in shipped files). The plugin ships the dispatch, dedupe, and filing mechanism only.
- The issue tracker used by the audit is the consuming project's; the plugin requires only that the project's script provides issue search and filing.
- Tests for the new commands follow the repository's existing unittest layout and run in CI.
- The record-sync, edit, and bulk-change operations are deterministic scripts, not LLM steps, per Principle IV.
