---
name: update
description: Refreshes the policy plugin's shipped templates in a repository that already has .policy/ (from /policy:init). Applies newer templates to files that are still unmodified, and reports customized, missing, or no-longer-shipped files without touching them. Use when the user asks to update, refresh, or sync the policy templates or check for policy template drift. Not for adding a rule (use /policy:add), syncing rules into CONTRIBUTING.md or CLAUDE.md (use /policy:sync), or running the CI audit (use /policy:audit).
---

# Updating shipped policy templates

Run from the repository root:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/update/scripts/update_policy.py
```

The script reads `.policy/manifest.json` and compares each tracked file with the plugin's current
template. It prints one line per file, grouped by state, then any diffs, then a summary.

## Report states

- `updated: <path>  (<old> -> <new>)`: the file was unmodified, so it was replaced with the newer template.
- `created: <path>`: a shipped file was missing from disk, so it was created and recorded.
- `current: <path>`: already matches the current template. No change.
- `customized: <path>`: the file was edited since it was written. It is left alone and a diff against the current template follows.
- `missing: <path>`: a tracked file was deleted. It is not recreated.
- `no-longer-shipped: <path>`: the plugin no longer ships this file. It is kept.
- `user-owned: <path>`: a shipped path exists on disk with no manifest entry. It is treated as the user's file and left alone.

## Exit codes

- `0`: nothing customized or missing
- `1`: at least one `customized` or `missing` file. Show the report to the user; CI can use this to surface drift.
- `2`: the manifest is missing, corrupt, or from a newer plugin. No files were changed. Report the message and the recovery step it names.

Never overwrite a `customized` file yourself. If the user wants the newer template, they merge the diff by hand.
