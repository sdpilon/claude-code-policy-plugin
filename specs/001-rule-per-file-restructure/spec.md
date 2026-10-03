# Feature Specification: One-Rule-Per-File Restructuring

**Feature Branch**: `[001-rule-per-file-restructure]`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "Restructure the policy plugin's `.policy/` convention from
one-topic-per-file to one-rule-per-file, renaming the term 'obligation' to 'rule'
throughout the plugin. Each rule gets its own file, identified by a single globally
unique integer, under `.policy/rule/<id>.md`; organizational subdirectories are
optional and carry no identity meaning. Each rule file gets frontmatter (title, tags,
created, modified, a required audience of human/agent/both, a verification method,
and a synced-content hash). `/policy:add`, `/policy:sync`, `/policy:status`, and
`/policy:audit` are updated for the new layout; a migration capability converts an
existing repo's topic files into the new layout. Plugin init and a hash-manifest
safe-update mechanism are explicitly out of scope (tracked in ROADMAP.yaml), as is
amending the project constitution (a separate follow-up pass)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add a rule without picking a topic file (Priority: P1)

A policy author runs `/policy:add` to record a new rule. Today they must first decide
which existing topic file it belongs in — often a toss-up between two or three
equally-plausible topics — and that file then accumulates unrelated rules over time.
With this feature, adding a rule never requires that decision: it gets its own file
and a permanent, unique ID.

**Why this priority**: This is the core pain driving the whole restructuring — the
arbitrary topic decision, noisy shared-file diffs, and disruption when a rule's
natural category changes later. Nothing else in this feature matters if this doesn't
work.

**Independent Test**: Run `/policy:add` twice for two unrelated rules. Confirm each
produces its own new file under `.policy/rule/` with a different numeric ID, and that
neither addition modifies a file the other created.

**Acceptance Scenarios**:

1. **Given** an empty `.policy/rule/` tree, **When** a rule is added, **Then** a new
   file is created whose name is a zero-padded integer ID (minimum three digits, e.g.
   `001`) and whose content includes that same ID in a bold statement line.
2. **Given** a `.policy/rule/` tree with existing rules, **When** another rule is
   added, **Then** the new rule's ID is higher than every existing ID and no existing
   file is modified.
3. **Given** a rule's file is later moved into an organizational subdirectory under
   `.policy/rule/` for browsing purposes, **When** any skill subsequently looks up
   that rule by ID, **Then** it is found and its ID is unchanged.

---

### User Story 2 - Sync a rule to the right derived document, automatically (Priority: P2)

A policy author runs `/policy:sync`. Today, deciding whether a given rule belongs in
the human-facing doc, the agent-operational doc, or both is an inferred judgment call
made fresh each time — a recurring source of confusion and drift. With this feature,
every rule states its intended audience, and `/policy:sync` uses that statement
directly instead of inferring it.

**Why this priority**: This closes a standing, recurring problem independently of the
file-layout change in User Story 1, and depends only on the new frontmatter existing,
not on migration being complete.

**Independent Test**: Create one rule with `audience: [human]` and one with
`audience: [agent]`. Run `/policy:sync` and confirm the human-only rule appears only
in the human-facing derived document and the agent-only rule appears only in the
agent-operational one.

**Acceptance Scenarios**:

1. **Given** a rule with `audience: [human]`, **When** `/policy:sync` runs, **Then**
   it is proposed for the human-facing document only.
2. **Given** a rule with `audience: [human, agent]`, **When** `/policy:sync` runs,
   **Then** it is proposed for both derived documents.
3. **Given** a rule whose content has not changed since its last successful sync,
   **When** `/policy:sync` runs again, **Then** that rule is not re-evaluated for
   propagation.

---

### User Story 3 - See what a rule is without opening a numbered file (Priority: P3)

A policy author or reviewer runs `/policy:status`. A bare numeric filename (`047.md`)
tells them nothing on its own. With this feature, each rule carries a short
human-readable title, and status output shows it next to the ID.

**Why this priority**: Directly offsets the one real readability cost of switching to
numeric-only filenames; valuable but not blocking for the restructuring to function.

**Independent Test**: Run `/policy:status` against a tree of numbered rule files, each
with a `title` in frontmatter, and confirm the output lists each rule's ID and title
together, not the ID alone.

**Acceptance Scenarios**:

1. **Given** a rule file with `title: No secrets in CI logs`, **When**
   `/policy:status` runs, **Then** that title appears next to the rule's ID in the
   output.
2. **Given** a rule file whose enforcement is declared via a `verification`
   frontmatter field, **When** `/policy:status` or `/policy:audit` runs, **Then** the
   reported enforcement tier matches that field, not an inline comment.

---

### User Story 4 - Migrate an existing repo's rules to the new layout (Priority: P2)

A maintainer of a repo that already adopted the old topic-file convention (e.g.
riposte) needs to move its existing rules into the new one-rule-per-file layout
without losing or silently renumbering anything.

**Why this priority**: Without this, every existing adopter is stuck on the old
convention and the other three stories only ever apply to brand-new repos. Ranked P2
because the mechanical split can run once, independent of day-to-day use of the other
stories.

**Independent Test**: Run the migration capability against a sample repo with two
topic files containing a total of five rules, including one pair that previously
shared a single rationale paragraph. Confirm five new rule files result, each with a
unique ID, and that the shared-rationale pair is flagged for a human decision rather
than silently duplicated or discarded.

**Acceptance Scenarios**:

1. **Given** an existing `.policy/<topic>.md` file with three bolded obligations,
   **When** the migration capability runs, **Then** three new files appear under
   `.policy/rule/`, each with a freshly allocated unique ID and none of the original
   statement text lost.
2. **Given** two obligations that previously shared one rationale paragraph under a
   topic's section heading, **When** migration runs, **Then** both resulting rule
   files are flagged for manual rationale review rather than each silently receiving
   an unreviewed copy of the full shared text.

---

### User Story 5 - Retire a rule without losing its ID (Priority: P2)

A policy author retires a rule that no longer applies. Today there's no defined way to
do this, and a deleted rule's ID could be reissued to a later rule. With this feature,
retiring a rule removes it from the live set and leaves a tombstone, so its ID is never
reissued and the retirement is recorded with a reason.

**Why this priority**: Without it, FR-004 (no ID reuse) can't hold. It depends only on
the allocation and frontmatter foundations, not on the other stories.

**Independent Test**: Retire one rule with a reason. Confirm its file is gone from
`.policy/rule/`, a tombstone exists at `.policy/retired/<id>.md`, and the next
`/policy:add` gets an ID above the retired one.

**Acceptance Scenarios**:

1. **Given** rule 066 exists, **When** it is retired with a reason, **Then** its file is
   removed and a tombstone recording that reason exists at `.policy/retired/066.md`.
2. **Given** rule 066 was retired and was the highest ID in use, **When** a new rule is
   added, **Then** its ID is 067 or higher, never 066.
3. **Given** a tombstone already exists for an ID, **When** retirement is attempted for
   that ID again, **Then** the operation refuses and changes nothing.

---

### Edge Cases

- What happens when two `/policy:add` runs in the same working copy race for the same
  next ID? The second allocation must detect the conflict immediately before writing
  and retry with the next integer, never silently overwriting the first rule's file.
- What happens when a rule is authored without a required `audience` value? The
  authoring skill must not produce a file lacking it; a rule already on disk without
  it is reported as a defect by `/policy:status`, not silently treated as any
  particular audience.
- What happens when a rule's file is moved between organizational subdirectories, or
  out of all of them into the flat root? Its ID and content are unaffected, and every
  skill that looks rules up by ID continues to find it.
- What happens to a repo's existing `.policy/<topic>.md` files if migration hasn't
  been run yet? They are out of scope for the updated skills, which operate only on
  `.policy/rule/`; migration is a precondition for using the updated skills, not
  something they do automatically on first encounter with old-format files.
- What happens when a rule file is deleted with plain git rather than the retirement
  operation? No tombstone exists, so its ID would otherwise be reissued. Status reports
  the resulting gap as a defect (FR-017) until a tombstone is written for it.
- What happens when two rules are added independently on separate, not-yet-merged
  branches and both happen to compute the same next ID before either branch sees the
  other's commit? This is a known, accepted residual risk (the same one Spec Kit's own
  sequential numbering accepts) — resolving it is a small, visible merge conflict on
  two single-rule files, not silent data loss.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store each rule in its own file located under
  `.policy/rule/`, optionally nested inside organizational subdirectories.
- **FR-002**: System MUST identify each rule by a single integer ID that is unique
  across the entire `.policy/rule/` tree, independent of which subdirectory (if any)
  the rule's file lives in.
- **FR-003**: System MUST allocate a new rule's ID as one greater than the highest ID
  currently present in the tree, and MUST re-check for a conflict immediately before
  creating the new file, retrying with the next integer if a conflict is found.
- **FR-004**: System MUST NOT reuse a rule ID once assigned, even after that rule is
  retired. Retiring a rule MUST leave a frontmatter-only tombstone at
  `.policy/retired/<id>.md`, and tombstones MUST count toward ID allocation.
- **FR-005**: Moving a rule's file between organizational subdirectories, or into or
  out of the flat root of `.policy/rule/`, MUST NOT change that rule's ID.
- **FR-006**: Each rule file MUST declare, in YAML frontmatter: a human-readable
  `title`; zero or more decorative `tags`; `created` and `modified` timestamps; a
  required `audience` listing one or both of `human`/`agent`; and a `verification`
  method classifying how the rule is actually enforced.
- **FR-007**: `/policy:sync` MUST propagate a given rule only into the derived
  document(s) matching that rule's declared `audience`.
- **FR-008**: `/policy:sync` MUST be able to skip re-evaluating a rule for
  propagation when that rule's content is unchanged since its last successful sync.
- **FR-009**: `/policy:status` MUST display each rule's human-readable title
  alongside its numeric ID.
- **FR-010**: `/policy:status` and `/policy:audit` MUST determine a rule's
  enforcement classification from its `verification` frontmatter field rather than
  an inline comment convention.
- **FR-011**: System MUST provide a one-time migration capability that converts an
  existing repo's topic-grouped rule files into the one-rule-per-file layout,
  assigning each migrated rule a freshly allocated, unique ID.
- **FR-012**: The migration capability MUST flag, rather than silently resolve, any
  rule whose rationale was previously shared with other rules in the same topic file.
- **FR-013**: Every plugin-facing document and skill description MUST use the term
  "rule" consistently in place of the prior term "obligation".
- **FR-014**: A fully flat `.policy/rule/` layout, with no organizational
  subdirectories at all, MUST remain a valid and complete setup.
- **FR-016**: System MUST provide a retirement operation that removes a rule's file from
  `.policy/rule/` and writes its tombstone in one step, refusing to proceed if the rule
  does not exist or a tombstone for that ID already exists.
- **FR-017**: `/policy:status` MUST report any gap in the ID sequence (an integer below
  the highest ID in use with neither a rule file nor a tombstone) as a defect, so a rule
  deleted outside the retirement operation is surfaced rather than silently allowing
  its ID to be reissued.
- **FR-015**: A rule's filename and the bold statement line identifying it within its
  own file MUST use only a zero-padded decimal integer ID — minimum three digits
  (e.g. `047`), growing to additional digits once the value exceeds what three digits
  hold — never an alphabetic category prefix (e.g. `**047**:`, not `**SEC-7**:` or
  `**P047**:`).

### Key Entities

- **Rule**: a single committed, enforceable statement (one sentence, one modal verb —
  MUST/SHOULD/MUST NOT/MAY). Identified by a permanent unique numeric ID. Carries a
  human-readable title, decorative tags, creation/modification timestamps, a required
  audience (human, agent, or both), a verification/enforcement classification, its own
  rationale, and optional references to related rules.
- **Tombstone**: the frontmatter-only record left when a rule is retired, at
  `.policy/retired/<id>.md`. Records the ID, title, retirement date, and reason, and
  counts toward ID allocation so the ID is never reissued (FR-004, FR-016).
- **Derived Document**: a human-facing or agent-operational document whose content is
  kept in sync with the set of rules whose declared audience includes that document's
  audience.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Adding a new rule never requires choosing an existing file to place it
  in — every newly added rule results in a new file, 100% of the time.
- **SC-002**: When two rules are added one after another within the same working
  copy, the second allocation never collides with the first, with no manual
  renumbering step required.
- **SC-003**: Every rule's audience (human, agent, or both) can be determined by
  reading that one rule's own file — no cross-referencing derived documents required.
- **SC-004**: Every rule shown in status or audit output is identifiable by a human-
  readable title, not only a numeric filename.
- **SC-005**: Migrating an existing repo's rules preserves 100% of the original
  obligation statements — none are lost or merged into another rule's text.
- **SC-006**: After migration, a human reviewer only needs to manually revisit the
  rationale text for rules that previously shared a rationale with another rule —
  not every migrated rule.

## Assumptions

- Consuming repos adopt this layout by running the provided migration capability
  first; the updated skills operate only on `.policy/rule/` and are not required to
  continue understanding the old `<PREFIX>-N` topic-file format.
- A rare cross-branch ID collision (two people independently adding rules before
  either branch sees the other's commit) is an accepted residual risk, consistent
  with how Spec Kit's own sequential feature numbering accepts the same race —
  resolving it is a small, visible conflict, not silent data loss.
- This plugin repository's own `README.md` is updated as part of this feature, since
  it documents the plugin's own assumed convention. This repository's
  `.specify/memory/constitution.md` is deliberately **not** amended as part of this
  feature; that is a separate, later pass (a MAJOR constitution version bump via
  `/speckit-constitution`) once this feature has shipped.
- A `/policy:init` bootstrap skill and a hash-manifest safe-update mechanism for the
  plugin's own shipped files are out of scope for this feature and remain tracked as
  a deferred phase in this repository's `ROADMAP.yaml`.
