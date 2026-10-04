# Quickstart: Validate the Migration Removal

Run these from the repository root after the change is applied. Each step maps to a
requirement or success criterion in `spec.md`.

## Prerequisites

- Python 3.14 and `uv` installed
- The `004-remove-migration` branch checked out, with the change applied

## 1. Confirm the files are gone (FR-001, FR-002)

```sh
test ! -e skills/migrate && test ! -e tests/test_migrate_rules.py && echo "removed"
```

Expected: `removed`

## 2. Confirm no live file references the feature (FR-003, FR-004, FR-006, SC-001)

```sh
git grep -n -i -E 'policy:migrate|skills/migrate|migrate_rules|migrating' -- ':!specs/001-*' ':!specs/002-*' ':!specs/003-*'
```

Expected: no output. A match in a live file means a reference was missed.

## 3. Confirm the historical specs are untouched (FR-007, SC-004)

```sh
git diff --stat main -- specs/001-rule-per-file-restructure specs/002-policy-init-update specs/003-policy-plugin-gaps
```

Expected: no output (no changed files).

## 4. Confirm the plugin metadata still parses and keeps its version (FR-004, Q2)

```sh
python3 -c "import json; [json.load(open(f)) for f in ['.claude-plugin/plugin.json', '.claude-plugin/marketplace.json']]; print('valid')"
git diff main -- .claude-plugin/plugin.json | grep '"version"' || echo "version unchanged"
```

Expected: `valid`, then `version unchanged`.

## 5. Run the unit tests (FR-005, SC-002)

```sh
uv run python -m unittest discover -s tests
```

Expected: all remaining tests pass, and no test named `test_migrate_rules` is collected.

## 6. Run the CI lint and format checks (FR-005)

```sh
uv lock --check
uv sync --locked
uv run ruff check .
uv run ruff format --check .
git ls-files -z '*.md' ':!.specify/**' ':!.claude/**' ':!.claude-plugin/**' | xargs -0 uv run pymarkdown scan
git ls-files -z '*.sh' ':!.specify/**' ':!.claude/**' ':!.claude-plugin/**' | xargs -0 uv run shellcheck
git ls-files -z '*.sh' ':!.specify/**' ':!.claude/**' ':!.claude-plugin/**' | xargs -0 uv run shfmt -i 2 -d
```

Expected: every command exits 0. The README edit must keep the markdown valid, so the
`pymarkdown scan` step is the one most likely to catch a broken list after the bullet is removed.

## Done when

All six steps pass, and the diff is limited to the files listed in `plan.md` under Source Code.
