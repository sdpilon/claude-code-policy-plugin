# Feature Specification: Sync Removal When Audience Drops a Target

**Feature Branch**: `005-sync-audience-removal`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "this problem" (the sync removal gap confirmed on 2026-10-03: changing a rule's `audience` from `[human]` to `[agent]` leaves no removal path for its text in `CONTRIBUTING.md`)

## Clarifications

### Session 2026-10-04

- Q: When sync writes a rule's wording into a derived doc, where should it remember the wording it last wrote, so it can find that old text after the rule is reworded? → A: In the rule's frontmatter, per audience, next to `synced_hash`.
- Q: If someone hand-edits a derived paragraph so it no longer exactly matches the stored wording, what should sync do when it can't find that text to remove? → A: Report "expected text not found in <doc> for rule <id>" and leave it for a person to resolve; propose nothing for it.

- Q: How should a repo like riposte get the wording stored in its rule files, given that its `CONTRIBUTING.md` was written by hand and doesn't match any rule yet? → A: A person copies each existing paragraph into the rule's audience wording once, by hand.

Superseded earlier in this session (design restarted): the bold-ID-token detection and whole-block removal answers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sync reports text that must leave a derived doc (Priority: P1)

A maintainer changes a rule's audience so that one derived document no longer applies to it (for example `[human, agent]` to `[agent]`). When they run `/policy:sync`, the proposal lists the rule's text in the no-longer-targeted document as a removal, with the matched text and the rule ID it comes from, before anything is written.

**Why this priority**: This is the reported defect. Without it, the human-facing doc can lose a rule silently, or keep a stale copy, and nothing in the output says so.

**Independent Test**: Create a rule with `audience: [human, agent]`, sync it, then change its audience to `[agent]`. Run sync and confirm the proposal contains a removal of that rule's text from `CONTRIBUTING.md`, and that `CLAUDE.md` and `.claude/rules/<id>.md` still receive the update.

**Acceptance Scenarios**:

1. **Given** a synced rule whose audience changed from `[human]` to `[agent]`, **When** `/policy:sync` runs, **Then** the proposal lists `CONTRIBUTING.md` as a target to remove the rule's text from, and lists `CLAUDE.md` and `.claude/rules/<id>.md` as targets to update.
2. **Given** a synced rule whose audience did not change, **When** `/policy:sync` runs, **Then** no removal is proposed for it.
3. **Given** a rule whose audience still includes `human` and whose stored `human` wording appears in `CONTRIBUTING.md`, **When** `/policy:sync` runs, **Then** that wording is not proposed for removal.

---

### User Story 2 - Removals are applied only after approval and the record stays consistent (Priority: P2)

After the maintainer approves a removal, the text is removed from the target document, and the rule is recorded as synced so the next run reports it as unchanged. A removal the maintainer declines leaves the document untouched and the rule still reported as changed.

**Why this priority**: The approval checkpoint is required by the constitution (Principle III). The record step has to match what was actually applied, or the rule would show as clean while a derived doc is still wrong.

**Independent Test**: Run the sync flow from User Story 1, approve the removal, record the sync, then run sync again and confirm the rule is unchanged and `CONTRIBUTING.md` no longer contains its text. Repeat with a declined removal and confirm the document is unchanged and the rule is still reported as changed.

**Acceptance Scenarios**:

1. **Given** an approved removal, **When** the change is applied and recorded, **Then** the next sync run reports the rule as unchanged and `CONTRIBUTING.md` no longer contains its text.
2. **Given** a declined removal, **When** the sync flow ends, **Then** `CONTRIBUTING.md` is unchanged and the rule is still reported as changed.
3. **Given** `CONTRIBUTING.md` changed after the proposal was shown, **When** the maintainer approves, **Then** sync re-checks the target and does not apply the removal over the newer content.

---

### Edge Cases

- What happens when a stored wording is found more than once in a document, or not at all? Sync reports it as `ambiguous` or `not_found` and proposes nothing for it (FR-002).
- What happens when `CONTRIBUTING.md` does not exist? No removal is proposed, and the sync report says the target is absent.
- What happens when a rule's audience is emptied or set to an invalid value? The rule is reported as an error (existing behavior), and no removal is proposed for it.
- What happens when a rule is retired? Retirement is a separate flow (`/policy:retire`) and is out of scope here; this feature covers audience changes only.
- What happens when a rule's audience changes from `[agent]` to `[human]`? The new `CONTRIBUTING.md` target is proposed as an addition, as today; no removal is involved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each rule MUST store its wording per audience in its own file, and the last-written wording per audience in its frontmatter next to `synced_hash`. The sync mechanism MUST determine, by script rather than by reading the derived documents with an LLM, which derived documents contain the last-written wording of a rule and are no longer among its targets. It MUST match that wording with whitespace normalized, and MUST treat a match as removable only when it occurs exactly once.
- **FR-002**: `/policy:sync` MUST list each such document in its proposal as a removal of that last-written wording, matched as FR-001 requires, with the rule ID it comes from, and MUST NOT write the removal before approval. When the last-written wording cannot be found in a document that should hold it, sync MUST report it by document and rule ID and MUST NOT propose a removal for it.
- **FR-003**: A rule whose audience changed MUST be reported as changed even when the only change is a dropped target.
- **FR-004**: After approved changes, `record_sync` MUST mark the rule as synced so the next run reports it as unchanged. It MUST write `synced_wording` for the rule's current audiences, verbatim, and MUST remove entries for audiences the rule no longer has. It MUST leave the rest of the rule file unchanged.
- **FR-005**: Sync MUST re-check each target document before applying a removal, consistent with the existing re-check rule for additions and edits.
- **FR-006**: The sync skill's instructions MUST describe the removal step, so the proposal does not depend on the agent deciding on its own to remove text.
- **FR-007**: When a target document is absent, sync MUST report it and MUST NOT create it for a removal.
- **FR-008**: For each addition of a rule's wording to a derived document, the `/policy:sync` proposal MUST state the target section and the position within it, and MUST NOT write the addition before approval. Placement is decided at proposal time and approved with the rest of the change. It is not stored in the rule file.
- **FR-009**: Each audience wording MUST be approved by a person at `add` or `edit` time, under the checkpoint in Principle III. Editing a rule's formal statement MUST prompt review of each audience wording before the edit is written.
- **FR-010**: A rule's `wording` MUST have exactly one entry for each audience in `audience`. Each entry MUST be non-empty and a single line after whitespace is collapsed at write time. Each `synced_wording` entry MUST be a non-empty single line. `/policy:status` MUST report a rule whose `wording` is missing, or does not match its `audience`, as a defect. Its keys MUST be a subset of `human` and `agent`, and MAY name an audience the rule no longer has until `record_sync` prunes it.
- **FR-011**: When sync adds a rule's wording to a derived document, it MUST write only the `wording` for that document's audience, copied verbatim. `CONTRIBUTING.md` takes the `human` wording. `CLAUDE.md` and `.claude/rules/<id>.md` take the `agent` wording.

### Key Entities *(include if feature involves data)*

- **Rule**: One file under `.policy/rule/`. Its `audience` determines its targets. Its stored `wording` and `synced_wording` are what sync writes to, and matches in, derived documents.
- **Derived document**: `CONTRIBUTING.md`, `CLAUDE.md`, or `.claude/rules/<id>.md`. Outputs only; never edited as a source.
- **Removal proposal**: A proposed deletion of one rule's text from one derived document, shown for approval.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test set of audience changes covering every transition between `human`, `agent`, and both, 100% of dropped targets that still contain the rule's text appear in the sync proposal as removals.
- **SC-002**: Zero derived-document edits occur without the maintainer's approval in the sync flow.
- **SC-003**: After an approved removal and record, the next sync run reports 100% of the affected rules as unchanged.
- **SC-004**: A maintainer can tell from the sync output alone which derived document will lose which rule's text, without opening the documents.

## Assumptions

- The fix is in the policy plugin (`skills/sync/`), not in riposte. Riposte is a consumer whose migration feedback raised the issue.
- The removal is a proposal like any other sync change, so it goes through the existing approval checkpoint.
- Rule frontmatter gains per-audience wording and last-written wording (see FR-001 and Clarifications). This is a schema change. Under Constitution Principle II (2.3.0), each stored wording is a single line approved by a person at `add` or `edit`, and its matching uses whitespace normalization; the formal statement alone is one sentence with one modal verb.
- `add` and `edit` must write the per-audience wording; `retire` is unchanged.
- Existing riposte prose is migrated by hand, once, into the rule files (see Clarifications). Until then, riposte's `CONTRIBUTING.md` stays outside this check.
- Derived paragraphs that were hand-edited are reported, not removed (see FR-002).
