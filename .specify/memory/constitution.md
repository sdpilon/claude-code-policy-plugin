# policy Constitution

## Core Principles

### I. Mechanism, Never Content

The plugin MUST ship only generic mechanism: skills, templates, and scripts that operate on
any repo following the `.policy/` convention. It MUST NOT ship any project's actual
rules, its CI audit script, or its constitution/principles doc. Riposte-specific (or any
other single-project) content MUST NOT appear in shipped files; examples drawn from a real
project MUST be generalized or clearly marked as illustrative.

Rationale: the plugin was extracted from riposte so other repos can adopt the same convention.
Project content leaking in makes it wrong for every other consumer.

### II. Single Source of Truth

Each rule is authoritative only in its own file, `.policy/rule/<id>.md`, which MAY be nested
in organizational subdirectories that carry no identity meaning. Derived forms
(`CONTRIBUTING.md`, the agent-operational doc such as `CLAUDE.md` or `.claude/rules/`) MUST be
treated as outputs and MUST NOT be edited as if they were the source.

Rule IDs MUST be integers, zero-padded to a minimum of three digits in filenames and bold
statement tokens (e.g. `047`), with no alphabetic prefix. IDs MUST be unique across the whole
`.policy/rule/` tree. Allocation MUST take one greater than the highest ID present, including
tombstones, and MUST re-check for collision immediately before writing.

An ID MUST NOT be reused, even after its rule is deleted. A retired rule MUST leave a
frontmatter-only tombstone at `.policy/retired/<id>.md`, which counts toward allocation.

Each rule MUST be one sentence with exactly one modal verb (MUST / SHOULD / MUST NOT / MAY).

Rationale: drift between a source and its derived docs is silent, and no test catches it.
One rule per file keeps diffs and ownership local and removes the arbitrary topic decision.
Stable, never-reused IDs keep references and drift detection meaningful over time.

### III. Checkpointed Steps

Each skill MUST be one distinct step (`add` writes `.policy/`, `sync` propagates to derived
docs, `judge` decides policy vs. preference). A skill MAY continue into the next step in the
same run, but only through an explicit checkpoint: it MUST show what the step just produced and
let the person correct it, continue, or stop (e.g. via `AskUserQuestion`) before the next step
writes anything. `sync` MUST re-check that the source hasn't changed since its proposal before
applying it.

Rationale: the goal is a chance to correct each layer before the next one is built on it, not
forced separate invocations. A checkpoint gives that without making the person re-run each
skill by hand.

### IV. Deterministic Before Generative

Wherever an answer can be computed (extracting rules, parsing CI job structure, hashing
content to detect staleness), it MUST be computed by a script, not re-derived by an LLM reading
files on every run. LLM judgment is reserved for what can't be mechanized: wording, policy vs.
preference, and whether a derived doc still means the same thing as its source.

Rationale: scripts are repeatable, fast, and cheap. LLM re-derivation is slow, costly, and can
give a different answer on each run.

### V. Honest Enforcement Reporting

Skills MUST report a rule's real enforcement tier (CI-blocking, CI-checked non-blocking,
human-verified only, written-policy-only) and MUST NOT imply that written policy, or policy
loaded into agent context, is enforced. Uncertain classifications MUST be labeled as
best-effort rather than presented as fact.

Rationale: agent-facing instructions (CLAUDE.md, rules) are context, not enforcement. The
plugin's value depends on never overstating what is actually checked.

## Plugin Constraints

- The plugin MUST stay a standard Claude Code plugin (skills under `skills/<name>/SKILL.md`,
  supporting scripts beside the skill that uses them) installable from a local marketplace at
  project scope.
- The plugin MUST NOT require a consuming repo to adopt anything beyond the documented
  convention. Optional pieces (`CONTRIBUTING.md`, a principles doc) MUST degrade gracefully
  when absent.
- Native Claude Code features (e.g. `.claude/rules/`, user-level `~/.claude/rules/`) SHOULD be
  used in place of re-implementing equivalent loading or scoping behavior inside the plugin.
- Skill descriptions MUST be written so they trigger on the intended requests and not on
  adjacent ones. A material change to a description SHOULD be validated with fresh-context
  trigger tests.

## Development Workflow

- Behavior changes to a skill SHOULD be compared side by side against the original in-repo
  riposte skills before any cutover in that repo.
- Deferred phases (hash-manifest safe-update, human-vs-agent scoping) MUST be recorded as
  entries in `ROADMAP.yaml` at the repo root, not in README.md, and MUST NOT be half-built
  in shipped skills.
- README.md MUST describe the plugin's current state only, not a changelog of how it got there.

## Governance

This constitution supersedes other practice documents in this repo. Spec Kit plans and reviews
MUST check proposed changes against the Core Principles; any deviation MUST be justified in the
plan's complexity/violation tracking.

Amendments are made through `/speckit-constitution`, with a Sync Impact Report reviewed before
commit. Versioning follows semantic versioning: MAJOR for removing or redefining a principle,
MINOR for adding a principle or section or materially expanding one, PATCH for clarifications
and wording.

**Version**: 2.0.1 | **Ratified**: 2026-10-02 | **Last Amended**: 2026-10-02
