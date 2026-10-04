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

- **`/policy:init`**: bootstraps `.policy/` in a repo that doesn't have one: an empty
  `rule/` and `retired/`, a starter `README.md`, and `manifest.json`. Never overwrites
  an existing file.
- **`/policy:update`**: applies newer shipped templates to files that are still unmodified.
  Customized, missing, and no-longer-shipped files are reported and left alone. Exits
  non-zero on drift, so CI can surface it.
- **`/policy:add`**: adds a rule as a new file under `.policy/rule/`, with the next
  free ID. Writes only that layer and flags that derived docs are now out of sync.
- **`/policy:edit`**: changes the title, tags, audience, verification, statement, or
  rationale of one or more existing rules. Previews first, then applies all-or-none, and
  sets `modified`. Backed by `skills/edit/scripts/edit_rule.py`.
- **`/policy:sync`**: checks whether `CONTRIBUTING.md` and the agent-operational doc
  still match `.policy/rule/`, using each rule's `audience` to pick its targets.
  Propagates only approved changes, records each applied rule's `synced_hash` through
  `skills/sync/scripts/record_sync.py`, and skips rules whose content hasn't changed since
  the last sync.
- **`/policy:judge`**: decides whether a proposed rule is repo policy or personal
  preference that belongs in memory or a local doc instead.
- **`/policy:audit`**: runs the `ci-checked` rules' checks in CI and files a GitHub issue
  for each failing or unbuilt check, deduplicated by a `policy-audit:<check>` label. The
  plugin supplies the runner (`skills/audit/scripts/audit_checks.py`). Each project supplies
  its own checks, in a registry file, since they encode that project's specifics.
- **`/policy:status`**: reports every rule's title and enforcement tier. The tier comes
  from the rule's `verification` frontmatter. Backed by
  `skills/status/scripts/policy_status.py` (called directly, or through its
  `policy-status.sh` wrapper), a deterministic script, so repeat runs
  don't need an LLM to re-read every file.

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
- **Write lock.** Rule writes from `record_sync` and `edit` hold an advisory lock,
  `.policy/rule/.write.lock`, so concurrent writes can't interleave. Add the file to `.gitignore`
  if you don't want it tracked. It is advisory: tools that write rule files directly bypass it.
- **Derived docs** are outputs, never sources. Edit the rule, then sync.
- **Manifest.** `.policy/manifest.json` records what the plugin wrote into `.policy/`: each
  tracked file's content fingerprint and the plugin version that shipped it. Only files
  listed there are ever updated by `/policy:update`. Don't edit it by hand.

Nothing here is enforced by the plugin itself. A project adopts the convention by
following it, the same way `.specify/` works for Spec Kit.

## Status

Pre-release (`0.2.0`). The one-rule-per-file layout is implemented: the skills, scripts,
and tests live in this repo, with the constitution (`.specify/memory/constitution.md`)
describing the convention. Human vs. agent scoping is not yet built. Project vs. user
scoping is not planned as plugin code: Claude Code's native `.claude/rules/` (project) and
`~/.claude/rules/` (user) already provide it. Deferred phases are tracked in `ROADMAP.yaml`.

## Paths in skills

Skills refer to scripts as `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/...`, where
`${CLAUDE_PLUGIN_ROOT}` is the plugin's root directory: the folder that contains `skills/` and
`scripts/`. If the variable is not set in the shell that runs a script, the plugin root is the
folder two levels above the skill's base directory, which the harness reports when the skill loads.

## Installing into a project

Register this repo as a local marketplace and install at project scope. See Claude
Code's plugin docs.
