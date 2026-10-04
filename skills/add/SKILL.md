---
name: add
description: Add a new policy rule as its own file under .policy/rule/ with the next free ID. Use when the user wants to add, define, write down, or formalize a project policy, convention, or house rule ("we should have a rule about...", "add a rule for...", "what's our policy on...") — even if they never say the word "policy".
---

# Adding a rule

A rule is one sentence in its own file: `.policy/rule/<id>.md`. The ID is the next free
integer, zero-padded to three digits (`047`). You never choose a topic file, and you never
append to an existing file.

## Steps

1. **Confirm it's repo policy, not personal preference.** If it's unclear, run `/policy:judge`
   first, then come back here.
2. **Draft the statement.** One sentence, exactly one modal verb (MUST / SHOULD / MUST NOT /
   MAY). Write a short rationale that stands alone; cross-link related rules by number
   (`See also [048](048.md).`) instead of repeating their reasoning.
3. **Set the required fields** and confirm them with the user before writing:
   - `audience`: `human`, `agent`, or both. This decides which derived docs the rule reaches.
   - `verification.method`: `ci-blocking`, `ci-checked`, `human-verified`, or `written-only`.
     Name the check that SHOULD enforce it, as an intended name: a CI job, script, or review
     step (`verification.via`). The check may not exist yet. Don't describe its current state.
   - `title`: a short human name. It's display-only and can change later.
4. **Run the script** (this is the checkpoint: show the person the statement, fields, and
   rationale first, and wait for a go-ahead):

   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/add/scripts/add_rule.py \
     --statement "<subject> MUST <requirement>." --title "<title>" \
     --audience human,agent --verification-method ci-checked \
     --verification-via "<check name>" --rationale "<paragraph>"
   ```

   The script allocates the ID, writes the file, and prints `{"id", "path"}`.
5. **Report**: the new ID and path. Say that derived docs (`CONTRIBUTING.md`, `CLAUDE.md`,
   `.claude/rules/`) are now out of sync and that `/policy:sync` will propagate the change.

## Guardrails

- Add one rule per invocation. Never edit another rule's file while adding.
- Don't commit unless the user asks. Follow this repo's own git conventions.
- To change an existing rule's wording, edit its file directly, then run `/policy:sync`.
  Don't re-add it under a new ID.
- To remove a rule, use `/policy:retire`. Don't delete the file by hand, since that leaves
  an ID gap that status reports.
