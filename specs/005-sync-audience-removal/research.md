# Research: Sync Removal When Audience Drops a Target

No NEEDS CLARIFICATION markers remain. The clarifications of 2026-10-04 settled the design points. R1 to R8 record decisions made in the first plan. R9 to R13 record decisions made when the spec was widened and clarified, and they are the basis for the revised plan.

## R1: Where per-audience wording lives

**Decision**: Frontmatter nested map `wording: {human: "...", agent: "..."}`. The body keeps `**<id>**: <statement>` as the formal rule.

**Rationale**: The existing parser already supports one nested level (as `verification` does), so no parser change is needed. Keeping the formal statement in the body preserves what `judge`, `audit` and `status` read today.

**Alternatives considered**:

- Per-audience sections in the body. Rejected: the body is parsed for the statement line, and adding sections makes exact-match boundaries harder to specify.
- Separate per-audience files. Rejected: splits one rule across files, against Principle II's one-file-per-rule model.

**Gap noted**: The spec did not say where authored wording lives. This decision fills it, and the spec's Assumptions should be updated to match.

## R2: Whitespace-normalized match semantics

**Decision**: Normalize whitespace on both sides before matching. The stored wording is split on `[ \t\r\n]+`, the words are joined with `[ \t\r\n]+`, and the pattern is searched in the doc. A match is a removal candidate only if exactly one occurrence exists. Zero occurrences is `not_found`; more than one is `ambiguous`. The removal span is the matched text plus one adjoining newline or space.

**Rationale**: Clarify chose matching on the stored text. Whitespace-only edits in a derived doc (rewraps, double spaces) should not hide a rule from removal, and any non-whitespace change still fails to match and is reported. Matching a span, not the whole paragraph, avoids deleting neighbors in hand-written paragraphs. The pattern is a pure function of the stored wording, so results are deterministic. Whitespace is limited to `[ \t\r\n]`, not Unicode whitespace, so the behavior is explicit (clarified 2026-10-04).

**Verified 2026-10-04**: the frontmatter parser round-trips runs of spaces, leading and trailing spaces, tabs, colons, and quotes on one line. A raw newline inside a stored value makes the file fail to parse ("unsupported syntax"), so `add` and `edit` must collapse whitespace before storing.

**Alternatives considered**: Whole-paragraph removal. Rejected: hand-written paragraphs can hold other rules' text (riposte's line 93 does), so the neighbors would be deleted.

## R3: Content hash must ignore synced_wording

**Decision**: `sync_status.content_hash` removes the `synced_hash:` line and the `synced_wording:` block (the key line plus its indented children) before hashing.

**Rationale**: `record_sync` writes `synced_wording` after hashing. Without this, a freshly recorded rule would hash differently and read as changed. This is a real pitfall, found while planning. The existing test `test_unchanged_after_synced_hash_is_written` covers the `synced_hash` case, and the new test extends it to `synced_wording`.

## R4: record_sync writes and prunes synced_wording

**Decision**: For each approved ID, `record_sync` sets `synced_wording` to the current `wording` for the rule's current audiences, and removes it entirely when empty. Dropped audiences disappear from `synced_wording` at that point.

**Rationale**: After a record, `synced_wording` describes what the derived docs now hold, so the next scan has nothing to remove for that rule.

## R5: Derived file format for the agent-only file

**Decision**: `.claude/rules/<id>.md` holds exactly the agent wording and a single trailing newline. Removal of that file is allowed only if its content matches the stored wording plus a newline exactly.

**Rationale**: Each file is generated for one rule, so there is no surrounding prose. An exact check keeps a hand-edited file from being deleted silently. The clarification of 2026-10-04 (agent-only file) chose deletion over emptying or leaving the file, so Claude Code no longer loads a stale rule into agent context.

## R6: Migration of riposte

**Decision**: A person writes `wording` for each riposte rule once, by hand (clarify Q3). `sync_status` reports a rule with an active audience and no wording for it in `missing_wording`, and `policy_status` reports the rule as a defect (`wording missing`), following the existing defect pattern.

**Rationale**: Riposte's `CONTRIBUTING.md` has no per-rule text to import. A missing wording must be visible, not silently skipped.

## R7: Test fixture impact

**Decision**: Existing rule fixtures in `tests/` gain `wording` for their audiences. This is mechanical. The alternative of making `wording` optional was rejected, because a rule without wording would silently produce no derived text.

## R8: FR-003 holds without new code

**Decision**: No change. A test pins it (`AudienceChangeRecordTests` in `tests/test_sync_status.py`).

**Rationale**: Verified 2026-10-04: an audience change alters the content hash, so the rule reads `changed: true`.

## R9: Rewording a still-targeted audience (FR-001, FR-002, acceptance scenario 4)

**Decision**: `sync_status` treats an audience as stale for rewording when it is still targeted, `synced_wording` holds an entry for it, and `wording` for it differs from that entry. The stale entry searches the doc for the last-written text and carries `reason: "reworded"`. Audiences dropped since the last record carry `reason: "dropped"`. A `reworded` removal is always proposed together with an addition of the current wording to the same doc.

**Rationale**: `synced_wording` already keeps the last-written text per audience, so no new storage is needed. Reusing the same exact-once match keeps detection deterministic (Principle IV). The `reason` field lets the sync skill pair a removal with its addition without re-deriving the cause.

**Alternatives considered**: A separate list for reworded audiences. Rejected: it duplicates the stale-location shape and would need its own tests for the same match rules.

## R10: Rejecting an audience drop with an unrecorded wording edit (FR-012)

**Decision**: `edit_rule.py` compares the rule's `wording.<audience>` and `synced_wording.<audience>` before applying any `--set`. When an audience is removed from `audience` and a recorded `synced_wording` entry exists for it that differs from `wording`, the edit is rejected with exit `2`, naming the audience, and nothing is written. An audience never recorded has no `synced_wording` entry and is not affected.

**Rationale**: `edit` already drops `wording` keys for removed audiences so `validate()` passes. Without this check the unrecorded wording edit is silently discarded. The check compares against the recorded text, so it does not change the common case of dropping an audience that was never reworded (quickstart Scenario 1).

**Alternatives considered**: Allowing the drop and printing what was discarded. Rejected in clarification in favor of an explicit error.

## R11: Review flag for statement edits (FR-009)

**Decision**: `edit_rule.py` requires `--reviewed-wording` on any non-preview run whose `--set` list includes `statement`. Without the flag it exits `2` and writes nothing. The flag is not needed for `--preview`, which prints a `review wording.<audience>` line for each audience. The skill passes the flag only after the person approves those lines.

**Rationale**: Clarification chose script enforcement (Principle III is otherwise enforced only by skill text). The flag makes the review an explicit, testable input without adding interactive prompts to the script.

**Alternatives considered**: Keeping the review in the skill only. Rejected in clarification.

## R12: Reworded agent-only file (plan decision, not in the spec)

**Decision**: When the agent audience is still targeted and its wording was reworded, `.claude/rules/<id>.md` is overwritten with the new agent wording plus a newline, under the same exact-match gate as deletion: the current content must equal the last-written wording plus a newline. Otherwise the file is reported as `not_found` and not overwritten.

**Rationale**: Deletion is the clarified outcome for a dropped audience (R5). For a reworded, still-targeted audience the file must stay, so the stale copy is replaced rather than deleted. The same exact-match gate protects hand edits.

**Open point**: The spec does not state this case. It follows from R5 and R9, and it is recorded here so the implementer does not invent a different behavior. Confirm it in the next clarify pass if you want it in the spec.

## R13: Source re-check before applying (FR-005, Constitution Principle III)

**Decision**: The proposal records each rule's `current_hash`. Before applying, the sync skill re-runs `sync_status` and stops for any rule whose hash changed. `record_sync --expect ID=HASH` refuses with exit `1` and writes nothing when the rule's current content hash differs from the one given.

**Rationale**: Principle III requires the source to be re-checked before a proposal is applied. The script check is a last guard at the point the record is written, so a change between approval and record cannot be recorded as synced.

## Plan-level decisions recorded for implementers

- `stale_in` entries have a `reason` field (`dropped` or `reworded`), added by R9.
- Rules still reported as `missing_wording` when they fail validation (Scenario 6). Unparseable rules report nothing (contract `sync_status.md`, error behavior).
