# Contract: `skills/retire/scripts/retire_rule.py`

Backs `/policy:retire` (User Story 5, FR-016). This is the only supported way to remove a
rule. It is the operation that writes the tombstone FR-004 relies on.

## CLI

```text
python3 skills/retire/scripts/retire_rule.py \
  --id 66 \
  --reason "<why it was retired>" \
  [--superseded-by 71] \
  [--rule-dir .policy/rule] \
  [--retired-dir .policy/retired]
```

## Behavior

1. Finds the rule file for `--id` anywhere under `--rule-dir` (any organizational
   subdirectory). It matches by parsed ID, so zero-padding is irrelevant.
2. Refuses if no rule file exists for that ID, or if `<retired-dir>/<format_id(id)>.md`
   already exists.
3. Writes the tombstone at `<retired-dir>/<format_id(id)>.md`, with frontmatter fields
   `id`, `title` (copied from the rule), `retired` (today's date, ISO 8601), `reason`,
   and `superseded_by` if given. No body. The tombstone is written before the rule file
   is removed, so an interruption leaves a duplicate rather than a gap.
4. Removes the rule file.
5. Prints one JSON object on stdout.

## Output

```json
{"id": 66, "tombstone": ".policy/retired/066.md", "removed": ".policy/rule/ci/066.md"}
```

## Errors

- `--reason` missing or empty: exit `2`, no file written.
- No rule file for `--id`: exit `1`, no file written.
- Tombstone already exists for `--id`: exit `1`, no file written.
- `--superseded-by` names an ID with no rule or tombstone: exit `2`, no file written.
