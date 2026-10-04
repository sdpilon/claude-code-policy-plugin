---
name: init
description: "Bootstraps the .policy/ layer in a repository that doesn't have one yet: creates rule/ and retired/, a starter README, and the manifest that /policy:update relies on. Use when the user asks to set up, initialize, or bootstrap policy in a repo. Not for adding a rule (use /policy:add) or for refreshing templates in an existing project (use /policy:update)."
---

# Initializing policy in a repository

Run from the repository root:

```sh
python3 <plugin>/skills/init/scripts/init_policy.py
```

The script creates:

- `.policy/rule/` and `.policy/retired/`, empty
- `.policy/README.md`, from the shipped template, tracked in the manifest
- `.policy/manifest.json`, recording the README's fingerprint and the plugin version

## Behavior

- If `.policy/manifest.json` already exists, the script does nothing and says so.
- If `.policy/README.md` exists without a manifest, it's treated as the user's own file. The script leaves it unchanged and doesn't track it.
- The script never modifies an existing file.

Report the lines the script printed. If the project was already initialized, say that and point to `/policy:update` for refreshing shipped templates.
