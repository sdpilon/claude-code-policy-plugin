# Contract: `skills/add/scripts/add_rule.py`

Backs `/policy:add`'s file-writing step (User Story 1). The skill still owns the
conversation — wording the statement, judging MUST vs. SHOULD, asking where
(organizationally) to put it — this script only performs the mechanical, deterministic
part: allocate an ID and write the file.

## CLI

```
python3 skills/add/scripts/add_rule.py \
  --statement "<subject> MUST <requirement>." \
  --title "<short human name>" \
  --audience human[,agent] \
  --verification-method ci-blocking|ci-checked|human-verified|written-only \
  [--verification-via "<note>"] \
  [--tags tag1,tag2] \
  [--dir .policy/rule/<optional-subdir>] \
  [--rationale "<paragraph>"]
```

## Behavior

1. Resolves the target directory (`--dir`, default `.policy/rule`), creating it if
   absent.
2. Allocates the next ID via `scripts/policy_ids.py`, reserving it by creating
   `<dir>/<format_id(id)>.md` (the reservation *is* the file write — there is no
   separate claim-then-write step for this script to race against itself).
3. Renders frontmatter via `scripts/policy_frontmatter.py.render`, sets `created` and
   `modified` to the current UTC timestamp, and writes the bold
   `**<format_id(id)>**: <statement>` line plus the rationale paragraph.
4. Prints the result as one JSON object on stdout; writes nothing else to stdout.

## Output

```json
{"id": 47, "path": ".policy/rule/047.md"}
```

`id` is a plain integer; the filename and bold-line token are zero-padded via
`format_id` (see `policy_ids.md`) — `id` itself is never padded in JSON output.

## Errors

- Missing or empty `--audience`, or a value outside `{human, agent}`: exits `2`,
  prints a one-line error to stderr, writes no file.
- `--verification-method` outside the four enumerated values: exits `2`, writes no
  file.
- An unresolvable ID allocation (see `policy_ids.md`'s bounded-retry note): exits `1`.
