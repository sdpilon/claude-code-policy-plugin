# Phase 0 Research: One-Rule-Per-File Restructuring

No `[NEEDS CLARIFICATION]` markers remain in the spec — everything ambiguous was
resolved with the user during brainstorming before the spec was written. The research
below covers technical decisions planning surfaced that the spec intentionally left to
this phase (format/implementation choices, not product behavior).

## 1. Frontmatter parsing without a third-party dependency

**Decision**: Hand-roll a minimal parser for the restricted subset of YAML this
feature actually needs: flat scalars, one flat list (`tags`, `audience`), and one
small nested mapping (`verification: {method, via}`). Lives in `scripts/policy_frontmatter.py`.

**Rationale**: `skills/status/scripts/policy_status.py` already runs on Python stdlib
only (`re`, `sys`, `pathlib`, `json`) — no `requirements.txt` or dependency file exists
anywhere in this repo. Adding a PyYAML dependency would mean every consuming project
needs it installed wherever these scripts run, for a document shape simple enough not
to need a general-purpose YAML parser. This keeps Constitution Principle IV's
determinism cheap rather than trading one dependency-free script for a dependent one.

**Alternatives considered**:
- *PyYAML*: full YAML support, but a new hard dependency for every consumer; rejected
  as disproportionate to the five fields actually used.
- *`tomllib`* (stdlib since Python 3.11): avoids a dependency, but changes the
  frontmatter format away from YAML, which was already decided during brainstorming;
  rejected as contradicting a settled decision.

## 2. Rule ID allocation and race handling

**Decision**: Scan `.policy/rule/**/*.md` recursively for the highest existing integer
filename (zero-padded or not — `parse_id` tolerates either), allocate `highest + 1`,
and re-check for a conflict immediately before creating the file — retrying with the
next integer if one is found. Filenames are rendered zero-padded to a minimum of
three digits (`format_id`), matching Spec Kit's own minimum-width-not-a-cap
convention for feature directories, so a plain directory listing sorts in numeric
order. No lock file, no persisted counter. Lives in `scripts/policy_ids.py`.

**Rationale**: This is the exact pattern already proven in this repo's own Spec Kit
scaffolding (`.specify/scripts/python/create_new_feature.py`'s `_get_highest_from_specs`
plus its pre-creation conflict recheck) for the structurally identical problem of
sequential feature numbering. Already resolved during brainstorming; recorded here only
to anchor the script design.

**Alternatives considered**:
- *Persisted counter file*: removes the scan, but introduces a new piece of state to
  keep correct and git-mergeable; rejected since the proven tool in this very repo
  doesn't need one.
- *Distributed lock*: solves the race fully, but massively disproportionate to a
  rare, cheaply-resolved residual risk the spec's own Assumptions already accept.

## 3. Migration capability packaging

**Decision**: A new `migrate` skill (`skills/migrate/SKILL.md` + `scripts/migrate_rules.py`),
exposed as `/policy:migrate`, rather than a bare, undiscoverable script.

**Rationale**: Every other plugin capability (`add`, `audit`, `judge`, `status`, `sync`)
is a discoverable `/policy:*` skill. A migration capability shipped as a script with no
skill wrapper would be inconsistent with that pattern and harder for a consuming repo
to find.

**Alternatives considered**:
- *Standalone script, no skill*: rejected for discoverability, per above.
- *Folding migration logic into `add`*: rejected — migration is a one-time,
  whole-tree operation with different inputs/outputs than adding a single rule, and
  mixing them would make `add`'s description less clear for its common case.

## 4. Testing approach

**Decision**: Python stdlib `unittest`, covering `scripts/policy_frontmatter.py`,
`scripts/policy_ids.py` (including the collision-retry path), the updated
`policy_status.py` (recursive scan, bare-int ID matching, reading `verification` from
frontmatter), `sync_status.py`, and `migrate_rules.py`'s shared-rationale flagging.

**Rationale**: This plugin ships zero automated tests today. The new logic has real,
silent-failure-prone correctness risk — a frontmatter parsing bug could misclassify a
rule's audience or enforcement tier without any visible symptom until someone notices
the wrong doc got updated. `unittest` adds no new dependency, matching Technical
Context's constraint.

**Alternatives considered**:
- *pytest*: nicer ergonomics, but a new dependency for a small, stdlib-sufficient test
  surface; rejected.
- *No automated tests*: matches the status quo, but the status quo has never had logic
  this easy to get subtly wrong; rejected given the restructuring's scope.

## 5. Full terminology-rename inventory

**Decision**: Rename "obligation" → "rule" in every plugin-owned file that uses it,
confirmed by inventory:

- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — plugin/marketplace
  descriptions reference the old convention (not explicitly named in the spec, found
  during planning's project-context exploration).
- `README.md`
- `skills/add/SKILL.md`, `skills/audit/SKILL.md`, `skills/status/SKILL.md`,
  `skills/sync/SKILL.md`
- `skills/status/scripts/policy_status.py` (docstring, `OBLIGATION_RE` name)
- `templates/policy-template.md` (replaced outright by `templates/rule-template.md`)

**Explicitly excluded**: `.specify/memory/constitution.md` (deferred to a separate
amendment per spec Assumptions) and `specs/001-rule-per-file-restructure/spec.md`
itself (describes the before/after; "obligation" there is historically accurate).
`skills/judge/SKILL.md` contains no occurrences already. Two Spec Kit template files
(`speckit-checklist`, `speckit-converge`) use "obligation" in unrelated generic example
text and are vendored, not ours to rename.

**Rationale**: FR-013 says every plugin-facing document and skill description must use
"rule" consistently; this is the concrete file list that requirement resolves to.
