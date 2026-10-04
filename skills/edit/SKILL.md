---
name: edit
description: Change the wording, title, tags, audience, verification method, or rationale of an existing policy rule under .policy/rule/, or the same change across several rules. Use when the person asks to reword, rephrase, retitle, re-tag, change the audience of, or change the verification of a rule that already exists ("reword rule 004", "make rule 012 agent-only", "change the check for rule 7 to ci-blocking"). Not for writing a new rule (use add), removing a rule (use retire), or propagating rules into docs (use sync).
---

# Editing a rule

A rule is one file, `.policy/rule/<id>.md`. This skill changes fields on existing rules through
`scripts/edit_rule.py`. It never edits the file by hand, so `modified` is always set and the
statement check always runs.

Run from the repository root. `<plugin>` is the plugin's root directory, the folder that contains
`skills/` and `scripts/`. The loader's base directory for this skill is `<plugin>/skills/edit`.

## Editable fields

| Field | Value |
|---|---|
| `title` | free text |
| `tags` | comma-separated |
| `audience` | `human`, `agent`, or both, comma-separated |
| `verification.method` | `ci-blocking`, `ci-checked`, `human-verified`, or `written-only` |
| `verification.via` | the intended check name |
| `statement` | one sentence with exactly one modal verb (MUST, SHOULD, MUST NOT, MAY) |
| `rationale` | free text; an empty value removes it |

`created`, `synced_hash`, and the rule ID cannot be edited. The script rejects them by name.

## Steps

1. **Identify the change.** Confirm which rule IDs and which fields. If the person's request is
   vague ("make the rule clearer"), ask what the new wording is. Don't guess the wording.
2. **Preview first.** Run:

   ```text
   python3 <plugin>/skills/edit/scripts/edit_rule.py --preview --set <field>=<value> [--set ...] <ID> [<ID> ...]
   ```

   It prints the proposed change for each rule and writes nothing. A rejected rule prints its
   reason and exits 2.
3. **Checkpoint (Constitution Principle III).** Show the person the preview: each rule ID, the old
   and new values, and any rejections. Ask whether to apply, using `AskUserQuestion` when it is
   available. Do not apply until they say yes. If a rule was rejected, fix the value and preview
   again. Don't apply the rest of the batch without saying so.
4. **Apply.** Run the same command without `--preview`. Every target is validated first. If any
   target is rejected, nothing is written and the command exits 2. Report each `changed` and
   `unchanged` line.
5. **Tell the person what comes next.** An edited rule now reads as changed in the sync status
   until its derived docs are synced. Say so, and offer to run the sync skill.

## Guardrails

- Never edit a rule file by hand, and never edit `synced_hash`.
- Never write to derived docs (`CONTRIBUTING.md`, `CLAUDE.md`, `.claude/rules/`) from this skill.
- A statement with more than one sentence or modal verb is rejected. Rewrite it as one sentence
  with one modal, then preview again.
- Don't commit unless the person asks.
