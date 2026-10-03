# Implementation Plan: One-Rule-Per-File Restructuring

**Branch**: `001-rule-per-file-restructure` | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-rule-per-file-restructure/spec.md`

## Summary

Replace the plugin's one-topic-per-file `.policy/<topic>.md` convention with one file per
rule under `.policy/rule/<id>.md`, identified by a global integer (zero-padded to a
minimum of three digits in the filename and bold-line token, e.g. `047`, growing beyond
that as needed — no alphabetic prefix) allocated via a scan-highest-then-recheck-before-write
pattern (no lock, no counter file — the same pattern Spec Kit's own
`create_new_feature.py` uses). Each rule file carries YAML
frontmatter (`title`, `tags`, `created`, `modified`, a required `audience`, a
`verification` method, and a `synced_hash`). `/policy:add`, `/policy:sync`,
`/policy:status`, and `/policy:audit` are updated for the new layout; a new `/policy:migrate`
skill mechanically splits an existing repo's topic files into the new layout and flags
anything (shared rationale) that needs a human decision rather than guessing. The term
"obligation" is renamed to "rule" everywhere in this plugin's own files except
`.specify/memory/constitution.md` (explicitly deferred to a separate amendment).

## Technical Context

**Language/Version**: Python 3 (stdlib only) + POSIX shell, matching the existing
`skills/status/scripts/policy_status.py` / `policy-status.sh` pair. Rule content itself
is Markdown with a YAML-subset frontmatter block.

**Primary Dependencies**: None. No third-party package (notably no PyYAML) — see
research.md for why frontmatter parsing is hand-rolled instead.

**Storage**: Plain files in a consuming repo's own git history, under `.policy/rule/`.
This plugin repository ships no `.policy/` content of its own (Constitution Principle I).

**Testing**: Python stdlib `unittest`. This plugin currently ships zero automated tests;
this feature introduces the first ones, scoped to the new deterministic logic (ID
allocation, frontmatter parsing, migration's rationale-sharing detection) where a bug
would silently corrupt or misclassify a rule.

**Target Platform**: Any POSIX shell + Python 3 environment a Claude Code session runs
in (macOS/Linux) — matches `policy-status.sh`'s existing defensive `python3` check.

**Project Type**: Claude Code plugin (skills + shared scripts + a template), not an
application. No `src/`/service layout applies.

**Performance Goals**: N/A — scripts operate over at most a few hundred small Markdown
files per consuming repo; "fast enough for interactive CLI use" is the only bar.

**Constraints**: No third-party runtime dependency (Constitution Principle IV and the
existing scripts' own ethos). Must not edit `.specify/memory/constitution.md` (deferred
per spec Assumptions). Must not implement `/policy:init` or the hash-manifest
safe-update mechanism (out of scope, tracked in `ROADMAP.yaml`).

**Scale/Scope**: Five existing skills plus one new one (`migrate`); consuming-repo rule
counts expected in the tens to low hundreds.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Mechanism, Never Content | Migration tool and templates operate generically; no project's real rules are shipped. | PASS |
| II. Single Source of Truth | Constitution v2.0.0 (and v2.0.1) redefined Principle II to describe this layout, so the written text now matches the design. | PASS |
| III. Checkpointed Steps | `add`/`sync`/`migrate` each remain one step with a checkpoint before the next; migrate flags shared-rationale cases for a human decision rather than silently resolving them. | PASS |
| IV. Deterministic Before Generative | ID allocation, frontmatter parsing, and sync's change-detection are all pushed into scripts, not re-derived by the model each run. | PASS |
| V. Honest Enforcement Reporting | `verification` frontmatter replaces the inline tier comment with no change in what gets reported. | PASS |
| Plugin Constraints — native features over reimplementation | No re-implementation of `.claude/rules/`-equivalent behavior. | PASS |
| Plugin Constraints — skill descriptions validated | `add`/`sync`/`status`/`audit`/`judge` descriptions change materially (new ID scheme, `audience` field). Fresh-context trigger validation is required before this work is done — tracked as a task, not skipped. | PASS (tracked) |

**Complexity Tracking** (Principle II): resolved. The earlier deviation (written
constitution still describing the old `.policy/<topic>.md` layout) was closed by the
MAJOR amendment to v2.0.0, then the PATCH to v2.0.1. No violations remain, so this table
has no rows.

## Project Structure

### Documentation (this feature)

```text
specs/001-rule-per-file-restructure/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
scripts/                              # NEW — shared deterministic logic, no skill-specific state
├── policy_frontmatter.py             # parse/write the frontmatter block (no PyYAML)
└── policy_ids.py                     # scan .policy/rule/ for highest ID; allocate-with-recheck; format/parse zero-padded filenames

skills/
├── add/
│   ├── SKILL.md                      # updated: writes .policy/rule/<id>.md via policy_ids/frontmatter
│   └── scripts/
│       └── add_rule.py               # NEW: allocates ID, writes file + frontmatter
├── audit/
│   └── SKILL.md                      # updated: recursive scan, verification field
├── judge/
│   └── SKILL.md                      # updated: describes the new convention on hand-off
├── retire/                           # NEW skill (H1 tombstones)
│   ├── SKILL.md
│   └── scripts/
│       └── retire_rule.py            # writes .policy/retired/<id>.md, removes the rule file
├── migrate/                          # NEW skill
│   ├── SKILL.md
│   └── scripts/
│       └── migrate_rules.py          # splits topic files, allocates IDs, flags shared rationale
├── status/
│   ├── SKILL.md                      # updated: shows title, reads verification from frontmatter
│   └── scripts/
│       ├── policy-status.sh          # unchanged entrypoint shape
│       └── policy_status.py          # updated: recursive scan, bare-int ID regex (zero-padding tolerant), frontmatter read
└── sync/
    ├── SKILL.md                      # updated: audience-driven propagation, synced_hash skip
    └── scripts/
        └── sync_status.py            # NEW: per-rule {audience, current_hash, synced_hash, changed}

templates/
└── rule-template.md                  # replaces policy-template.md

tests/
├── test_policy_frontmatter.py
├── test_policy_ids.py
├── test_policy_status.py
├── test_sync_status.py
└── test_migrate_rules.py

.claude-plugin/
├── plugin.json                       # updated: drop "obligation"/topic-file wording
└── marketplace.json                  # updated: same

README.md                             # updated: terminology + convention description
```

**Structure Decision**: Single project, no existing structure to preserve beyond what's
already there. Logic shared across more than one skill (frontmatter parsing, ID
allocation) moves to a repo-root `scripts/` library rather than living inside one
skill's own `scripts/` folder, since `add`, `migrate`, `status`, `audit`, and `sync` all
need it and skills otherwise stay independent per Principle III. `migrate` is a new,
sixth skill rather than a bare script, matching how every other plugin capability is
exposed as a discoverable `/policy:*` command.

## Constitution Check — Post-Design Re-evaluation

No violations remain. Principle II was resolved by the v2.0.0 amendment (see Complexity Tracking).
Design choices in Phase 0/1 actively reinforce rather than strain the other
principles: both new scripts (`policy_ids.py`, `policy_frontmatter.py`) push mechanical
decisions out of the skills entirely (Principle IV); `migrate_rules.py`'s
`needs_review` output is specifically designed to force a human checkpoint rather than
silently resolve ambiguity (Principle III); no project-specific content appears
anywhere in `scripts/`, `templates/`, or the contracts (Principle I). The one tracked,
not-yet-discharged item is the Plugin Constraints gate on fresh-context trigger
validation for the five changed skill descriptions — carried into `tasks.md`, not
resolved by design alone.
