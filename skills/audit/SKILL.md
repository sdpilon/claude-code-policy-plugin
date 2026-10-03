---
name: audit
description: Checks self-verifiable rules in .policy/rule/ against live repo state and files a ticket for each unmet one. Automated CI step only; there is no live user to ask mid-run.
---

# Auditing self-checkable rules

Runs in CI, non-interactively. It checks the rules whose `verification.method` is
`ci-checked` and whose check is a file or pattern existence test. The check lives in the
consuming project's own script, which encodes that project's checks. This skill documents the
contract only.

## Contract

- Input: the rules under `.policy/rule/` (via `skills/status/scripts/policy_status.py`).
- For each `ci-checked` rule the project's script can verify, run the check. A check proves
  presence, never sufficiency.
- For each failing rule, look for an already-open ticket with the same dedupe key. If none
  exists, file one. Don't auto-close anything.
- **Dedupe key:** the consuming project's script must stamp each ticket with a key that
  survives renumbering and retitling, such as a label or a hidden body marker. The key must
  not be the rule's ID or title, since changing either would otherwise file duplicates. The
  project's docs must name the key it uses.
- For each passing rule, do nothing.
- Never fail the build because a rule isn't verifiable. Log one line per rule (pass, filed,
  or skipped).

## Token scopes

The plugin's own skills need no token; they read and write local files only. The
consuming project's script needs a token with **Issues: read and write** on the repo,
to search for open tickets and file new ones. Nothing more is required. A token without
issue write access fails the first filing attempt, so check it before the first CI run.

## Guardrails

- The audit never edits rules, and it never changes a `verification` field.
- A rule with `"defect"` set is skipped and logged, not checked.
