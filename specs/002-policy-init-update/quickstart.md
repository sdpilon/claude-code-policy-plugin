# Quickstart: Policy Init and Safe Update

Validation scenarios that prove the feature works end to end. Run each in a scratch directory,
never in a real project (per the test-tooling rule in the user's CLAUDE.md).

## Setup

```sh
export SCRATCH="$(mktemp -d)"
cd "$SCRATCH" && git init -q
PLUGIN="<path to this repo>"   # the directory containing skills/ and scripts/
```

## S1: Fresh init, then add a rule (User Story 1)

1. Run `/policy:init` in `$SCRATCH`.
2. Expect `.policy/rule/`, `.policy/retired/`, `.policy/README.md`, `.policy/manifest.json` to exist, and exit `0`.
3. Expect `manifest.json` `format_version` `1`, `plugin_version` `0.2.0`, and a `.policy/README.md` entry whose `sha256` matches the file.
4. Run `/policy:add` for one rule. Expect ID `001` under `.policy/rule/`.

## S2: Init is idempotent (FR-002)

1. Run `/policy:init` again.
2. Expect `already initialized`, exit `0`, and no byte changes anywhere under `.policy/`.

## S3: User-owned README (edge case)

1. Remove `.policy/manifest.json`. Edit `.policy/README.md`.
2. Run `/policy:init`. Expect `user-owned: .policy/README.md (not tracked)`, and the README unchanged.

## S4: Clean update (no drift)

1. From a fresh init, run `/policy:update`. Expect `current` for the README, no writes, exit `0`.
2. Run it again. Expect the same result, no writes (edge case).

## S5: Stale file is auto-applied (User Story 2, row 1)

1. Simulate a newer template: set `plugin_version` in the manifest to `0.1.0` and change the recorded `sha256` of `.policy/README.md` to match the file's current content, so the file is `stale` against the shipped template.
2. Run `/policy:update`. Expect `updated: .policy/README.md`, the file now equal to the shipped template, the manifest entry at the new `shipped_version`, exit `0`.

## S6: Customized file is reported, not changed (User Story 2, row 2)

1. Run `/policy:init`. Append a line to `.policy/README.md`.
2. Run `/policy:update`. Expect `customized: .policy/README.md`, a unified diff, the file byte-identical to before, exit `1`.

## S7: Deleted tracked file is not recreated (User Story 2, row 3)

1. Run `/policy:init`. Delete `.policy/README.md`.
2. Run `/policy:update`. Expect `missing: .policy/README.md`, the file still absent, exit `1`.

## S8: Entry whose template was removed is kept (User Story 2, row 4)

1. Run `/policy:init`. Add a manifest entry for `.policy/old-file.md` with a valid `sha256` and create that file.
2. Run `/policy:update`. Expect `no-longer-shipped: .policy/old-file.md`, the file kept, exit `0`.

## S9: New shipped file, absent vs. present (User Story 2, row 5)

1. Simulate a shipped path not yet in the manifest, absent on disk: expect it created and recorded.
2. Simulate one present on disk with no entry: expect `user-owned` and the file unchanged.

## S10: Fail closed on manifest problems (User Story 3)

1. Delete the manifest. Run `/policy:update`. Expect exit `2`, a message naming `/policy:init`, no file changes.
2. Write `{ not json` to the manifest. Run `/policy:update`. Expect exit `2`, a message naming the manifest, no file changes.
3. Write `{"format_version": 99, "plugin_version": "9.9.9", "files": {}}`. Expect exit `2` with a "newer plugin" message, no file changes.

## S11: Line endings (SC-004)

1. Run `/policy:init`. Convert `.policy/README.md` to CRLF line endings, content otherwise unchanged.
2. Run `/policy:update`. Expect `current`, not `customized`, exit `0`.

## Automated coverage

`python3 -m unittest discover -s tests` must pass. The unit suite covers the classification table
(S4–S9) and the fail-closed cases (S10). S11 is covered by a fingerprint test that compares an LF
and a CRLF copy.
