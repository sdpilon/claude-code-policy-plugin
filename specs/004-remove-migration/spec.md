# Feature Specification: Remove the Migration Feature

**Feature Branch**: `004-remove-migration`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "remove the migration feature entirely"

## Clarifications

### Session 2026-10-03

- Q: Does any repo still use the old `.policy/<topic>.md` layout and need converting before migration is removed? → A: No repo still uses the old layout; removal can proceed as written.
- Q: Should removing this command bump the plugin's version number in this change? → A: No; the version is set at release time.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plugin no longer offers migration (Priority: P1)

A maintainer of the policy plugin removes the one-time migration capability (converting a repo's old `.policy/<topic>.md` files into one-rule-per-file under `.policy/rule/`). After the change, the plugin offers no migration command, and nothing it ships or documents describes migration as something it does.

**Why this priority**: This is the whole feature. Until the command, its guidance, and its descriptions are gone, the plugin still advertises a capability the maintainer has decided to drop.

**Independent Test**: Inspect the plugin's shipped commands and its user-facing descriptions after the change. No migration command is listed, and no description names migrating as a capability.

**Acceptance Scenarios**:

1. **Given** the plugin at the head of the default branch after this change, **When** a user looks for the `/policy:migrate` command, **Then** no such command is available.
2. **Given** the plugin's README, plugin metadata, and marketplace entry, **When** they are read, **Then** none of them lists migration or "migrating" among the plugin's capabilities.
3. **Given** the repository after this change, **When** a maintainer searches the current tree for the migration command, its skill, or its conversion script, **Then** no live file defines or invokes them.

---

### User Story 2 - Test suite and CI stay green without migration tests (Priority: P2)

A maintainer runs the repository's checks after the removal. The migration-specific tests are gone, every other test still runs, and the continuous-integration checks pass.

**Why this priority**: Removing code without removing its tests leaves CI failing on a missing script. Keeping the other tests running proves the removal did not break unrelated behavior.

**Independent Test**: Run the full unit test suite and the lint/format/markdown/shell checks. All pass, and no test refers to the migration script.

**Acceptance Scenarios**:

1. **Given** the change applied, **When** the unit test suite runs, **Then** it passes and no migration test is collected.
2. **Given** the change applied, **When** the CI checks run, **Then** they pass.

---

### User Story 3 - Historical specs are preserved (Priority: P3)

A future reader of the spec history can still see what the migration feature was, why it was built, and when it was decided to remove it. The earlier spec artifacts are not rewritten to erase it.

**Why this priority**: Specs 001 through 003 are records of decisions. Editing them to remove migration references would falsify the history, and it is not needed for the product to work.

**Independent Test**: Diff the `specs/001-*`, `specs/002-*`, and `specs/003-*` directories against their state before this change. No file in them has changed.

**Acceptance Scenarios**:

1. **Given** the change applied, **When** the earlier spec directories are compared with their prior state, **Then** they are byte-identical.

---

### Edge Cases

- A repo still on the old topic-file layout (`.policy/<topic>.md`) can no longer be converted by the plugin. Such a repo must be converted by hand, or with a release of the plugin that still includes migration.
- Removal must be recorded as tracked deletions. Leaving behind an untracked script or a stale `__pycache__` directory would leave the feature half-removed.
- A migration reference in a user-facing description that is not caught by search (for example, a generic "migrating" word in a list of capabilities) would keep advertising the feature. Descriptions must be reviewed by reading, not only by search.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The plugin MUST NOT provide the `/policy:migrate` command, and its skill definition MUST be removed.
- **FR-002**: The migration conversion script and the unit tests that exercise it MUST be removed from the repository.
- **FR-003**: The plugin's README MUST NOT list migration as a feature.
- **FR-004**: The plugin metadata and marketplace entry descriptions MUST NOT list migrating among the plugin's capabilities.
- **FR-005**: After the change, the unit test suite and the CI checks MUST pass, with no test referring to the removed script.
- **FR-006**: No live file in the repository (outside the historical spec directories) MUST reference the removed command, skill path, or script.
- **FR-007**: Earlier spec directories (`specs/001-*` through `specs/003-*`) MUST NOT be edited to remove migration references.
- **FR-008**: The removal MUST be expressed as tracked deletions and edits, so it is reviewable as one change.

### Key Entities

Not applicable. This feature removes behavior and does not introduce or change data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A search of the current repository, excluding the historical spec directories, finds zero references to the migration command or the migration skill path.
- **SC-002**: The unit test suite and the CI checks pass on the change, with every test that passed before the change still running except the migration tests.
- **SC-003**: The plugin's README, plugin metadata, and marketplace entry together list only capabilities the plugin ships, with migration absent from all of them.
- **SC-004**: The earlier spec directories show zero changed files in the change's diff.

## Assumptions

- The migration feature has no remaining users who depend on it. Confirmed by the maintainer in clarification: no repo still uses the old topic-file layout.
- Specs 001 through 003 are historical records. Their references to migration (such as the spec 003 note that migration "is removed in a later spec") stay as they are.
- Removing the feature does not by itself require a plugin version bump. Versioning is decided at release time, outside this spec.
- Local build artifacts such as `__pycache__` directories are not tracked and need no removal from version control, though they should not be left in the working tree.
