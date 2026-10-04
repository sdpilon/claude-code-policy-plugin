# Contract: `scripts/policy_frontmatter.py`

Dependency-free read/write for the restricted YAML subset used in rule frontmatter:
flat scalars, one flat list, one one-level-deep mapping. Not a general YAML parser —
rejects anything outside that subset rather than guessing.

## Library API

- `parse(text: str) -> dict` — splits the leading `---`-delimited block from the rest
  of the file and parses it. Raises `FrontmatterError` (with a line number) on anything
  outside the supported subset.
  - **Return type**: a `dict` with `str` keys. Each value is a `str` (scalar), a `list` of
    `str` (inline `[a, b]` or block list), or a `dict` of `str` to `str` (the one nested level,
    for `verification`).
  - **Empty values**: an empty scalar (`via:` with nothing after it) is `""`. An empty inline
    list (`tags: []`) is `[]`.
  - **No frontmatter**: a text with no leading `---` block raises `FrontmatterError`
    (`no frontmatter block`), with no line number.
  - **Block lists**: the `- item` lines must sit at column zero under their key. An indented
    item indented by two spaces raises `FrontmatterError`, even though the block-list form is otherwise
    supported. Write block lists unindented, or use the inline form.
- `validate(fields: dict) -> list[str]` — returns a list of human-readable problems
  (empty list means valid) against the Rule schema in `data-model.md`: missing
  `audience`, an `audience` value outside `{human, agent}`, a `verification.method`
  outside the four enumerated values, etc. Does not raise — callers decide what to do
  with a non-empty problem list.
- `render(fields: dict) -> str` — serializes `fields` back into the same restricted
  subset, preserving key order (`title, tags, created, modified, audience, verification,
  synced_hash`) so re-saving a file doesn't produce a noisy diff.

## CLI (debugging / ad hoc use)

```text
python3 scripts/policy_frontmatter.py read <rule-file>
python3 scripts/policy_frontmatter.py validate <rule-file>
```

- `read`: prints the parsed frontmatter as one JSON object on stdout.
- `validate`: prints `{"valid": true}` or `{"valid": false, "errors": ["..."]}`.

Exit codes: `0` on a successful parse regardless of validation result; `2` if the file
has no frontmatter block at all or the block doesn't parse (a real `FrontmatterError`,
distinct from a schema validation failure).
