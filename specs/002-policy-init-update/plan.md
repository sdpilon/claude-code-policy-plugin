# Implementation Plan: Policy Init and Safe Update

**Branch**: `002-policy-init-update` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-policy-init-update/spec.md`

## Summary

Add `/policy:init`, which bootstraps a minimal `.policy/` skeleton with a manifest, and
`/policy:update`, which uses that manifest to apply newer shipped templates to unmodified
files while reporting customized, missing, and no-longer-shipped files. The manifest holds a
format version, the plugin version, and a per-file content fingerprint (SHA-256 over LF-normalized
bytes). Hashing and classification live in one shared, stdlib-only script so both skills
use the same logic (Constitution IV).

## Technical Context

**Language/Version**: Python 3 (stdlib only), matching `scripts/policy_ids.py` and `scripts/policy_frontmatter.py`

**Primary Dependencies**: None beyond the standard library (`hashlib`, `json`, `difflib`, `argparse`, `pathlib`)

**Storage**: Files under the consuming repo's `.policy/`: `README.md` (tracked), `manifest.json` (new), `rule/` and `retired/` (created empty, never tracked)

**Testing**: `python3 -m unittest discover -s tests` (pytest is not installed; the existing suite uses `unittest`)

**Target Platform**: Any machine running Claude Code with a `python3` on PATH (macOS, Linux, Windows)

**Project Type**: Claude Code plugin: skills plus shared scripts

**Performance Goals**: Not applicable; a repo has a handful of tracked files

**Constraints**: No new runtime dependencies. Never overwrite a file whose fingerprint doesn't match the manifest. Fail closed on a missing or corrupt manifest.

**Scale/Scope**: One tracked file in v0.2.0; the design allows more entries without schema change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / constraint | Status | Notes |
|---|---|---|
| I. Mechanism, Never Content | Pass | The shipped `policy-readme.md` template describes the convention generically; it contains no riposte-specific content. |
| II. Single Source of Truth | Pass | Init and update never create or alter rule files or IDs. `rule/` and `retired/` are created empty. |
| III. Checkpointed Steps | Pass with justification | `/policy:update` applies unmodified files and reports in one run. It has no next step, so no checkpoint applies. The auto-apply behavior was an explicit user decision during brainstorming. Recorded here, not as a violation. |
| IV. Deterministic Before Generative | Pass | Fingerprinting, classification, and the diff are computed by `scripts/policy_manifest.py`. The skill only invokes the script and presents its output. |
| V. Honest Enforcement Reporting | Pass | Update reports what it did and what it didn't touch. It makes no claim about enforcement. |
| Plugin: standard plugin layout | Pass | `skills/init/` and `skills/update/` each hold a `SKILL.md` and their script. Shared code goes in root `scripts/`, as in the existing shared modules. |
| Plugin: no extra adoption burden | Pass | Init is opt-in. Projects with no manifest keep working; update fails closed with a recovery message. |
| Plugin: skill descriptions validated | Planned | Fresh-context trigger tests for `init` and `update` are a task in `tasks.md`. |
| Plugin: deferred phases in ROADMAP only | Pass | The `init-and-safe-update` entry moves from `deferred` to in-progress in `ROADMAP.yaml` as part of this feature. Nothing is half-built in shipped skills. |
| Plugin: README describes current state | Planned | README gets the two new skills and the manifest convention, written as the post-feature state. |

No violations require entries in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-policy-init-update/
├── plan.md              # This file
├── research.md          # Phase 0: decisions behind the technical choices
├── data-model.md        # Phase 1: manifest and tracked-entry schema
├── quickstart.md        # Phase 1: end-to-end validation scenarios
├── contracts/
│   ├── manifest.md      # On-disk manifest format and version rules
│   └── commands.md      # /policy:init and /policy:update behavior, outputs, exit codes
├── checklists/
│   └── requirements.md
└── tasks.md             # Created by /speckit-tasks, not by this command
```

### Source Code (repository root)

```text
scripts/
├── policy_manifest.py         # NEW: fingerprint, read/write manifest, classify tracked files, diff
├── policy_ids.py              # existing
└── policy_frontmatter.py      # existing

skills/
├── init/                      # NEW
│   ├── SKILL.md
│   └── scripts/init_policy.py
└── update/                    # NEW
    ├── SKILL.md
    └── scripts/update_policy.py

templates/
├── policy-readme.md           # NEW: shipped .policy/README.md (the one tracked file)
└── rule-template.md           # existing

tests/
├── test_policy_manifest.py    # NEW: fingerprint normalization, classification table, manifest parsing
├── test_init_policy.py        # NEW: fresh init, idempotence, user-owned README
└── test_update_policy.py      # NEW: one case per row of the spec's update table, plus fail-closed cases

.claude-plugin/
├── plugin.json                # version 0.1.0 -> 0.2.0
└── marketplace.json           # version 0.1.0 -> 0.2.0

ROADMAP.yaml                   # init-and-safe-update: deferred -> in-progress
README.md                      # new skills and manifest convention
```

**Structure Decision**: Shared logic in root `scripts/policy_manifest.py`, imported by both skill
scripts through the same `sys.path` bootstrap that `add_rule.py` uses. Each skill is a thin CLI over
that module. Tests follow the existing `tests/test_*.py` pattern.

## Phase 0 & 1 Artifacts

- `research.md`: resolved decisions (hash algorithm, line-ending normalization, diff format, module placement, exit-code scheme).
- `data-model.md`: the manifest schema and the classification states.
- `contracts/manifest.md`: the on-disk format and version rules.
- `contracts/commands.md`: init and update behavior, outputs, and exit codes.
- `quickstart.md`: the end-to-end scenarios that must pass before the feature is done.

## Complexity Tracking

No constitution violations to justify.
