---
name: add
description: Add or modify a process/procedure policy in .policy/<topic>.md (the invariant rule + rationale) — step 1 of a two-step process. It deliberately does NOT touch CONTRIBUTING.md or CLAUDE.md; it ends by flagging that those are now out of sync and recommending the sync skill (step 2) to propagate the change. Use this whenever the user wants to add, define, write down, or formalize a new project policy, procedure, convention, or house rule for this repo — including phrasing like "we should have a rule about...", "let's decide how we handle...", "add a procedure for...", or "what's our policy on..." — even when they don't say the word "policy" explicitly. Also use it for editing an existing obligation's wording when a prior assumption turned out stale. If it's unclear whether the proposed rule belongs in the repo at all versus being personal preference, use the judge skill first, then come back here once it's confirmed as policy.
---

# Adding a policy

This convention splits process rules into three layers, and every policy topic
needs all three kept in sync eventually — but as two separate, deliberately
sequenced steps, not one bundled action:

1. **`.policy/<topic>.md`** — the invariant rule and *why* it exists, written at a
   level that makes sense regardless of who or what is carrying it out. Same
   altitude as a product-principles doc's principle + rationale, but for process
   rather than product. **This skill writes this layer only.**
2. **`CONTRIBUTING.md`** — the human-readable narrative version, referencing the
   policy file for full rationale rather than restating it.
3. **`CLAUDE.md`** (or whatever this project's agent-operational doc is called) —
   the agent-operational version: the same rule, phrased as something an agent can
   act on directly, also referencing the policy file.

Layers 2 and 3 are **the sync skill's job, run as a separate, later step** — never
inline here, even when the edit looks small enough to "just also" fix while you're
in the file. Committing a policy change and committing its propagation into the
human/agent docs are different units of review: the first is "what's the rule now,"
the second is "does everything that describes the rule agree with it," and
bundling them hides which one a reviewer is actually looking at. This split also
keeps each commit a single logical change — a different file touched for a
genuinely different reason (propagating vs. deciding) is a different change.

Read the existing files in `.policy/` before writing a new one — they're the style
guide for this repo. Notice the pattern: obligations as `<PREFIX>-N: <subject>
MUST/SHOULD/MUST NOT/MAY <requirement>`, one sentence each, grouped into `##`
sections, each section followed by a short "Rationale:" paragraph explaining what
actually breaks without it (not just "because I said so"). Match that tone; don't
invent a new format for the new topic.

## Before writing anything

Confirm the topic and its actual scope. If the user's request is already crisp (a
clear rule, a clear reason), you don't need to interview them further — draft
directly. If it's a rough idea ("we should have some kind of policy about
deploys"), ask clarifying questions one at a time: what's the actual rule, why does
it matter, what's the failure mode without it. Prefer multiple-choice questions
when there's a natural set of options.

Then apply the same test the visibility policy (if this repo has one) uses for
anything else that might go in it: **would this be useful to a stranger picking up
the repo cold** — any future contributor or agent, not just the person asking right
now? If the answer feels like "no, this is really about how *I* like to work," stop
and suggest running the judge skill instead — that's exactly the judgment call it
exists to make. This kind of rule has been misjudged before in practice: something
about how one specific person wants an agent to collaborate with them gets drafted
straight into a repo's policy files, then on reflection gets recognized as not
belonging there and moved to memory instead. Don't re-litigate that kind of
decision once it's already been made for this repo.

## Writing the policy layer

1. **`.policy/<topic>.md`** — copy `templates/policy-template.md` and fill in the
   obligation IDs; don't freehand the structure. Each obligation gets its own
   `<PREFIX>-N` (one sentence, exactly one MUST/SHOULD/MUST NOT/MAY), followed by a
   shared "Rationale:" for the section it belongs to. Check existing `.policy/*.md`
   files for prefixes already taken before picking a new one — a prefix is
   assigned once and never reused, even if an obligation is later removed or the
   file is restructured, so anything that ever cited it by ID doesn't silently
   start pointing at something else. If the topic has more than one distinct rule
   area, split it into sections the same way, each with its own obligations. Don't
   pad it with implementation detail that belongs in the agent-operational doc
   instead — mechanism (exact commands, exact tool calls) lives there, written
   later by the sync skill, not here.

   Editing an existing obligation's wording (not just adding a new one) belongs
   here too — e.g. a rationale that assumed a credential/permission state which
   has since changed. Update the text under its existing ID; IDs are never
   renumbered or reused, but the sentence they label can be corrected as
   understanding evolves.

2. **Check whether this project has a product-principles doc** (a Spec Kit
   `constitution.md`, or an equivalent). If it does, and the rule is durable and
   non-negotiable enough that violating it would be a real regression — not just a
   process nicety — flag that it might belong there instead of (or in addition to)
   a regular policy, and ask before proceeding either way. This should be rare;
   most new policies are regular process rules, not product/governance principles.
   If the project has no such doc, skip this step.

Do not touch `CONTRIBUTING.md` or the agent-operational doc in this pass, even to
fix an obviously related, obviously small mention — that propagation is the sync
skill's job (see "Finishing up").

## Finishing up

- If the new policy is replacing something that was sitting in memory (a
  not-yet-decided convention, an interim exception), say so and note that the
  memory entry should be retired once this is committed. Don't leave both existing
  at once.
- Show the user what you're about to write (or the diff, if extending an existing
  file) before committing — a brand-new `.policy/<topic>.md` file is a new
  top-level/structural file in most repos' own conventions and usually needs
  confirmation before being added; extending an existing policy file with a new
  section usually doesn't, but use judgment per this repo's own rules on that.
- Commit — just the `.policy/<topic>.md` change, nothing else. Follow this repo's
  own git/GitHub conventions (every commit through a PR, etc.) if it has them.
  Pushing a branch and opening its PR are typically separate authorizations in
  repos that care about this distinction — confirm before opening the PR, don't
  treat permission to commit as permission to also open it.
- **Conclude by stating plainly that this change is now unsynced**: name the
  policy file just changed and say that `CONTRIBUTING.md`/the agent-operational doc
  may no longer agree with it, and recommend running the sync skill next. Don't run
  it yourself as part of this skill, and don't silently leave the recommendation
  implied — say it as an explicit next step the user can act on (or decline) on
  their own schedule.
