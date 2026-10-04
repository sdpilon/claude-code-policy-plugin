# Implementation Plan: Remove the Migration Feature

**Branch**: `004-remove-migration` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-remove-migration/spec.md`

## Summary

Remove the one-time migration capability (`/policy:migrate`, its skill, its conversion script,
and its tests) and every user-facing description that advertises it. The change is pure
deletion plus description edits. It adds no new behavior, does not bump the plugin version
(per clarification Q2), and leaves historical spec directories untouched (FR-007). The
maintainer confirmed that no repo still uses the old topic-file layout, so no conversion path
is needed (clarification Q1).

## Technical Context

**Language/Version**: Python 3.14 (`requires-python = ">=3.14"` in `pyproject.toml`); shell for CI lint steps

**Primary Dependencies**: `ruff`, `pymarkdownlnt`, `shellcheck-py`, `shfmt-py` (dev group, `pyproject.toml`); standard-library `unittest` for tests

**Storage**: N/A. The feature reads and writes `.policy/` files only at runtime; this change does not touch stored data.

**Testing**: `uv run python -m unittest discover -s tests` (CI step "Unit tests"), plus the lint, format, markdown, and shell checks in `.github/workflows/checks.yml`

**Target Platform**: Claude Code plugin (local marketplace install at project scope); CI on `ubuntu-24.04`

**Project Type**: Claude Code plugin: skills under `skills/<name>/SKILL.md`, supporting scripts beside them, Python tests under `tests/`

**Performance Goals**: N/A. Removal changes no runtime path.

**Constraints**: Historical spec directories (`specs/001-*` through `specs/003-*`) must not change (FR-007). The change must be tracked deletions and edits, so it reviews as one unit (FR-008).

**Scale/Scope**: 1 skill directory (`skills/migrate/`, 1 script), 1 test file, 1 README line, 2 metadata description strings. About 6 files touched.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` (v2.0.1).

- **I. Mechanism, Never Content**: PASS. Removing the migration script and its guidance does not add project content to the plugin.
- **II. Single Source of Truth**: PASS. Rule-ID and rule-file behavior is unchanged. Migration only converted old files into this layout.
- **III. Checkpointed Steps**: PASS (not applicable). No skill gains or loses a checkpoint. Other skills are untouched.
- **IV. Deterministic Before Generative**: PASS (not applicable). No logic is added.
- **V. Honest Enforcement Reporting**: PASS (not applicable). No enforcement tier changes.
- **Plugin Constraints**: PASS. The plugin remains a standard Claude Code plugin. Removing one skill directory keeps the rest installable. The plugin still requires nothing new of consuming repos.
- **Development Workflow, README current state only**: PASS. Removing the `/policy:migrate` line from the README keeps it describing current state; no changelog entry is added.
- **Development Workflow, deferred phases in ROADMAP.yaml**: PASS (not applicable). Removal is not a deferred phase, and `ROADMAP.yaml` has no migration entry to update.

No violations, so Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-remove-migration/
├── spec.md              # Feature spec (with Clarifications session)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── quickstart.md        # Phase 1 output: validation run guide
├── checklists/
│   └── requirements.md  # Spec quality checklist (16/16)
└── tasks.md             # Phase 2 output (/speckit-tasks) — NOT created here
```

`data-model.md` and `contracts/` are not generated. The spec has no entities, and the
change removes an interface rather than adding one.

### Source Code (repository root)

Files this change deletes or edits:

```text
skills/migrate/                      # DELETE: SKILL.md, scripts/migrate_rules.py,
                                     #         scripts/__pycache__/ (local artifact)
tests/test_migrate_rules.py          # DELETE: migration unit tests
README.md                            # EDIT: remove the /policy:migrate bullet (line 45)
.claude-plugin/plugin.json           # EDIT: drop "migrating" from description; version unchanged
.claude-plugin/marketplace.json      # EDIT: same description edit; version unchanged
```

Files deliberately left alone:

```text
specs/001-*, specs/002-*, specs/003-*   # Historical records (FR-007)
.github/workflows/checks.yml            # Runs discover over tests/; no migrate reference
pyproject.toml                          # No migrate reference
```

**Structure Decision**: Single-project plugin layout, unchanged. Only deletions and description
edits; no new directories.

## Phase 0: Research

No `NEEDS CLARIFICATION` markers remain in the spec or in Technical Context, so there is nothing
to research. The one open choice, how to remove the feature, is settled by the spec: tracked
deletions and edits (FR-008). See `research.md`.

## Phase 1: Design & Contracts

- **Data model**: Not applicable (see above).
- **Contracts**: Not applicable. The removed `/policy:migrate` command was the only interface
  involved, and removing it creates no new contract.
- **Quickstart**: `quickstart.md` lists the commands that prove the removal is complete and
  the CI checks still pass.

## Post-design Constitution Check

Re-checked after Phase 1. The design adds nothing, so every principle still passes as above. No
new violations.
