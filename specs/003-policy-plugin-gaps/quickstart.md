# Quickstart: validate spec 003

A runnable guide to prove the feature works end to end. It uses a scratch repository, so
nothing in this checkout is changed. The contracts define each command's behavior:
[record_sync](contracts/record_sync.md), [edit_rule](contracts/edit_rule.md),
[audit_checks](contracts/audit_checks.md).

## Prerequisites

- Python 3.14 and `uv` on PATH.
- This repo checked out on branch `003-policy-plugin-gaps`.
- `tools/check.sh` passes before you start.

```bash
cd /path/to/policy && tools/check.sh
```

## Setup: a scratch repo with two rules

```bash
export PLUGIN=/path/to/policy
SCRATCH=$(mktemp -d) && cd "$SCRATCH"
mkdir -p .policy/rule .policy/retired
cat > .policy/rule/001.md <<'EOF'
---
title: "Commit messages are conventional"
tags: []
created: 2026-10-01T00:00:00Z
modified: 2026-10-01T00:00:00Z
audience: [human, agent]
verification:
  method: written-only
  via: ""
---

# Commit messages are conventional

**001**: Commit messages MUST follow Conventional Commits.
EOF
sed 's/001/002/g; s/Commit messages are conventional/Branches are short-lived/; s/Commit messages MUST follow Conventional Commits/Branches MUST be merged within a week/' .policy/rule/001.md > .policy/rule/002.md
```

## Scenario 1: record a sync (US1)

```bash
python3 "$PLUGIN/skills/sync/scripts/record_sync.py" 001 002
# expect: recorded 001 / recorded 002
python3 "$PLUGIN/skills/sync/scripts/record_sync.py" 001 002
# expect: unchanged 001 / unchanged 002, and no file mtime change
python3 "$PLUGIN/skills/sync/scripts/sync_status.py" --dir .policy/rule
# expect: both rules report changed: false
python3 "$PLUGIN/skills/sync/scripts/record_sync.py" 999
# expect: exit 2, error names 999, no file written
```

## Scenario 2: a single edit moves `modified` (US2)

```bash
python3 "$PLUGIN/skills/edit/scripts/edit_rule.py" --preview \
  --set 'statement=Commit messages MUST follow Conventional Commits and stay under 72 characters.' 001
# expect: before and after shown, no file change (diff .policy/rule/001.md is empty)
python3 "$PLUGIN/skills/edit/scripts/edit_rule.py" \
  --set 'statement=Commit messages MUST follow Conventional Commits and stay under 72 characters.' 001
# expect: changed 001; modified is now later than 2026-10-01
python3 "$PLUGIN/skills/sync/scripts/sync_status.py" --dir .policy/rule
# expect: 001 changed: true, 002 changed: false
```

Invalid edit, which must leave the file untouched:

```bash
python3 "$PLUGIN/skills/edit/scripts/edit_rule.py" \
  --set 'statement=This MUST do one thing and MAY do another.' 001
# expect: exit 2, rejected 001 (two modal verbs), file unchanged
```

## Scenario 3: a bulk edit is all-or-none (US3)

```bash
python3 "$PLUGIN/skills/edit/scripts/edit_rule.py" \
  --set 'audience=agent' 001 002
# expect: changed 001, changed 002
python3 "$PLUGIN/skills/edit/scripts/edit_rule.py" \
  --set 'verification.method=not-a-method' 001 002
# expect: exit 2, rejected 001 and 002, neither file changed
```

## Scenario 4: the audit files exactly the right issues (US4)

Write a registry with one passing check and one check that is not defined. Rule 001 is
`ci-checked` with `via: lint-clean`. Rule 002 is `ci-checked` with `via: deploy-gate`, which the
registry lacks.

```bash
cat > "$SCRATCH/checks.py" <<'EOF'
CHECKS = {"lint-clean": lambda: True}
EOF
# set 001 and 002 to ci-checked via the edit path, then:
python3 "$PLUGIN/skills/audit/scripts/audit_checks.py" \
  --registry "$SCRATCH/checks.py" --policy-dir .policy --tracker none
# expect: pass 001 / filed 002 (Build policy check: deploy-gate) (dry run)
```

Dedupe: run the audit with a tracker that already holds an open issue labelled
`policy-audit:deploy-gate`. Expect `skipped 002 (already open)` and nothing filed. The
automated tests cover this with an in-memory fake tracker.

## Scenario 5: the frontmatter docs match the parser (US6)

```bash
python3 -c "import sys; sys.path.insert(0, '$PLUGIN/scripts'); import policy_frontmatter as fm; print(type(fm.parse(open('.policy/rule/001.md').read())).__name__)"
# expect: dict
python3 -c "import sys; sys.path.insert(0, '$PLUGIN/scripts'); import policy_frontmatter as fm; fm.parse('no frontmatter')" 2>&1 | tail -1
# expect: FrontmatterError: no frontmatter block
```

## Cleanup

```bash
cd / && rm -rf "$SCRATCH"
```
