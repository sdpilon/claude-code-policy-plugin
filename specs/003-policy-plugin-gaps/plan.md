# Implementation Plan: Policy Plugin Gaps

**Branch**: `003-policy-plugin-gaps` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-policy-plugin-gaps/spec.md`

## Summary

Close the gaps the riposte migration session hit, excluding migration. Four pieces of
deterministic mechanism, plus two documentation fixes:

1. `record_sync.py` writes each named rule's content hash into `synced_hash` (US1).
2. `edit_rule.py` edits one or more rules atomically, sets `modified`, and supports a
   preview (US2, US3). One command covers single and bulk edits.
3. `audit_checks.py` runs the `ci-checked` checks from a consumer-supplied registry,
   dedupes issues by a label key, and files issues for failing and unbuilt checks (US4).
4. Plugin root discovery and frontmatter-parser docs (US5, US6). Discovery is a research
   item, see `research.md`.

Every new command is a script under the skill that uses it, following the existing layout
(`skills/<skill>/scripts/`). Shared logic goes in `scripts/`.

## Technical Context

**Language/Version**: Python 3.14 (`requires-python = ">=3.14"`), stdlib only at runtime

**Primary Dependencies**: none at runtime. Dev tools via `uv`: ruff, pymarkdownlnt,
shellcheck-py, shfmt-py. The audit's GitHub adapter shells out to the `gh` CLI.

**Storage**: rule files under `.policy/rule/` and `.policy/retired/`, plain Markdown with
YAML-style frontmatter. No database.

**Testing**: `python -m unittest discover -s tests`, run by `tools/check.sh` and CI.

**Target Platform**: developer machines (macOS, Linux) and `ubuntu-24.04` CI.

**Project Type**: Claude Code plugin: skills under `skills/`, supporting scripts beside them,
shared modules under `scripts/`.

**Performance Goals**: none beyond "a repo with a few hundred rules finishes in seconds".

**Constraints**: writes must be atomic per file; a multi-rule edit is all-or-none; no network
access except the audit's issue calls; the plugin ships no project check implementations.

**Scale/Scope**: about 4 new scripts, 1 new skill (`edit`), 3 test modules, doc updates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Mechanism, Never Content | The audit's check implementations come from a consumer-supplied registry (`--registry`). The plugin ships dispatch, dedupe, and filing only. | Pass |
| II. Single Source of Truth | `edit_rule.py` writes only `.policy/rule/*.md`. Derived docs are not touched. | Pass |
| III. Checkpointed Steps | `edit` shows the diff (`--preview`) and the SKILL requires confirmation before the write run. `record_sync` runs only after the sync skill's approval step. | Pass |
| IV. Deterministic Before Generative | Hashing, ID handling, validation, and the dedupe key are all scripted. The LLM only proposes the edit values. | Pass |
| V. Honest Enforcement Reporting | The audit logs pass, filed, or skipped per rule and never claims a check ran that did not. | Pass |

Plugin constraints: all new skills are standard `skills/<name>/SKILL.md` with scripts beside
them. No consuming repo has to adopt anything new. The new `edit` skill's description must be
validated with fresh-context trigger tests, per the constitution's Development Workflow.

No violations. Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-policy-plugin-gaps/
├── plan.md              # This file
├── research.md          # Phase 0: decisions and open items
├── data-model.md        # Phase 1: entities and state
├── quickstart.md        # Phase 1: runnable validation guide
├── contracts/
│   ├── record_sync.md   # CLI contract for record_sync.py
│   ├── edit_rule.md     # CLI contract for edit_rule.py
│   └── audit_checks.md  # CLI and registry contract for audit_checks.py
├── checklists/
│   └── requirements.md
└── tasks.md             # Created by /speckit-tasks, not by this plan
```

### Source Code (repository root)

```text
scripts/
├── policy_frontmatter.py   # extend: return-type docs, statement check (shared)
└── policy_manifest.py      # reuse: atomic_write_bytes

skills/sync/
├── SKILL.md                # step 6 now calls record_sync.py
└── scripts/
    ├── sync_status.py      # reuse: content_hash
    └── record_sync.py      # NEW (US1)

skills/edit/                # NEW skill
├── SKILL.md
└── scripts/
    └── edit_rule.py        # NEW (US2, US3)

skills/audit/
├── SKILL.md                # documents the registry, tracker, and dedupe key
└── scripts/
    ├── audit_checks.py     # NEW (US4)
    └── github_tracker.py   # NEW: gh-backed tracker adapter (US4)

tests/
├── test_record_sync.py     # NEW
├── test_edit_rule.py       # NEW
└── test_audit_checks.py    # NEW
```

**Structure Decision**: follows the existing per-skill `scripts/` layout. `edit` gets its own
skill because it is user-invoked, like `add` and `retire`. `record_sync` lives under `sync`,
and `audit_checks` lives under `audit`, since those are the skills that run them.

## Phase 0 and Phase 1 summary

- Research decisions and open items: [research.md](research.md)
- Entities and state: [data-model.md](data-model.md)
- CLI contracts: [contracts/](contracts/)
- Validation guide: [quickstart.md](quickstart.md)

## Complexity Tracking

Not applicable: no constitution violations.
