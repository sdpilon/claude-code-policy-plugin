# Feature Specification: Sync Removal When Audience Drops a Target

**Feature Branch**: `005-sync-audience-removal`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "this problem" (the sync removal gap confirmed on 2026-10-03: changing a rule's `audience` from `[human]` to `[agent]` leaves no removal path for its wording in `CONTRIBUTING.md`)

## Clarifications

### Session 2026-10-04

- Q: When sync writes a rule's wording into a derived doc, where should it remember the wording it last wrote, so it can find that old wording after the rule is reworded? → A: In the rule's frontmatter, per audience, next to `synced_hash`.
- Q: If someone hand-edits a derived paragraph so it no longer exactly matches the stored wording, what should sync do when it can't find that wording to remove? → A: Report "expected text not found in <doc> for rule <id>" and leave it for a person to resolve; propose nothing for it.

- Q: How should a repo like riposte get the wording stored in its rule files, given that its `CONTRIBUTING.md` was written by hand and doesn't match any rule yet? → A: A person copies each existing paragraph into the rule's audience wording once, by hand.
- Q: For matching, which characters count as whitespace: only space, tab, carriage return, and newline, or every Unicode whitespace character? → A: Only space, tab, carriage return, and newline. Other Unicode whitespace is not treated as whitespace.
- Q: Should sync re-check the rule's source as well as the target documents before applying a change? → A: Yes. This follows from Constitution Principle III, which requires the re-check, so it was not put to a question. A rule whose source changed since its proposal is not applied or recorded.
- Q: Should the spec call the per-audience sentence "wording" everywhere, and reserve "text" for the span found inside a derived doc? → A: Yes. "Wording" names the per-audience sentence. "Text" names only the span matched in a derived doc.
- Q: When a rule's agent wording is reworded while the agent audience still applies, should sync replace `.claude/rules/<id>.md` with the new wording, but only if the file still holds exactly the old wording? → A: Yes. The file is overwritten with the new agent wording and a newline, only when its content equals the last-written wording plus a newline. Otherwise it is reported and not overwritten.
- Q: When an agent-only rule's audience is dropped, and `.claude/rules/<id>.md` still holds exactly the last-written wording, should sync delete that whole file? → A: Yes, only when its content still exactly equals the last-written wording plus a newline. Otherwise the file is reported and not deleted.
- Q: When sync removes a matched sentence from a derived doc, should it also remove one adjoining space or newline, so no blank gap is left behind? → A: Yes. The removal covers the matched text plus one adjoining space or newline.
- Q: Should `edit` refuse a statement change until each audience's wording has been reviewed, or is that review enforced only by the skill's preview step? → A: The script enforces it. A statement change requires an explicit review flag, and without it the script refuses and writes nothing. The skill passes the flag only after the person approves each previewed wording.
- Q: When a rule fails validation because an audience has no wording, should sync report that missing wording, or report only the validation error? → A: Report the missing wording as `missing_wording`, even though the rule is invalid. Only an unparseable rule reports no missing wording.
- Q: If an audience is dropped while its wording has an edit that sync has not yet recorded, what should happen to that edit? → A: `edit` rejects the audience change and names the audience. The person either runs sync to record the wording change first, or reverts the wording. A drop with no unrecorded wording edit is unchanged.
- Q: When a rule's wording for an audience that is still targeted changes, should sync also remove the wording last written for that audience? → A: Yes. Sync finds the last-written wording for that audience in its doc by the same exact-once match, proposes its removal, and proposes the new wording as an addition. If the old wording is not found or matches more than once, it is reported and nothing is removed.
- Q: When a person approves only some of a rule's proposed changes, should sync record the rule as synced anyway? → A: No. The rule is recorded as synced only when every proposed change for it was applied. Otherwise it stays changed, and the next run re-proposes it. A change already in place in its target is not re-proposed.
- Q: How many rules should one repo's sync handle at most, so we know how much scanning each run can afford? → A: Up to about 100 rules per repo. A full re-scan of derived docs on each run is acceptable; no index or cache is needed.

Superseded earlier in this session (design restarted): the bold-ID-token detection and whole-block removal answers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sync reports wording that must leave a derived doc (Priority: P1)

A maintainer changes a rule's audience so that one derived document no longer applies to it (for example `[human, agent]` to `[agent]`). When they run `/policy:sync`, the proposal lists the rule's wording in the no-longer-targeted document as a removal, with the matched text and the rule ID it comes from, before anything is written.

**Why this priority**: This is the reported defect. Without it, the human-facing doc can lose a rule silently, or keep a stale copy, and nothing in the output says so.

**Independent Test**: Create a rule with `audience: [human, agent]`, sync it, then change its audience to `[agent]`. Run sync and confirm the proposal contains a removal of that rule's wording from `CONTRIBUTING.md`, and that `CLAUDE.md` and `.claude/rules/<id>.md` still receive the update.

**Acceptance Scenarios**:

1. **Given** a synced rule whose audience changed from `[human]` to `[agent]`, **When** `/policy:sync` runs, **Then** the proposal lists `CONTRIBUTING.md` as a target to remove the rule's wording from, and lists `CLAUDE.md` and `.claude/rules/<id>.md` as targets to update.
2. **Given** a synced rule whose audience did not change, **When** `/policy:sync` runs, **Then** no removal is proposed for it.
3. **Given** a rule whose audience still includes `human` and whose stored `human` wording appears in `CONTRIBUTING.md`, **When** `/policy:sync` runs, **Then** that wording is not proposed for removal.
4. **Given** a synced rule whose audience still includes `human`, whose `human` wording changed since the last record, and whose previous `human` wording appears exactly once in `CONTRIBUTING.md`, **When** `/policy:sync` runs, **Then** the proposal lists that previous wording as a removal from `CONTRIBUTING.md` and the new wording as an addition to it, with the rule ID for both.

---

### User Story 2 - Removals are applied only after approval and the record stays consistent (Priority: P2)

After the maintainer approves a removal, the text is removed from the target document, and the rule is recorded as synced so the next run reports it as unchanged. A removal the maintainer declines leaves the document untouched and the rule still reported as changed.

**Why this priority**: The approval checkpoint is required by the constitution (Principle III). The record step has to match what was actually applied, or the rule would show as clean while a derived doc is still wrong.

**Independent Test**: Run the sync flow from User Story 1, approve the removal, record the sync, then run sync again and confirm the rule is unchanged and `CONTRIBUTING.md` no longer contains its wording. Repeat with a declined removal and confirm the document is unchanged and the rule is still reported as changed.

**Acceptance Scenarios**:

1. **Given** an approved removal, **When** the change is applied and recorded, **Then** the next sync run reports the rule as unchanged and `CONTRIBUTING.md` no longer contains its wording.
2. **Given** a declined removal, **When** the sync flow ends, **Then** `CONTRIBUTING.md` is unchanged and the rule is still reported as changed.
3. **Given** `CONTRIBUTING.md` changed after the proposal was shown, **When** the maintainer approves, **Then** sync re-checks the target and does not apply the removal over the newer content.

---

### Edge Cases

- What happens when a stored wording is found more than once in a document, or not at all? Sync reports it as `ambiguous` or `not_found` and proposes nothing for it (FR-002).
- What happens when `CONTRIBUTING.md` does not exist? No removal is proposed, and the sync report says the target is absent.
- What happens when a rule's audience is emptied or set to an invalid value? The rule is reported as an error (existing behavior), and no removal is proposed for it.
- What happens when a wording changed for a still-targeted audience, and its previous wording was reworded by hand in the doc? Sync reports it as `not_found` and proposes no removal for it, as for a dropped audience (FR-002). The new wording is still proposed as an addition.
- What happens when a rule is invalid because an audience has no wording? Sync reports the invalid rule with its `error`, reports each missing audience in `missing_wording`, and proposes no removal for the rule.
- What happens when an edit drops an audience whose wording was changed but not yet recorded by sync? The edit is rejected (FR-012). A drop with no unrecorded wording change, or for an audience never recorded, is not affected.
- What happens when a rule is retired? Retirement is a separate flow (`/policy:retire`) and is out of scope here; this feature covers audience changes and wording changes for audiences still targeted.
- What happens when a rule's audience changes from `[agent]` to `[human]`? The new `CONTRIBUTING.md` target is proposed as an addition, as today; no removal is involved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each rule MUST store its wording per audience in its own file, and the last-written wording per audience in its frontmatter next to `synced_hash`. The sync mechanism MUST determine, by script rather than by reading the derived documents with an LLM, which derived documents contain the last-written wording of a rule and either are no longer among its targets, or are still targets for an audience whose wording has changed since the last record. It MUST match that wording with whitespace normalized, and MUST treat a match as removable only when it occurs exactly once.
- **FR-002**: `/policy:sync` MUST list each such document in its proposal as a removal of that last-written wording, matched as FR-001 requires, with the rule ID it comes from, and MUST NOT write the removal before approval. The removal covers the matched text plus one adjoining space or newline. For the agent-only file `.claude/rules/<id>.md`, the removal is deleting the file, proposed only when its content equals the last-written wording plus a newline; otherwise it is reported and not deleted. When the agent audience is still targeted and its wording was reworded, the file is overwritten with the new agent wording and a newline, under the same exact-match condition; otherwise it is reported and not overwritten. For a still-targeted audience whose wording changed, the proposal MUST also list the new wording as an addition to that document (FR-008, FR-011). When the last-written wording cannot be found in a document that should hold it, sync MUST report it by document and rule ID and MUST NOT propose a removal for it.
- **FR-003**: A rule whose audience changed MUST be reported as changed even when the only change is a dropped target.
- **FR-004**: After approved changes, `record_sync` MUST mark the rule as synced so the next run reports it as unchanged, but only when every proposed change for the rule was applied. Otherwise the rule stays reported as changed, and the next run re-proposes it without re-proposing any change already in place in its target. It MUST write `synced_wording` for the rule's current audiences, verbatim, and MUST remove entries for audiences the rule no longer has. It MUST leave the rest of the rule file unchanged.
- **FR-005**: Sync MUST re-check each target document before applying a removal, consistent with the existing re-check rule for additions and edits. Sync MUST also re-check that the rule's source has not changed since its proposal, as Constitution Principle III requires, and MUST NOT apply or record a change for a rule whose source has changed.
- **FR-006**: The sync skill's instructions MUST describe the removal step, so the proposal does not depend on the agent deciding on its own to remove text.
- **FR-007**: When a target document is absent, sync MUST report it and MUST NOT create it for a removal.
- **FR-008**: For each addition of a rule's wording to a derived document, the `/policy:sync` proposal MUST state the target section and the position within it, and MUST NOT write the addition before approval. Placement is decided at proposal time and approved with the rest of the change. It is not stored in the rule file.
- **FR-009**: Each audience wording MUST be approved by a person at `add` or `edit` time, under the checkpoint in Principle III. Editing a rule's formal statement MUST prompt review of each audience wording before the edit is written. The `edit` script MUST refuse a statement change that lacks an explicit review flag, and MUST write nothing in that case. The skill passes the flag only after the person approves each previewed wording.
- **FR-010**: A rule's `wording` MUST have exactly one entry for each audience in `audience`. Each entry MUST be non-empty and a single line after whitespace is collapsed at write time. Each `synced_wording` entry MUST be a non-empty single line. `/policy:status` MUST report a rule whose `wording` is missing, or does not match its `audience`, as a defect. Its keys MUST be a subset of `human` and `agent`, and MAY name an audience the rule no longer has until `record_sync` prunes it.
- **FR-011**: When sync adds a rule's wording to a derived document, it MUST write only the `wording` for that document's audience, copied verbatim. `CONTRIBUTING.md` takes the `human` wording. `CLAUDE.md` and `.claude/rules/<id>.md` take the `agent` wording.
- **FR-012**: `edit` MUST reject an audience change that drops an audience whose `wording` differs from the `synced_wording` recorded for it, and MUST exit non-zero naming that audience, without writing. The person then runs sync to record the wording change, or reverts the wording. An audience drop with no such difference, or an audience never recorded, is not rejected.

### Key Entities *(include if feature involves data)*

- **Rule**: One file under `.policy/rule/`. Its `audience` determines its targets. Its stored `wording` and `synced_wording` are what sync writes to, and matches in, derived documents.
- **Derived document**: `CONTRIBUTING.md`, `CLAUDE.md`, or `.claude/rules/<id>.md`. Outputs only; never edited as a source.
- **Removal proposal**: A proposed deletion of one rule's wording from one derived document, shown for approval.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test set of audience changes covering every transition between `human`, `agent`, and both, 100% of dropped targets that still contain the rule's wording appear in the sync proposal as removals. In a test set of wording changes for still-targeted audiences, 100% of previous wordings that appear exactly once in their doc appear in the proposal as removals.
- **SC-002**: Zero derived-document edits occur without the maintainer's approval in the sync flow.
- **SC-003**: After an approved removal and record, the next sync run reports 100% of the affected rules as unchanged.
- **SC-004**: A maintainer can tell from the sync output alone which derived document will lose which rule's wording, without opening the documents.

## Assumptions

- The fix is in the policy plugin (`skills/sync/`), not in riposte. Riposte is a consumer whose migration feedback raised the issue.
- The removal is a proposal like any other sync change, so it goes through the existing approval checkpoint.
- Rule frontmatter gains per-audience wording and last-written wording (see FR-001 and Clarifications). This is a schema change. Under Constitution Principle II (2.3.0), each stored wording is a single line approved by a person at `add` or `edit`, and its matching uses whitespace normalization; the formal statement alone is one sentence with one modal verb.
- `add` and `edit` must write the per-audience wording; `retire` is unchanged.
- Existing riposte prose is migrated by hand, once, into the rule files (see Clarifications). Until then, riposte's `CONTRIBUTING.md` stays outside this check.
- Derived paragraphs that were hand-edited are reported, not removed (see FR-002).
- A repo has up to about 100 rules, so sync re-scans its derived docs on each run; no index or cache is needed.
