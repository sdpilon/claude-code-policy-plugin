# Feature Specification: Policy Init and Safe Update

**Feature Branch**: `002-policy-init-update`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Add /policy:init to bootstrap .policy/ in a new project, and /policy:update with a hash manifest (.policy/manifest.json) that tracks which init-generated files a consuming project has customized, so plugin template updates apply safely."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bootstrap policy in a new project (Priority: P1)

A developer adopting the policy convention in a repo that has none runs `/policy:init`. The plugin creates the minimal policy skeleton, so the developer can immediately start adding rules with `/policy:add`.

**Why this priority**: Without a bootstrap step, a new project has no defined starting layout, and nothing else in the plugin can be used. This is the minimum viable slice.

**Independent Test**: In an empty scratch repository, run `/policy:init` and confirm the skeleton exists and `/policy:add` can create a rule in it.

**Acceptance Scenarios**:

1. **Given** a repository with no `.policy/` directory, **When** the user runs `/policy:init`, **Then** `.policy/rule/`, `.policy/retired/`, `.policy/README.md`, and `.policy/manifest.json` are created, and the manifest records the README's content fingerprint and the plugin version.
2. **Given** a freshly initialized repository, **When** the user runs `/policy:add` for a new rule, **Then** the rule is created under `.policy/rule/` with ID `001`.
3. **Given** a repository that already has `.policy/manifest.json`, **When** the user runs `/policy:init`, **Then** nothing is written or changed, and the user is told the project is already initialized.

---

### User Story 2 - Update shipped templates without overwriting customizations (Priority: P2)

A developer whose project was initialized with an earlier plugin version runs `/policy:update`. Files the project has not customized are brought up to the newer shipped template automatically. Files the project has customized are left untouched and listed in a report for manual review.

**Why this priority**: Without this, plugin improvements either never reach existing projects or overwrite local edits. Both outcomes undermine trust in the convention.

**Independent Test**: Initialize a project, edit its README, simulate a newer shipped template, and run `/policy:update`. Confirm the edited file is reported and left alone, and an unedited file is updated.

**Acceptance Scenarios**:

1. **Given** a tracked file whose content still matches its recorded fingerprint and a newer shipped template exists, **When** the user runs `/policy:update`, **Then** the file is replaced with the new template, and the manifest records the new fingerprint and plugin version.
2. **Given** a tracked file whose content differs from its recorded fingerprint, **When** the user runs `/policy:update`, **Then** the file is not changed, and the report lists it with a diff against the new template.
3. **Given** a tracked file the user deleted, **When** the user runs `/policy:update`, **Then** the file is not recreated, and the report lists it as missing.
4. **Given** a manifest entry whose shipped template no longer exists in the plugin, **When** the user runs `/policy:update`, **Then** the project's file is kept, and the report says it is no longer shipped.
5. **Given** a shipped file that is not yet in the manifest, **When** the user runs `/policy:update` and no file exists at that path, **Then** the file is created and recorded; if a file already exists there, it is treated as user-owned and reported.
6. **Given** any customized or missing file, **When** the update finishes, **Then** the command exits with a non-zero status so CI can surface drift.

---

### User Story 3 - Recover safely from a broken manifest (Priority: P3)

If `.policy/manifest.json` is missing or cannot be parsed, the update command stops and explains how to recover, rather than guessing a baseline that could overwrite user content.

**Why this priority**: This is a safety guard. It matters most when something goes wrong, but it is not needed for the core flows.

**Independent Test**: Delete the manifest, or corrupt it, and run `/policy:update`. Confirm no files change and the message names the recovery step.

**Acceptance Scenarios**:

1. **Given** no manifest file exists, **When** the user runs `/policy:update`, **Then** no files change and the user is told to run `/policy:init` or restore the manifest.
2. **Given** a manifest that is not valid JSON, **When** the user runs `/policy:update`, **Then** no files change and the error identifies the manifest as the problem.

---

### Edge Cases

- A content fingerprint must be stable across operating systems: a file checked out with CRLF line endings must not look customized.
- A manifest entry whose file was deleted and whose template was also removed from the plugin is reported once, not twice.
- Running `/policy:update` twice in a row with no plugin changes produces no writes and an empty change report.
- Running `/policy:init` in a directory where `.policy/README.md` exists but no manifest does: the README is treated as user-owned and not overwritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The plugin MUST provide a `/policy:init` command that creates `.policy/rule/`, `.policy/retired/`, `.policy/README.md`, and `.policy/manifest.json` in a repository.
- **FR-002**: `/policy:init` MUST NOT modify any existing file, and MUST NOT modify an already-initialized project (one that has a manifest).
- **FR-003**: `/policy:init` MUST record, for each file it writes, a content fingerprint and the plugin version that shipped it.
- **FR-004**: Content fingerprints MUST be computed with line endings normalized to LF, so the same content produces the same fingerprint on every platform.
- **FR-005**: The plugin MUST provide a `/policy:update` command that compares each tracked file's current fingerprint against its recorded fingerprint.
- **FR-006**: `/policy:update` MUST overwrite a tracked file only when its current fingerprint matches the recorded one and the shipped template has changed.
- **FR-007**: `/policy:update` MUST leave customized files unchanged and list each in its report with a diff against the current shipped template.
- **FR-008**: `/policy:update` MUST NOT recreate a tracked file the user deleted, and MUST report it as missing.
- **FR-009**: `/policy:update` MUST NOT delete any project file, even when its shipped template no longer exists; it MUST report such files.
- **FR-010**: `/policy:update` MUST create a shipped file that is absent from the manifest only if no file exists at that path; otherwise it MUST treat the existing file as user-owned and report it.
- **FR-011**: `/policy:update` MUST stop without changing any file when the manifest is missing or cannot be parsed, and MUST name the recovery step.
- **FR-012**: `/policy:update` MUST exit with a non-zero status when any file is customized or missing, and zero otherwise.
- **FR-013**: The manifest MUST record its own format version, so future changes to its structure can be recognized.

### Key Entities

- **Manifest**: The project's record of what the plugin wrote. Holds the manifest format version, the plugin version at last write, and one entry per tracked file.
- **Tracked file entry**: One file path in the manifest, with the plugin version that shipped it and the content fingerprint at the time it was written.
- **Shipped template**: A file bundled with the plugin that init and update write into projects. Its current content is the target for update.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can go from an empty repository to adding their first rule in under 2 minutes using only `/policy:init` and `/policy:add`.
- **SC-002**: Across every row of the update behavior table (User Story 2), no file is overwritten unless its content matches the recorded fingerprint, verified by automated tests.
- **SC-003**: 100% of customized files in a test project are reported by `/policy:update` and left byte-for-byte unchanged.
- **SC-004**: A project checked out with different line endings on another operating system reports no false customizations.
- **SC-005**: A developer can recover from a missing or corrupt manifest by following the update command's message, without reading the plugin source.

## Assumptions

- The plugin is installed through the marketplace and is not copied into projects, so the manifest tracks only files that `/policy:init` writes.
- The minimal skeleton ships one tracked file, `.policy/README.md`. Additional tracked files are added in later versions as the skeleton grows.
- Rule files under `.policy/rule/` and `.policy/retired/` are user content and are never tracked.
- Derived documents (`CONTRIBUTING.md`, the agent-operational doc) are not created by init in this version and are not tracked.
- Projects initialized before this feature existed have no manifest; they get one only by an explicit future migration, not by `/policy:update`.
- Starter rules from the `common-policy-topics` roadmap item are out of scope.
- Human vs. agent scoping of rules is out of scope, as stated in the README.
