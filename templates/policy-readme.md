# Policy

This directory holds the repository's committed process policy. Each rule is its own file.

- `rule/<id>.md` is the source of truth for one rule. IDs are zero-padded numbers (for example `047`), unique across the directory, and never reused.
- `retired/<id>.md` is a frontmatter-only tombstone for a rule that was removed. It keeps the ID reserved.
- Derived documents, such as `CONTRIBUTING.md` and the agent-operational doc, are outputs. Edit the rule, then sync.
- `manifest.json` records what the policy plugin wrote into this directory, so updates can tell untouched files from customized ones. Do not edit it by hand.

Rule files live in `rule/` and are yours to write. This README is regenerated only by a plugin update, and only while it is unmodified.
