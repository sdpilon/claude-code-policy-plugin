---
name: migrate
description: One-time conversion of a repo's old .policy/<topic>.md files (several rules per file, <PREFIX>-N IDs) into one-rule-per-file under .policy/rule/. Use when a repo still uses the topic-file convention, or when asked to migrate policy files to the rule layout.
---

# Migrating topic files to rules

The mechanical split is a script. Every decision it can't make safely goes to a person.

## Steps

1. **Back up first.** Confirm the repo is committed or that the person has a copy, so the
   old topic files can be restored.
2. **Dry run:**

   ```sh
   python3 <plugin>/skills/migrate/scripts/migrate_rules.py --source-dir .policy --dest-dir .policy/rule --dry-run
   ```

   Show the person the planned mapping (`source_id` → `new_id`) and the `needs_review` list.
3. **Wait for a go-ahead.** Then run it for real (drop `--dry-run`).
4. **Guided cleanup, one rule at a time.** Work through `needs_review`:
   - `audience not set`: ask the person for `human`, `agent`, or both.
   - `shared rationale`: the rule's rationale was shared with siblings. Ask the person to write
     a short rationale for this rule alone, or to cross-link siblings with
     `See also [N](N.md).` Never copy the shared text in unchanged.
   - `could not determine section boundaries`: read the file and fix the rationale by hand.
   - Give each rule a `title` (the script leaves it blank) and a `verification` if the
     migration didn't carry one over.
5. **Remove the old files** only after the person confirms the new rules are right. Use
   `git rm` so the change stays reviewable.
6. **Report**: rule count, anything still unresolved, and a reminder to run `/policy:sync`.

## Guardrails

- Never resolve a shared rationale or a missing audience yourself.
- Don't commit unless the user asks.
