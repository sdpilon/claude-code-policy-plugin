# Trigger tests: edit skill description (T009)

Method: research R8. Each case was sent to a fresh-context general-purpose subagent with
no tools. The agent saw only the four candidate descriptions (add, edit, retire, sync) and one
request, and answered with a single skill name. Descriptions were copied verbatim from each
`skills/<name>/SKILL.md`.

## Results

| Case | Request | Expected | Answered | Result |
|---|---|---|---|---|
| P1 | "Reword rule 004 so it says Secrets MUST NOT appear in build logs." | edit | edit | pass |
| P2 | "Make rule 012 agent-only." | edit | edit | pass |
| P3 | "Change the check for rule 7 to ci-blocking, and retitle it 'Tag releases'." | edit | edit | pass |
| P4 | "Bump the audience on rules 003, 005 and 009 to agent only." | edit | edit | pass |
| N1 | "We should have a rule that every PR needs two approvals." | add | add | pass |
| N2 | "Rule 004 is superseded by rule 011, so take it out." | retire | retire | pass |
| N3 | "Sync the docs with the rules, I edited a few of them." | sync | sync | pass |
| N4 | "Rule 004 is no longer true, we dropped that practice last month." | retire | retire | pass |

**Result: 8 of 8 pass.** Four positive and four negative cases, including one boundary case (N4)
where the wording sounds like an edit but the intent is retirement.

## Limits

- The agents routed on the four descriptions alone, not inside a live session that also lists
  the other plugin skills. This tests the description's discrimination, which is what the
  constitution asks for.
- Eight cases is a small sample. Re-run this set after any change to the `edit` description,
  and add a case for any routing mistake seen in use.
