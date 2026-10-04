---
name: status
description: Lists every rule under .policy/rule/ with its title and enforcement tier, plus any defects and ID gaps. Use when asked what policies are in effect, for an overview of the repo's rules, or how a specific rule is enforced.
---

# Rule status

Read-only. Runs a deterministic script and presents the result. It never edits rules.

## Steps

1. Run the inventory:

   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/status/scripts/policy_status.py .
   ```

2. Present a table with one row per rule: `ID`, `title`, `tier`, and `via`. Sort by ID.
3. Report **defects** separately: a rule with `"defect"` set (missing `audience`, malformed
   frontmatter) is listed with its problem, not hidden.
4. Report **gaps** separately: any ID in `"gaps"` has no rule file and no tombstone, so the
   rule was probably deleted without `/policy:retire`. Name the gap IDs and suggest
   `/policy:retire` or restoring the rule.
5. Show the CI job inventory only if the person asked how enforcement works.

## Tiers

- `ci-blocking` / `ci-checked`: CI enforces it (blocking or advisory).
- `human-verified`: a person checks it.
- `written-only`: nothing enforces it. Say so plainly.
- `unclassified`: no valid `verification` field. Treat it as a defect to fix with `/policy:add`
  or by editing the rule.

## Guardrails

- Never imply a rule is enforced beyond its declared tier (Constitution Principle V).
- Tiers are read from frontmatter. Don't infer them from CI job names.
