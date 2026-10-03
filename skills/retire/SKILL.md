---
name: retire
description: Retire a policy rule by removing it from .policy/rule/ and leaving a tombstone, so its ID is never reissued. Use when a rule no longer applies, or has been superseded by another rule.
---

# Retiring a rule

Retiring a rule removes its file and leaves a frontmatter-only tombstone at
`.policy/retired/<id>.md`. The tombstone keeps the ID out of circulation, so it's never
reissued. This is the only supported way to remove a rule.

## Steps

1. **Confirm which rule.** Find its ID with `/policy:status`. Check whether anything else
   depends on it: other rules cross-linking it, or derived docs that cite it.
2. **Ask for the reason** via `AskUserQuestion` (Constitution Principle III). The reason is
   required and is recorded in the tombstone. If the rule is replaced, also ask for the
   replacement's ID (`superseded_by`).
3. **Run the script:**

   ```sh
   python3 <plugin>/skills/retire/scripts/retire_rule.py --id <id> --reason "<reason>" [--superseded-by <id>]
   ```

   It writes the tombstone first, then removes the rule file.
4. **Report** the tombstone path. Then run `/policy:sync`, because derived docs that cite the
   rule now need updating.

## Guardrails

- Never delete a rule file by hand. A manual delete leaves an ID gap that status reports.
- Don't commit unless the user asks.
