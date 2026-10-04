# Research: Policy Plugin Gaps

Each entry is Decision, Rationale, and Alternatives considered. Open items are marked.

## R1. Record-sync write path (US1)

**Decision**: `record_sync.py` takes explicit rule IDs. For each, it reads the file, computes
`sync_status.content_hash(text)`, and sets `synced_hash` in the frontmatter. It writes with
`policy_manifest.atomic_write_bytes`. A rule whose stored hash already matches is not
rewritten (FR-002).

**Rationale**: `content_hash` already strips the `synced_hash` line, so writing the hash does
not change the hash, and a second run is a no-op. Reusing the atomic writer keeps the file
mode and atomicity fixes from earlier commits (`076e575`).

**Alternatives considered**: record every rule whose hash changed. Rejected: the sync skill
must record only the rules it actually applied, so explicit IDs keep the approval step honest.

## R2. Edit path and `modified` (US2)

**Decision**: `edit_rule.py` sets `modified` to `fm.now_utc()` on every rule it changes. It
does not touch `synced_hash`. An edited rule therefore reads as changed in `sync_status` until
`record_sync` runs, which is the behavior the spec's Independent Test describes.

**Rationale**: the spec separates "this rule changed" (edit) from "derived docs now reflect
it" (record-sync). Setting `synced_hash` in the edit step would hide an unsynced change.

**Alternatives considered**: the edit also records the sync. Rejected for the reason above.

**Validation**: edits go through `fm.validate` on the resulting fields. The one-sentence and
one-modal-verb check on `statement` is shared with `add_rule.py`. If that check is currently
inline in `add_rule.py`, move it to `scripts/policy_frontmatter.py` (see R5).

## R3. Bulk edit (US3)

**Decision**: one command, `edit_rule.py`, takes one or more IDs. It runs in two phases.
Phase 1 loads and validates every target. Any failure stops the run before any write, and
the report names each failing rule and reason. Phase 2 writes each file atomically. If a
write fails partway, the script restores the already-written files from the in-memory
originals and exits nonzero.

**Rationale**: validation failures are the common case, and phase 1 covers them with no
writes at all. The restore covers the rarer I/O failure. Full cross-file transactions are not
available on a filesystem, so the rollback is best effort, and the report says so.

**Alternatives considered**: a separate `bulk_edit.py`. Rejected: one command with a preview
mode keeps the surface small and avoids two code paths for the same change.

## R4. Audit dedupe key (US4, FR-013)

**Decision**: the dedupe key is the rule's `verification.via` value. It is stamped on each
issue two ways: as a label `policy-audit:<via>`, and as a hidden marker
`<!-- policy-audit-key: <via> -->` in the body. The search uses the label.

**Rationale**: `via` names the check, not the rule. It survives title and ID changes, which
is what FR-013 requires. Several rules sharing one check produce one issue, which is the
correct result: the same check failing twice is one problem.

**Alternatives considered**:

- Rule ID. Rejected: the spec and the audit contract both forbid it.
- A new `uid` frontmatter field. Rejected: it adds a required schema field for a problem the
  check name already solves. Revisit if two rules must track one check independently.

**Open item**: a rule that changes its `via` value will file a new issue and orphan the old
one. The audit does not close issues (FR-016), so this is documented, not fixed.

## R5. Shared statement check and frontmatter docs (FR-006, FR-018)

**Decision**: move the one-sentence, one-modal-verb check out of `add_rule.py` into
`scripts/policy_frontmatter.py` as `validate_statement(text)`, returning a list of problems.
`add_rule.py` and `edit_rule.py` both call it. Document the parser's return type in
`specs/001-rule-per-file-restructure/contracts/policy_frontmatter.md` and in the skills that
call it: `parse(text)` returns a `dict` of `str` keys mapping to `str`, `list`, or a nested
`dict` of scalars. A file with no frontmatter block raises `FrontmatterError`. An empty value
is `""` (for scalars) or `[]` (for lists).

**Rationale**: both writers must enforce the same rule. Without a shared check, the edit
path could accept a statement that `add` rejects.

**Alternatives considered**: copy the check into `edit_rule.py`. Rejected: two copies drift.

## R6. Audit tracker and registry (US4, FR-010)

**Decision**: `audit_checks.py` takes `--registry <path>` to a consumer-supplied Python file
that exports `CHECKS: dict[str, Callable[[], bool]]`. A check returns True when it passes. It
takes `--tracker github` (default) or `--tracker none` for a dry run that logs what it would
file. The GitHub tracker runs `gh issue list --label` and `gh issue create`, and it never
closes issues.

**Rationale**: the plugin supplies the dispatch and filing mechanism only (Principle I). A
dry-run tracker lets the audit be tested with no network, and the tests use an in-memory
fake tracker.

**Alternatives considered**: the audit calls the GitHub REST API directly. Rejected: `gh`
already handles auth and is what the consumer's token scope is documented against
(`skills/audit/SKILL.md`, Token scopes).

## R7. Plugin root discovery (US5, FR-017) — OPEN

**Question**: can a skill body reference the plugin root without a search? The installed
plugins use `CLAUDE_PLUGIN_ROOT` in hook commands, but it is not verified for skill bodies.

**Plan**: before implementing, check the Claude Code plugin docs (or `claude-code-guide`) for
whether `${CLAUDE_PLUGIN_ROOT}` is substituted in skill content. Then pick one of:

- If substituted: `SKILL.md` uses `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/...`. Document
  that and remove the "two levels up" rule from `README.md`.
- If not: keep the documented rule (base directory from the skill loader, two levels up) and
  add `scripts/plugin_root.py`, which prints the root by walking up from its own path. Skills
  then call it by a fixed relative path.

Either way, FR-017 needs one documented method. The task list includes a verification step.

## R8. Edit skill trigger (constitution, Development Workflow)

**Decision**: the new `edit` skill's description must be validated with fresh-context trigger
tests before merge. Positive cases: "change the statement of rule 004", "bump the audience on
these three rules". Negative cases: "add a rule" (must go to `add`), "retire rule 004" (must go
to `retire`), "sync the docs" (must go to `sync`).
