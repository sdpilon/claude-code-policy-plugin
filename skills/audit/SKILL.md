---
name: audit
description: Checks self-verifiable obligations in a repo's policy file for CI-checkable obligations (conventionally .policy/compliance-audit.md) against live repo state and files an issue-tracker ticket for each one currently unmet. Use this as an automated CI step, not interactively or conversationally — there is no live user to ask questions of mid-run.
---

# Auditing self-checkable policy obligations

## Overview

Checks whichever obligations a project's own policy file declares as
self-verifiable — conventionally named `.policy/compliance-audit.md`, but use
whatever this repo actually calls it — against actual repo content: existence and
pattern only, never sufficiency. Files an issue-tracker ticket for each one
currently unmet. Runs unattended in CI; there is no user to ask questions of
mid-run. If something is ambiguous, fail loud (non-zero exit, clear log line)
rather than guessing or skipping silently.

## Scope

Only the obligations that policy file's own "what gets checked" section actually
lists. Never anything that file explicitly excludes from automated checking (most
commonly: obligations that need credentials beyond what the CI job already has —
e.g. administrative/branch-protection state deliberately withheld from day-to-day
automation). Treating a permission error as "passing" would be worse than not
checking it at all.

## Implementation

The actual checks belong in a plain script this project's CI invokes — not in this
skill, and not as an ad hoc agent-run procedure. This skill documents the
contract; the script is the authoritative implementation, and there is no separate
agent-run version to keep in sync with it.

If the policy file's obligations change (an ID added, removed, or reworded),
update the audit script in the same change — treat any mismatch between the script
and the policy file as a bug in the script, fix it there, not in the policy file.

The script's expected behavior:
- Runs each obligation's check (file/pattern existence only, never sufficiency).
- For each failing obligation: checks for an already-open ticket referencing that
  ID before filing a new one, so reruns don't duplicate it.
- For each passing obligation: does nothing. Never auto-closes a matching open
  ticket — closing means a human confirmed the fix is actually sufficient, not
  just that the existence-check flipped to pass.
- Always exits 0, regardless of findings, if this project's policy says the audit
  must never fail the build. Logs one line per obligation either way (pass, filed,
  or already tracked) so the CI log is a readable audit trail.

## What this is not

Not a substitute for building the missing thing. Not a sufficiency check. Run it
on whatever cadence this project's own policy specifies — don't assume "every push
to the default branch" is universal; check the actual policy file for when and how
often.
