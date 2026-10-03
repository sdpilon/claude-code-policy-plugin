# Contract: `skills/status/scripts/policy_status.py` (updated)

Backs `/policy:status` (User Story 3) and `/policy:audit`. Existing contract, changed
in three ways; everything else (the `policy-status.sh` wrapper, the "deterministic
inventory, classify once, cache the annotation" design) is unchanged.

## Changes from the current version

1. **Scan**: `(root / ".policy").glob("*.md")` becomes a recursive scan of
   `.policy/rule/**/*.md` — so organizational subdirectories are found, and files
   directly under old-style `.policy/*.md` (pre-migration) are *not* (Edge Cases: old
   format is out of scope for the updated skills).
2. **ID pattern**: `OBLIGATION_RE` (`\*\*([A-Z][A-Z0-9]*-\d+)\*\*:\s*(.+)`) becomes a
   bare-integer pattern (`\*\*(\d+)\*\*:\s*(.+)`) — no alpha prefix accepted. The
   pattern itself doesn't need to know about zero-padding (`\d+` already matches
   `047`); the captured string is passed through `scripts/policy_ids.py`'s `parse_id`
   to get the plain integer reported in `id` below.
3. **Tier source**: the inline `<!-- tier: ...; via: ... -->` comment convention is
   replaced by reading `verification.method`/`verification.via` from the file's
   frontmatter (via `scripts/policy_frontmatter.py`). A rule with no `verification`
   field, or a `method` outside the four enumerated values, is reported as
   `unclassified` — same fallback behavior as today, new source.

4. **Defects**: a rule with no `audience` field, or an empty one, is reported with
   `"defect": "audience missing"` rather than being classified. Any gap in the ID
   sequence (an integer below the highest ID in use, with neither a rule file nor a
   tombstone) is reported as a top-level `"gaps": [...]` entry (FR-017).
5. **Scope**: files directly under `.policy/` (old-style `<topic>.md`, pre-migration) are
   ignored, not parsed. A flat `.policy/rule/` (no subdirectories) is a fully supported
   input.

## CLI

Unchanged invocation shape: `policy-status.sh [args]` → `policy_status.py [args]`.

## Output (updated schema)

```json
[
  {
    "id": 47,
    "title": "No secrets in CI logs",
    "statement": "No secrets in CI logs MUST NOT appear in build output.",
    "tier": "ci-blocking",
    "via": "secret-scan job in ci.yml",
    "path": ".policy/rule/047.md"
  }
]
```

`title` is new (read from frontmatter); everything else keeps its existing meaning,
now sourced from frontmatter instead of an inline comment for `tier`/`via`.
