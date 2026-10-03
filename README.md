# policy

Claude Code plugin for a repo's committed process-policy layer: a
`.policy/<topic>.md` source of truth, with two derived forms (a human-facing
narrative doc, usually `CONTRIBUTING.md`, and an agent-operational doc, usually
`CLAUDE.md` or `.claude/rules/<topic>.md`), plus the judgment calls around adding
to it, keeping the derived docs in sync, auditing what's self-checkable, and
reporting on what's actually enforced.

This plugin ships the **mechanism** — skills that operate on any repo following
this convention. It never ships a project's actual obligations, its actual CI
audit script, or its actual constitution/principles doc; those stay in the
project that owns them. Extracted from [riposte](https://github.com/sdpilon/riposte)'s
in-repo `.claude/skills/policy-*`, generalized to drop riposte-specific content.

## Skills

- **`/policy:add`** — add or edit an obligation in `.policy/<topic>.md`. Writes
  only that layer; flags that the derived docs are now unsynced.
- **`/policy:sync`** — checks whether `CONTRIBUTING.md`/the agent-operational doc
  still match `.policy/*.md`, and propagates approved changes.
- **`/policy:judge`** — decides whether a proposed rule is repo policy or personal
  preference that belongs in memory/a local doc instead.
- **`/policy:audit`** — documents the contract for a CI-run script that checks
  self-verifiable obligations against live repo state. The actual script stays in
  the consuming project (it encodes that project's specific checks).
- **`/policy:status`** — reports every obligation's enforcement tier
  (CI-blocking / CI-checked non-blocking / human-verified only / written-policy-
  only). Backed by `skills/status/scripts/policy-status.sh`, a deterministic
  script that extracts obligations and best-effort CI job structure without
  needing an LLM to re-read every file on every call — see that script's docstring
  for the tier-annotation convention that makes repeat runs fast.

## Conventions this plugin assumes

- A `.policy/` directory at the repo root, one `.md` file per topic.
- Each obligation written as `**<PREFIX>-N**: <subject> MUST/SHOULD/MUST
  NOT/MAY <requirement>` — one sentence, one modal verb, IDs never renumbered or
  reused.
- Optionally, a human-facing `CONTRIBUTING.md` and an agent-operational doc
  (`CLAUDE.md`, Claude Code's native `.claude/rules/<topic>.md`, or equivalent)
  that each link to the `.policy/<topic>.md` files they derive from.
- Optionally, a product-principles doc (e.g. a Spec Kit `constitution.md`) that
  `/policy:add` checks before writing something that might belong there instead.

None of these are enforced by the plugin itself — a project adopts the convention
by following it, the same way `.specify/` works for Spec Kit.

## Status

v0.1.0 — first extraction pass. Project vs. user scoping is not planned as
plugin code: Claude Code's native `.claude/rules/` (project) and
`~/.claude/rules/` (user) already provide it. Human vs. agent scoping is not yet
built. Other deferred phases are tracked in `ROADMAP.yaml`, not narrated here.

## Installing into a project

Register this repo as a local marketplace and install at project scope — see
Claude Code's plugin docs.
