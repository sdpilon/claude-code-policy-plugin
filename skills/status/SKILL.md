---
name: status
description: Lists every .policy/*.md file and, per obligation ID, how (if at all) it's actually enforced — CI-blocking, CI-checked non-blocking, human-verified only, or written policy with no technical check. Use this whenever the user asks what policies are in effect, wants an overview of this repo's process rules, or asks how a specific obligation is actually enforced or checked.
---

# Policy status overview

## Overview

Produces a table of every obligation across `.policy/*.md`: its ID, a short
statement, and its enforcement tier. Read-only — never edits `.policy/`,
`CONTRIBUTING.md`, `CLAUDE.md`, or anything else.

## Run the script first, every time

Don't re-derive this by reading every policy file and every CI workflow by hand —
that's slow and it's exactly the kind of fixed-schema extraction a script should do
once, deterministically. Run:

```
scripts/policy-status.sh <repo-root>
```

(repo-root defaults to `.` if omitted). It emits JSON:

- `obligations`: every `**<PREFIX>-N**: <statement>` found under `.policy/*.md`,
  each tagged with a `tier` — one of `ci-blocking`, `ci-checked`, `human-verified`,
  `written-only`, or `unclassified` — and a `via` note, read from an inline
  annotation immediately following the obligation (same line or the next line):

  ```
  <!-- tier: ci-blocking; via: .github/workflows/ci.yml quality-gate job -->
  ```

- `ci_jobs`: a best-effort inventory of this repo's GitHub Actions jobs (name,
  whether it's blocking — no `continue-on-error`, no non-blocking `if` gate — and
  its step names). Use this only as a hint for classifying `unclassified`
  obligations against tier 1/2; never treat it as authoritative on its own, and
  never present an inferred mapping as certain.

## Enforcement tiers, in priority order

1. **CI-blocking** — fails the build. A required check in a workflow job with no
   `continue-on-error` and no non-blocking conditional gate.
2. **CI-checked, non-blocking** — some automated process verifies it (a script run
   in CI, a scheduled job) without failing the build — e.g. `continue-on-error:
   true`, or a job gated to a narrower trigger than the main quality gate.
3. **Human-verified only** — the policy file itself says a human must do the
   verification (reading state, applying a change) rather than CI, often because
   the credential/authority needed is deliberately withheld from automation.
4. **Written policy only** — everything else: a real rule, but nothing technical
   checks it. This is the default when an obligation doesn't match tiers 1–3, not a
   sign something's missing.

## For every `unclassified` obligation

The script can only report what it can regex out of a comment annotation — it has
no way to know an obligation's tier the first time it's ever looked at. For each
`unclassified` obligation:

1. Read the obligation's own policy file in full (not just the matched line) —
   the tier is often explained in that section's "Rationale:" paragraph, or in a
   dedicated subsection the way `branch-protection.md`-style policies sometimes
   explicitly carve themselves out of an automated check.
2. Cross-reference `ci_jobs` for a plausible match by keyword — say explicitly
   when a mapping is inferred rather than self-declared, exactly as you would in
   the final table. An obligation can be "backed by" CI indirectly (e.g. it depends
   on a branch-protection ruleset's actual configured content, which this script
   cannot see) — flag that dependency rather than guessing at the ruleset's state.
3. If it still doesn't obviously fit any tier, ask the user rather than forcing a
   guess.
4. **Write the classification back into the policy file** as the tier annotation,
   in the same place the script looks for it (the obligation's own line or the
   line right after it). This is the entire point of the annotation convention: the
   next run of this skill — on this obligation, in this repo — never has to pay the
   reasoning cost again. Only a genuinely new or reworded obligation should ever
   show up `unclassified` after the first pass.

Treat writing that annotation as a small, reversible edit to `.policy/<topic>.md`
itself (not to `CONTRIBUTING.md`/`CLAUDE.md`, which this skill never touches) —
confirm with the user before committing it, same as any other edit to a policy
file, and keep it a separate commit from anything substantive this run also found.

## Presenting the result

Table: `ID | Statement | Policy file | Enforcement`, with a short note under the
table for every obligation whose mapping was inferred rather than self-declared or
script-verified. Don't judge whether an obligation *should* have stronger
enforcement — that's a design conversation, not a status report. Don't modify
anything beyond writing back tier annotations for obligations you just classified,
and never file issues or open PRs from this skill.
