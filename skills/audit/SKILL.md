---
name: audit
description: Checks self-verifiable rules in .policy/rule/ against live repo state and files a ticket for each unmet one. Automated CI step only; there is no live user to ask mid-run.
---

# Auditing self-checkable rules

Runs in CI, non-interactively. It runs the checks for the rules whose `verification.method` is
`ci-checked`. The plugin supplies the runner, deduplication, and filing through
`scripts/audit_checks.py`. The checks themselves live in the consuming project's own registry
file, which encodes that project's checks. A check proves presence, never sufficiency.

Run from the repository root. `${CLAUDE_PLUGIN_ROOT}` is the plugin's root directory, the folder
that contains `skills/` and `scripts/`. If it is not set in your shell, use the folder two levels
above this skill's base directory.

```text
python3 ${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/audit_checks.py --registry <path/to/checks.py> [--policy-dir .policy] [--tracker github|none]
```

## The registry

The project writes one Python file, for example `ci/policy_checks.py`, that defines:

```python
CHECKS = {
    "secret-scan job": lambda: check_secret_scan(),  # returns True when the check passes
}
```

- Keys match `verification.via` in the rule, exactly.
- Each value is a function with no arguments that returns `True` for a pass. A check that
  returns `False` or raises counts as failing, and a raised exception's text goes in the issue.
- A rule whose `via` is not a key is an **unbuilt** check. The audit files an issue to build it.
  It does not skip it.

If the registry fails to import, or does not define `CHECKS` as a dict, the audit exits 2 and
files nothing.

## Contract

- For each `ci-checked` rule, in ID order:
  - `defect` set: log `skipped <ID> (defect)`. The check does not run.
  - No `verification.via`: log `skipped <ID> (no verification.via)`.
  - Check passes: log `pass <ID>`.
  - Check fails, or is unbuilt: look for an open issue with the label `policy-audit:<via>`. If one
    exists, log `skipped <ID> (already open: <url>)`. If none, file one and log `filed <ID> <url>`.
- Rules that share a `via` share one check run and at most one issue. The other rules log
  `skipped <ID> (tracked by <url>)`.
- The audit never closes an issue, and it never edits a rule.
- It never fails the build because a rule can't be verified. A tracker error (for example, `gh`
  not authenticated) is logged against each rule it affects as `error <ID> (tracker: ...)`. The
  remaining rules are still checked, and the run exits 1 at the end.

## Dedupe key

Every issue the audit files carries:

- the label `policy-audit:<via>`, which is the search key, and
- a hidden body marker `<!-- policy-audit-key: <via> -->`.

The key is the check name, not the rule's ID or title. Renumbering or retitling a rule therefore
does not file a duplicate. The title is `Policy check failing: <via>` for a failing check, and
`Build policy check: <via>` for an unbuilt one.

If a rule changes its `via`, the audit files a new issue under the new name and leaves the old
one open, since the audit never closes issues. Close the old one by hand.

## Trackers

- `github` (default): searches and files issues with `gh`. `scripts/github_tracker.py` creates the
  `policy-audit:<via>` label if it is missing. It has no close operation.
- `none`: a dry run. It logs what it would file and changes nothing. Use it to test a registry
  locally.

## Token scopes

The plugin's own skills need no token; they read and write local files only. The `github` tracker
needs a token with **Issues: read and write** on the repo, to search for open issues and file new
ones. Nothing more is required. A token without issue write access fails the first filing
attempt, so check it before the first CI run.

## Guardrails

- The audit never edits rules, and it never changes a `verification` field.
- A rule with `"defect"` set is skipped and logged, not checked.
- The plugin ships no check implementations. A check in the plugin's own repo would break
  Principle I (mechanism, never content).
