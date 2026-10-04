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
printf 'Never print secrets to CI output.\n' > .claude/rules/001.md
python3 $PLUGIN/skills/sync/scripts/record_sync.py --dir .policy/rule 001
```

**Pass condition**: `.policy/rule/001.md` has `synced_wording` with both audiences, and `sync_status` reports `changed: false`.

Every scenario below reuses `$D` and `$PLUGIN` from Setup. Run Setup first, in the same shell, before any scenario. A sandboxed shell may not keep `cd` or variables between commands; if so, put each scenario's commands in one script, or use absolute paths.

## Scenario 1: audience drops `human`

```sh
python3 $PLUGIN/skills/edit/scripts/edit_rule.py --dir .policy/rule \
  --set audience=agent 001
python3 $PLUGIN/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
```

**Pass condition**: `changed: true`, `targets` is `["CLAUDE.md", ".claude/rules/001.md"]`, and `stale_in` has `CONTRIBUTING.md` with `audience: "human"`, `kind: "span"`, `reason: "dropped"`, and `status: "found"`.

## Scenario 2: approve, remove, record

From Scenario 1 (run its edit first), empty `CONTRIBUTING.md` to remove the exact sentence, then record and run again:

```sh
printf '' > CONTRIBUTING.md
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

From Setup, remove only the `agent` line under `wording:` in `.policy/rule/001.md`. The `synced_wording:` entry also has an `agent:` line, so delete just the first match. The `wording:` entry comes first in the file, so the first match is the one to remove. Then run sync:

```sh
awk 'BEGIN{d=0} /^  agent: / && !d {d=1; next} {print}' .policy/rule/001.md > t && mv t .policy/rule/001.md
python3 $PLUGIN/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
```

**Pass condition**: `missing_wording` lists `agent`, and the row has an `error`.

## Scenario 7: reword a still-targeted audience

From Setup (both audiences still targeted), change the human wording and do not record:

```sh
python3 $PLUGIN/skills/edit/scripts/edit_rule.py --dir .policy/rule \
  --set wording.human="Secrets MUST NOT leak into CI logs." 001
python3 $PLUGIN/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
```

**Pass condition**: `changed: true`, `targets` still includes `CONTRIBUTING.md`, and `stale_in` has `CONTRIBUTING.md` with `audience: "human"`, `reason: "reworded"`, and `status: "found"`. `pending` has a `CONTRIBUTING.md` entry for the new human wording, with `path`, `audience`, and `kind` but no text. The addition is proposed from that entry.

## Scenario 8: rejected drop after an unrecorded wording edit

From Setup, run Scenario 7's edit, then drop `human` without recording:

```sh
python3 $PLUGIN/skills/edit/scripts/edit_rule.py --dir .policy/rule \
  --set audience=agent 001
```

**Pass condition**: exit `2`, the message names `human` and says to run sync or revert the wording, and `.policy/rule/001.md` is byte-identical to before the command.

## Scenario 9: agent-only file

From Setup, drop `agent` (`--set audience=human`). Setup already created `.claude/rules/001.md`, so overwrite it with the exact agent wording and a newline, the way sync would, then run sync:

```sh
printf 'Never print secrets to CI output.\n' > .claude/rules/001.md
python3 $PLUGIN/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
```

To check the hand-edited case, overwrite the file with other text, then run sync again:

```sh
printf 'Someone hand-edited this.\n' > .claude/rules/001.md
python3 $PLUGIN/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
```

**Pass condition**: `stale_in` includes `.claude/rules/001.md` with `kind: "file"`, `reason: "dropped"`, and `status: "found"` (`CLAUDE.md` may also be listed, since the agent audience was dropped). After the hand edit, that file's status is `not_found` and `pending` is empty.

## Scenario 10: statement change needs the review flag

```sh
python3 $PLUGIN/skills/edit/scripts/edit_rule.py --dir .policy/rule \
  --set statement="Secrets MUST NOT appear in build logs." 001
```

To preview the wording review, then write the statement with the flag:

```sh
python3 $PLUGIN/skills/edit/scripts/edit_rule.py --dir .policy/rule \
  --set statement="Secrets MUST NOT appear in build logs." --preview 001
python3 $PLUGIN/skills/edit/scripts/edit_rule.py --dir .policy/rule \
  --set statement="Secrets MUST NOT appear in build logs." --reviewed-wording 001
```

**Pass condition**: exit `2`, the message asks for `--reviewed-wording`, and the file is unchanged. With `--reviewed-wording` added, the statement is written: `grep -n 'build logs' .policy/rule/001.md` matches the body line `**001**:`, because the statement lives in the body, not in a `statement` key. `--preview` without the flag prints a `review wording.<audience>` line for each audience.

## Scenario 11: partial approval keeps the rule changed

From Setup, reword the human wording as in Scenario 7. Approve only the addition: write the new human wording into `CONTRIBUTING.md` and leave the old sentence in place, which declines that removal. Run sync again without recording:

```sh
printf 'Secrets MUST NOT appear in CI logs.\nSecrets MUST NOT leak into CI logs.\n' > CONTRIBUTING.md
python3 $PLUGIN/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
```

**Pass condition**: `changed: true`, and `pending` is empty because the added wording is already in `CONTRIBUTING.md`, so no addition is left to apply. `stale_in` still lists `CONTRIBUTING.md` with `status: "found"` for the old sentence. `record_sync 001` refuses it with exit `1` and writes nothing until every change is applied (FR-004, R14).

To check that the refused record writes nothing, save a copy of the rule file, run the record, and compare the bytes:

```sh
cp .policy/rule/001.md before.md
python3 $PLUGIN/skills/sync/scripts/record_sync.py --dir .policy/rule 001; echo "exit $?"
cmp .policy/rule/001.md before.md && echo unchanged
```

The exit code is `1`, and `cmp` reports `unchanged`.

## Scenario 12: hand-edited agent-only file is held

From Setup, replace `.claude/rules/001.md` with hand-written text, then run sync:

```sh
printf 'Someone rewrote this by hand.\n' > .claude/rules/001.md
python3 $PLUGIN/skills/sync/scripts/sync_status.py --dir .policy/rule --root .
```

**Pass condition**: `held` lists `.claude/rules/001.md` with `audience: "agent"` and `kind: "file"`, and it is not in `pending`. Afterwards the file still holds the hand-written text, because sync never overwrites a held file.

## Cleanup

```sh
cd / && rm -rf "$D"
```

## Automated coverage

`python3 -m unittest tests.test_sync_status tests.test_record_sync tests.test_add_rule tests.test_edit_rule tests.test_policy_frontmatter` covers Scenarios 1 to 12 with the same fixtures.
