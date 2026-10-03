# policy

Claude Code plugin for a repo's committed process-policy layer. Each rule is its own
file under `.policy/rule/`, the source of truth, with two derived forms: a human-facing
narrative doc (usually `CONTRIBUTING.md`) and an agent-operational doc (usually
`CLAUDE.md`, or `.claude/rules/<slug>.md`). The plugin also covers the judgment calls
around adding rules, keeping derived docs in sync, auditing what's self-checkable, and
reporting on what's actually enforced.

This plugin ships the **mechanism**: skills that operate on any repo following this
convention. It never ships a project's actual rules, its CI audit script, or its
constitution/principles doc. Those stay in the project that owns them. Extracted from
[riposte](https://github.com/sdpilon/riposte)'s in-repo `.claude/skills/policy-*`,
generalized to drop riposte-specific content.

## Skills

- **`/policy:add`**: adds a rule as a new file under `.policy/rule/`, with the next
  free ID. Writes only that layer and flags that derived docs are now out of sync.
- **`/policy:sync`**: checks whether `CONTRIBUTING.md` and the agent-operational doc
  still match `.policy/rule/`, using each rule's `audience` to pick its targets.
  Propagates only approved changes, and skips rules whose content hasn't changed since
  the last sync.
- **`/policy:judge`**: decides whether a proposed rule is repo policy or personal
  preference that belongs in memory or a local doc instead.
- **`/policy:audit`**: documents the contract for a CI-run script that checks
  self-verifiable rules against live repo state. The script itself stays in the
  consuming project, since it encodes that project's specific checks.
- **`/policy:status`**: reports every rule's title and enforcement tier. The tier comes
  from the rule's `verification` frontmatter. Backed by
  `skills/status/scripts/policy-status.sh`, a deterministic script, so repeat runs
  don't need an LLM to re-read every file.
- **`/policy:migrate`**: one-time conversion of a repo's old `.policy/<topic>.md` files
  into the one-rule-per-file layout. It flags anything needing a human decision, such
  as a rationale shared between rules, instead of guessing.

## Conventions this plugin assumes

- **One rule per file.** Each rule lives at `.policy/rule/<id>.md`. Subdirectories
  under `.policy/rule/` are optional, purely organizational, and carry no identity.
  Moving a file never changes its ID.
- **IDs.** Each rule's ID is an integer, zero-padded to at least three digits in the
  filename and in the bold statement token (`**047**: ...`). IDs are globally unique,
  allocated as one more than the highest in use, and never reused.
- **Retired rules.** Retiring a rule leaves a frontmatter-only tombstone at
  `.policy/retired/<id>.md`. Tombstones count toward ID allocation, so a retired ID is
  never reissued.
- **Frontmatter.** Each rule file carries `title`, optional `tags`, `created`,
  `modified`, a required `audience` (`human`, `agent`, or both), a `verification`
  method (`ci-blocking`, `ci-checked`, `human-verified`, or `written-only`), and a
  `synced_hash` that `/policy:sync` maintains.
- **Statements.** Each rule is one sentence with one modal verb (MUST, SHOULD,
  MUST NOT, or MAY), and carries its own short rationale. Related rules cross-link by
  number instead of sharing rationale text.
- **Derived docs** are outputs, never sources. Edit the rule, then sync.

Nothing here is enforced by the plugin itself. A project adopts the convention by
following it, the same way `.specify/` works for Spec Kit.

## Status

Pre-release (`0.1.0`). The one-rule-per-file layout is specified and planned but not
yet implemented in the skills and scripts. The constitution (`.specify/memory/constitution.md`)
describes the target convention. Project vs. user scoping is not planned as plugin
code: Claude Code's native `.claude/rules/` (project) and `~/.claude/rules/` (user)
already provide it. Deferred phases are tracked in `ROADMAP.yaml`.

## Installing into a project

Register this repo as a local marketplace and install at project scope. See Claude
Code's plugin docs.
