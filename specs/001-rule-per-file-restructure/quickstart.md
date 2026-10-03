# Quickstart: Validating the One-Rule-Per-File Restructuring

Run from a scratch directory, not this plugin repo or any real consuming project (per
this plugin's "test tooling against scratch copies" practice) — e.g. a temp dir with a
plain `.policy/rule/` tree, this plugin's `scripts/` on `PYTHONPATH`.

## Prerequisites

- Python 3, no additional packages.
- This plugin's `scripts/` directory and the relevant `skills/*/scripts/` on
  `PYTHONPATH`, or invoked by path directly.

## Scenario 1 — Add a rule without choosing a file (User Story 1)

```sh
mkdir -p /tmp/policy-smoke/.policy && cd /tmp/policy-smoke
python3 <plugin>/skills/add/scripts/add_rule.py \
  --statement "Secrets MUST NOT appear in CI logs." \
  --title "No secrets in CI logs" \
  --audience agent \
  --verification-method ci-blocking --verification-via "secret-scan job"
# Expect: {"id": 1, "path": ".policy/rule/001.md"}
python3 <plugin>/skills/add/scripts/add_rule.py \
  --statement "PRs MUST have one approval before merge." \
  --title "Require PR approval" --audience human \
  --verification-method ci-checked
# Expect: {"id": 2, "path": ".policy/rule/002.md"} — different ID, first file untouched
```

**Pass condition**: two files exist, `001.md` and `002.md`, under `.policy/rule/`;
running `add_rule.py` a third time never reuses `1` or `2`; moving `001.md` into a new
`.policy/rule/ci/` subdirectory and re-running `policy_status.py` still finds it under
ID `1` (reported as a plain integer, filename still zero-padded).

## Scenario 2 — Audience-driven sync (User Story 2)

```sh
python3 <plugin>/skills/sync/scripts/sync_status.py --dir .policy/rule
```

**Pass condition**: rule `1` (audience `agent`) and rule `2` (audience `human`) both
show `"changed": true` (no `synced_hash` yet). After `/policy:sync` applies a
propagation and writes `synced_hash` back, re-running `sync_status.py` shows
`"changed": false` for any rule whose content didn't change in between.

## Scenario 3 — Human-readable status (User Story 3)

```sh
python3 <plugin>/skills/status/scripts/policy_status.py --dir .policy/rule
```

**Pass condition**: output includes `"title": "No secrets in CI logs"` for rule `1`
and `"tier": "ci-blocking"` sourced from frontmatter, not an inline comment.

## Scenario 4 — Migrate an existing topic-file repo (User Story 4)

```sh
mkdir -p /tmp/policy-migrate/.policy && cd /tmp/policy-migrate
cat > .policy/security.md <<'EOF'
# Security Policy

## Secrets

**SEC-7**: Secrets MUST NOT be committed to the repository.
**SEC-8**: Secrets MUST be rotated within 90 days of exposure.

Rationale: a leaked secret is only as contained as how fast it's rotated and how
reliably it's kept out of history in the first place.
EOF
python3 <plugin>/skills/migrate/scripts/migrate_rules.py \
  --source-dir .policy --dest-dir .policy/rule
```

**Pass condition**: two new files appear under `.policy/rule/`; the JSON report's
`needs_review` lists both for missing `audience`, and flags the `SEC-7`/`SEC-8` pair's
shared rationale under one `shared_rationale_group` rather than silently duplicating or
discarding the shared paragraph.

## Full teardown

```sh
rm -rf /tmp/policy-smoke /tmp/policy-migrate
```
