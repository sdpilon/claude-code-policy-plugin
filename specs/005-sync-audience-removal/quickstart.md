# Quickstart: Validate Sync Removal

Run these in a scratch directory, never in a real project. Replace `$PLUGIN` with the plugin root.

## Setup

```sh
D=$(mktemp -d) && cd "$D" && mkdir -p .policy/rule .claude/rules
python3 $PLUGIN/skills/add/scripts/add_rule.py --dir "" --policy-dir .policy \
  --statement "Secrets MUST NOT appear in CI logs." --title "Secrets stay out of logs" \
  --audience human,agent --verification-method written-only \
  --wording human="Secrets MUST NOT appear in CI logs." \
  --wording agent="Never print secrets to CI output."
```

Write the derived docs the way sync would, then record so the rule starts clean:

```sh
printf 'Secrets MUST NOT appear in CI logs.\n' > CONTRIBUTING.md
printf 'Never print secrets to CI output.\n' > CLAUDE.md
python3 $PLUGIN/skills/sync/scripts/record_sync.py --dir .policy/rule 001
```

**Pass condition**: `.policy/rule/001.md` has `synced_wording` with both audiences, and `sync_status` reports `changed: false`.

## Scenario 1: audience drops `human`

```sh
python3 $PLUGIN/skills/edit/scripts/edit_rule.py --dir .policy/rule \
  --set audience=agent 001
python3 $PLUGIN/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
```

**Pass condition**: `changed: true`, `targets` is `["CLAUDE.md", ".claude/rules/001.md"]`, and `stale_in` has `CONTRIBUTING.md` with `audience: "human"`, `kind: "span"`, and `status: "found"`.

## Scenario 2: approve, remove, record

Remove the exact sentence from `CONTRIBUTING.md`, then record and run again:

```sh
python3 $PLUGIN/skills/sync/scripts/record_sync.py --dir .policy/rule 001
python3 $PLUGIN/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
```

**Pass condition**: `changed: false`, `stale_in: []`, and `synced_wording` no longer has a `human` key.

## Scenario 3: declined removal

Start from Setup, run Scenario 1's edit, and do not remove the sentence or run `record_sync`.

**Pass condition**: `changed: true` and `stale_in` still lists `CONTRIBUTING.md` as `found`.

## Scenario 4: hand-edited text

Start from Setup, run Scenario 1's edit, then reword the sentence in `CONTRIBUTING.md`.

**Pass condition**: `stale_in` lists `CONTRIBUTING.md` with `status: "not_found"`, and no removal is proposed for it.

## Scenario 5: absent doc

Start from Setup, run Scenario 1's edit, then delete `CONTRIBUTING.md`.

**Pass condition**: `status: "absent"` for `CONTRIBUTING.md`, and no error.

## Scenario 6: missing wording

From Setup, delete the `agent` line under `wording:` in `.policy/rule/001.md` by hand, then run sync.

**Pass condition**: `missing_wording` lists `agent`.

## Cleanup

```sh
cd / && rm -rf "$D"
```

## Automated coverage

`python3 -m unittest tests.test_sync_status tests.test_record_sync tests.test_add_rule tests.test_edit_rule tests.test_policy_frontmatter` covers these scenarios with the same fixtures.
