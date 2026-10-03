---
name: sync
description: Check whether CONTRIBUTING.md and the agent-operational doc still match the rules under .policy/rule/, using each rule's audience, and propagate approved changes. Use after a rule was added or edited, before finishing a task that touched .policy/rule/, or when asked to sync docs or check for drift.
---

# Syncing rules into derived docs

`.policy/rule/` is the source of truth. `CONTRIBUTING.md` (human-facing) and the
agent-operational doc (`CLAUDE.md` plus `.claude/rules/<id>.md`) are outputs. This skill
proposes changes; it never writes without approval.

## Steps

1. **Get the mechanical state.** Run:

   ```sh
   python3 <plugin>/skills/sync/scripts/sync_status.py --dir .policy/rule
   ```

   Each row gives `id`, `audience`, `targets`, `changed`, and an optional `error`.
2. **Skip unchanged rules.** Only `"changed": true` rules need work (FR-008).
3. **Fix errors first.** A rule with an `error` field is malformed. Surface it to the person
   instead of proposing docs for it.
4. **Propose, don't apply.** For each changed rule, use its `targets` list (never infer from
   `audience`) to draft the exact text change in each target. Show the full proposal:
   file, the old and new text, and the rule ID it comes from.
5. **Wait for approval** (Constitution Principle III). Re-check the target files are unchanged
   since you read them before applying anything.
6. **Apply and record.** After approval, make the edits. Then write each applied rule's new
   `synced_hash` (the value `sync_status.py` computes) into its frontmatter, so the next run
   reports it unchanged.
7. **Report.** Say what was synced, and say so plainly if nothing had changed.

## Guardrails

- Don't commit unless the user asks.
- A clean sync is a useful result. Say so plainly.
