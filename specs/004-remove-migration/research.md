# Research: Remove the Migration Feature

No open technical unknowns. This feature removes code and descriptions, so the research question
is only how to remove it safely.

## Removal approach

**Decision**: Delete the migration files with `git rm` (or `git rm -r` for the skill directory),
and edit the three description/documentation files in place.

**Rationale**: Tracked deletions show up in the diff as one reviewable change (FR-008). Deleting
with plain `rm` would leave the deletions unstaged and easy to miss in review.

**Alternatives considered**:

- Leave the skill in place and mark it deprecated. Rejected: the spec says remove entirely, and
  a deprecated command still ships to installers.
- Move the files to an `archive/` directory. Rejected: keeps dead code in the tree, and history
  already preserves it.

## Stale-reference search

**Decision**: After deletion, search the whole tree for `migrate`, `migrating`, and `skills/migrate`,
excluding `specs/001-*` through `specs/003-*`.

**Rationale**: The earlier grep found the README line, the plugin and marketplace descriptions,
and the skill and test files. A repeat search after deletion confirms nothing else referenced
them (SC-001). Descriptions must also be read by eye, since a generic word like "migrating" can
be missed by search wording.

**Alternatives considered**: Rely only on the CI test run. Rejected: CI would not catch a
description or README line that still advertises the removed command.

## Local artifacts

**Decision**: Remove `skills/migrate/scripts/__pycache__/` with the rest of the skill directory.

**Rationale**: The bytecode cache is a local build artifact of the deleted script and has no
reason to remain. Git ignores it, so it does not need to be staged.
