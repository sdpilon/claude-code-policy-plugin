---
name: sync
description: Check whether CONTRIBUTING.md and the agent-operational doc still match the rules under .policy/rule/, using each rule's audience, and propagate approved changes. Use after a rule was added or edited, before finishing a task that touched .policy/rule/, or when asked to sync docs or check for drift.
---

# Syncing rules into derived docs

`.policy/rule/` is the source of truth. `CONTRIBUTING.md` (human-facing) and the
agent-operational doc (`CLAUDE.md` plus `.claude/rules/<id>.md`) are outputs. This skill
proposes changes; it never writes without approval.

Each rule carries one `wording` line per audience in its frontmatter. Sync copies that wording
verbatim into the matching doc. After a sync, the rule's `synced_wording` holds what was last
written for each audience, so an audience that is later dropped can be found and removed.

## Steps

1. **Get the mechanical state.** Run:

   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
   ```

   Each row gives `id`, `audience`, `targets`, `changed`, `missing_wording`, `stale_in`, and an
   optional `error`.
2. **Skip unchanged rules.** Only `"changed": true` rules need work (FR-008).
3. **Fix errors and defects first.** A rule with an `error` field is malformed. Surface it to the
   person instead of proposing docs for it. A rule with a non-empty `missing_wording` has no
   wording for an active audience. Report it as a defect and propose nothing for that audience
   until someone adds the wording with `/policy:edit`.
4. **Propose, don't apply.** For each changed rule, draft the change for each item, and show the
   full proposal: the file, the old and new text, the rule ID it comes from, the position, and the
   rule's `current_hash` as `sync_status` reported it.
   - **Removals** come from `stale_in`, one entry per stale location. `reason` says why it is
     stale: `dropped` means the audience left `audience`, and `reworded` means it is still targeted
     with changed wording. Propose a removal
     only when `status` is `"found"`. Show the matched `text` and the one adjoining newline or
     space that goes with it, so no blank gap is left. Never propose a removal for `not_found`,
     `ambiguous`, or `absent`. Report those by document and rule ID with the reason:
     `not_found` means the text was reworded by hand, `ambiguous` means it appears more than once,
     and `absent` means the document does not exist.
   - **Reworded pairs.** Each `reworded` removal is proposed together with an addition of the
     current `wording` for that audience to the same doc, placed as the proposal states (FR-002).
     For a `reworded` `kind: "file"` location, the addition overwrites `.claude/rules/<id>.md`, and
     only when its `status` is `found` (R12). A `dropped` removal is proposed alone.
   - **Additions** come from `targets`, which lists the docs for the current audiences (never infer
     them from `audience`). Each addition states the target section and the position within it
     (FR-008). Its text is that rule's `wording` for that document's audience, copied verbatim
     (FR-011). Never write the formal statement into a derived doc.
5. **Wait for approval** (Constitution Principle III). Re-check the target files are unchanged
   since you read them before applying anything. Before applying each approved removal or
   addition, re-read its target document. If the document changed since the proposal, stop for
   that item and ask again (FR-005). Re-run `sync_status` and compare each approved rule's
   `current_hash` with the one in its proposal. If a rule's source changed since the proposal,
   stop for that rule and propose again, because the approval was for different text.
6. **Apply and record.** After approval, make the edits. Then record the rules you applied with
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/scripts/record_sync.py <ID> [<ID> ...]`, passing only
   the IDs that were approved and applied, and pass each one's proposed hash with
   `--expect <ID>=<current_hash>`. The script refuses, and writes nothing, if a rule's source
   changed since it was proposed. It writes each rule's `synced_hash` and
   `synced_wording` and leaves the rest of the file unchanged. Dropped audiences are pruned from
   `synced_wording`, so the next run reports those rules as unchanged. It exits 2 without writing
   anything if an ID is missing.
7. **Report.** Say what was synced, which proposals were declined, and which stale or missing
   items were reported but not proposed. A declined removal leaves its rule `changed`, and its
   stale location stays listed on the next run. Say so plainly if nothing had changed.

## Guardrails

- Don't commit unless the user asks.
- A clean sync is a useful result. Say so plainly.
- Text that no longer matches is reported, never removed. Only an exact, single match is removed.
