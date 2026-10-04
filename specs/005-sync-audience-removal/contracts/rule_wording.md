# Contract: Rule `wording` and `synced_wording` frontmatter

## Example rule file

```markdown
---
title: "Secrets stay out of logs"
tags: [security]
created: 2026-10-04T00:00:00Z
modified: 2026-10-04T00:00:00Z
audience: [human, agent]
verification:
  method: ci-checked
  via: "scripts/check-logs.sh"
wording:
  human: "Secrets MUST NOT appear in CI logs."
  agent: "Never print secrets to CI output."
synced_hash: 05f0…
synced_wording:
  human: "Secrets MUST NOT appear in CI logs."
  agent: "Never print secrets to CI output."
---

**001**: Secrets MUST NOT appear in CI logs.
```

## `add_rule.py`

- `--wording AUDIENCE=TEXT`, repeatable. Required once for each audience in `--audience`.
- Each `TEXT` is normalized before storing: runs of `[ \t\r\n]` collapse to one space, and the ends are trimmed. A `TEXT` that is empty after normalization is an error (exit `2`). No sentence-count or modal check is applied.
- A `--wording` for an audience not in `--audience` is an error (exit `2`).
- Writes `wording` in frontmatter. Does not write `synced_wording` or `synced_hash`.

## `edit_rule.py`

- `--set wording.human=TEXT` and `--set wording.agent=TEXT` are editable.
- Setting `wording.<audience>` for an audience not in `audience` is an error (exit `2`).
- Setting `audience` to remove an audience drops that audience's `wording` key. This is rejected (exit `2`, nothing written) when the audience has a `synced_wording` entry that differs from its current `wording`, because an unrecorded wording edit would otherwise be discarded. The message names the audience and says to run sync first or revert the wording. An audience with no `synced_wording` entry, or with equal values, is dropped without error.
- A run whose `--set` list includes `statement` requires `--reviewed-wording`. Without it the run exits `2` and writes nothing. `--preview` does not need the flag, and it prints `review wording.<audience>` for each audience.
- Editing `wording` or `audience` changes the content hash, so the rule reads `changed` until `record_sync` runs. `synced_wording` is never changed by `edit`.

## `record_sync.py`

- `ID ...`: rules to record. Each must exist (exit `2` otherwise).
- `--expect ID=HASH`, repeatable: the content hash the rule had when it was proposed. Each named ID must also be recorded. If a rule's current content hash differs, the run exits `1`, names the rule, and writes nothing. This is the source re-check Constitution Principle III requires.
- `--root PATH`: directory derived-doc paths resolve against. Default `.`.
- Refuses, exit `1` with nothing written, a rule that still has an unapplied change: a `pending` addition, or a `stale_in` removal with `status: "found"` (FR-004, R14). `not_found`, `ambiguous`, and `absent` entries do not block recording.
- For each approved ID, sets `synced_wording` to the current `wording` for the rule's current audiences, verbatim.
- Removes `synced_wording` entirely when no audience remains.
- Writes only `synced_hash` and `synced_wording`. The body and other fields stay byte-identical.

## Validation (`policy_frontmatter.validate`)

- `wording` is required and must be a map.
- Its keys must equal the set of `audience` values. Missing keys are problems.
- Each value must be non-empty and a single line (no `\n` or `\r`). Normalization at write time guarantees this; the validator checks it as a backstop.
- `synced_wording`, when present, must be a map whose keys are a subset of `{human, agent}`, and whose values are non-empty single lines.
