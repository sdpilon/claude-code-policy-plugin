# Contract: audit_checks.py

Backs the audit skill (FR-010 to FR-016). Runs in CI, non-interactive.

## Invocation

```text
python3 skills/audit/scripts/audit_checks.py \
    --registry <path/to/checks.py> \
    [--policy-dir .policy] \
    [--tracker github|none]
```

- `--registry`: required. Path to a consumer-supplied Python file.
- `--tracker`: `github` (default) files and searches issues with `gh`. `none` logs what it would
  file and changes nothing. Tests use `none` or an in-memory fake.

## Registry contract

The file must define:

```python
CHECKS: dict[str, Callable[[], bool]]
```

- Keys are check names, matched exactly against `verification.via`.
- Each callable takes no arguments and returns `True` when the check passes.
- The plugin does not load or ship any other part of the registry.

A registry that fails to import, or lacks `CHECKS`, is a hard error: the audit exits 2 without
filing anything.

## Behavior

For each rule under `--policy-dir/rule` with `verification.method: ci-checked`:

1. If `defect` is set on the rule: log `skipped (defect)` and continue (FR-014).
2. If `verification.via` is not a key in `CHECKS`: this is an unbuilt check. Search for an open
   issue with label `policy-audit:<via>`. If none, file `Build policy check: <via>` (FR-012).
   Log `filed` or `skipped (already open)`.
3. Otherwise run `CHECKS[via]()`. If it returns `True`, log `pass`. If it returns `False`,
   search for an open issue with the label. If none, file `Policy check failing: <via>`
   (FR-011). Log `filed` or `skipped (already open)`.
4. A check that raises is treated as failing, and the exception text goes in the issue body.
   It never stops the run.

Issues are stamped with the label `policy-audit:<via>` and the body marker
`<!-- policy-audit-key: <via> -->` (FR-013). The body names each rule ID and title that depends
on the check.

Two rules that share a check produce one issue, not two.

## Output

One line per rule on stdout: `pass <ID>`, `filed <ID> <issue-url>`, `skipped <ID> (<reason>)`.
Errors on stderr, prefixed `error:`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | the run finished. Failing checks and filed issues do not change the exit code (FR-015). |
| 2 | registry error or missing policy dir |
| 1 | tracker error after retries (for example, `gh` not authenticated) |

## Guarantees

- The audit never closes an issue (FR-016) and never edits a rule (SKILL guardrail).
- Running it twice with no change to rule or check state files nothing new on the second run
  (SC-004).
- A rule that never fails and has a check produces no output beyond `pass`.
