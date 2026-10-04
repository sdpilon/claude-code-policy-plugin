# Research: Sync Removal When Audience Drops a Target

No NEEDS CLARIFICATION markers remain. The three clarifications of 2026-10-04 (stored per-audience wording, hand-edit reporting, one-time manual migration) settled the design points. The items below record what the plan decided beyond them.

## R1: Where per-audience wording lives

**Decision**: Frontmatter nested map `wording: {human: "...", agent: "..."}`. The body keeps `**<id>**: <statement>` as the formal rule.

**Rationale**: The existing parser already supports one nested level (as `verification` does), so no parser change is needed. Keeping the formal statement in the body preserves what `judge`, `audit` and `status` read today.

**Alternatives considered**:
- Per-audience sections in the body. Rejected: the body is parsed for the statement line, and adding sections makes exact-match boundaries harder to specify.
- Separate per-audience files. Rejected: splits one rule across files, against Principle II's one-file-per-rule model.

**Gap noted**: The spec did not say where authored wording lives. This decision fills it, and the spec's Assumptions should be updated to match.

## R2: Whitespace-normalized match semantics

**Decision**: Normalize whitespace on both sides before matching. The stored wording is split on `[ \t\r\n]+`, the words are joined with `[ \t\r\n]+`, and the pattern is searched in the doc. A match is a removal candidate only if exactly one occurrence exists. Zero occurrences is `not_found`; more than one is `ambiguous`. The removal span is the matched text plus one adjoining newline or space.

**Rationale**: Clarify chose matching on the stored text. Whitespace-only edits in a derived doc (rewraps, double spaces) should not hide a rule from removal, and any non-whitespace change still fails to match and is reported. Matching a span, not the whole paragraph, avoids deleting neighbors in hand-written paragraphs. The pattern is a pure function of the stored wording, so results are deterministic. Whitespace is limited to `[ \t\r\n]`, not Unicode whitespace, so the behavior is explicit.

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

**Rationale**: Each file is generated for one rule, so there is no surrounding prose. An exact check keeps a hand-edited file from being deleted silently.

## R6: Migration of riposte

**Decision**: A person writes `wording` for each riposte rule once, by hand (clarify Q3). `sync_status` reports a rule with an active audience and no wording for it as a defect (`audience wording missing`), following the existing defect pattern.

**Rationale**: Riposte's `CONTRIBUTING.md` has no per-rule text to import. A missing wording must be visible, not silently skipped.

## R7: Test fixture impact

**Decision**: Existing rule fixtures in `tests/` gain `wording` for their audiences. This is mechanical. The alternative of making `wording` optional was rejected, because a rule without wording would silently produce no derived text.

## R8: FR-003 holds without new code

**Decision**: No change. A test pins it.

**Rationale**: Verified 2026-10-04: an audience change alters the content hash, so the rule reads `changed: true`.
