# Research: Policy Init and Safe Update

Each decision below resolves a technical choice in `plan.md`. No NEEDS CLARIFICATION items remain.

## 1. Content fingerprint algorithm

**Decision**: SHA-256, hex-encoded, computed with `hashlib`.

**Rationale**: Standard library, collision-resistant for this purpose, and stable across Python versions.

**Alternatives considered**:

- MD5: available, but a known-weak digest; there's no reason to use it when SHA-256 costs nothing here.
- Git blob hash: would tie the mechanism to git and to the repo's object format. Projects may not use git, and the spec doesn't require it.

## 2. Line-ending normalization

**Decision**: Read the file as bytes, decode as UTF-8, replace every `\r\n` with `\n`, re-encode as UTF-8, then hash. Trailing whitespace and final newlines are not changed.

**Rationale**: FR-004 and SC-004 require that a CRLF checkout of an unmodified file is not reported as customized. Normalizing only line endings is the minimum change that satisfies that. Stripping trailing whitespace would hide real edits.

**Alternatives considered**:

- Hash raw bytes: produces false customizations on Windows checkouts with `core.autocrlf`.
- Normalize all whitespace: hides genuine edits and is harder to reason about.

**Edge case**: A file that isn't valid UTF-8 is hashed over its raw bytes and reported as customized. The tracked template is always UTF-8, so such a file was necessarily changed by someone.

## 3. Where the plugin version comes from

**Decision**: Read `version` from `.claude-plugin/plugin.json` at runtime. The manifest's `plugin_version` is written from that value.

**Rationale**: One source of truth. A version bump in `plugin.json` is then the only change needed to record the shipped version.

**Alternatives considered**: A separate `VERSION` file or a constant in the Python module. Both duplicate a value that `plugin.json` already holds.

## 4. Diff format for customized files

**Decision**: `difflib.unified_diff` between the project's current file and the current shipped template, printed in the update report.

**Rationale**: Stdlib, deterministic, and the format users already read in `git diff`. FR-007 requires a diff for customized files.

## 5. Exit codes

**Decision**:

- `0`: clean run (no drift), or init on an already-initialized project.
- `1`: drift: at least one file is customized or missing (FR-012).
- `2`: fail closed: manifest missing or unparseable, or unsupported `format_version` (FR-011). Matches the `fail()` convention in `skills/add/scripts/add_rule.py`.

**Rationale**: CI can branch on `1` (surface drift) versus `2` (fix the setup). Exit `0` for no-longer-shipped files matches the spec, which only lists customized and missing as drift; those files are reported but don't fail the run.

## 6. Atomic writes

**Decision**: Write to a temporary file in the same directory, then `os.replace` onto the target.

**Rationale**: An interrupted update must never leave a half-written tracked file or manifest.

## 7. Module placement

**Decision**: Shared logic in root `scripts/policy_manifest.py`. Each skill script imports it through the `sys.path` bootstrap used by `skills/add/scripts/add_rule.py`.

**Rationale**: Matches the existing `policy_ids.py` and `policy_frontmatter.py` pattern. Keeps init and update from diverging on fingerprinting.

## 8. Test runner

**Decision**: `unittest`, run via `python3 -m unittest discover -s tests`.

**Rationale**: pytest isn't installed, and the existing suite is already `unittest`. Adding a dependency needs an install approval, which this feature doesn't need.
