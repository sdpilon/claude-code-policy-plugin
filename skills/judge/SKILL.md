---
name: judge
description: Decide whether a proposed rule for this repo — "we should always/never do X", a new convention, a house rule — belongs in the committed policy layer (.policy/, CONTRIBUTING.md, the agent-operational doc) or is actually personal/agent-collaboration preference that belongs in memory or a local/gitignored doc instead. Use this whenever it's genuinely unclear which bucket a new rule belongs in, including when you (the agent) are about to write a new procedural instruction into a repo file and aren't sure it's really a repo-wide policy rather than just how this person likes to work. Hands off to the add skill once something is judged to be a real policy.
---

# Judging policy vs. preference

Not every rule someone wants followed belongs in a repo. The line: a committed
file is for anything a stranger picking up this repo cold — a future contributor, a
different agent — would need or benefit from. Something that's really about how
one specific person wants to collaborate with an agent doesn't meet that bar, no
matter how firmly held or how often it comes up, and putting it in a repo file
anyway just adds noise for every other reader.

This is a real judgment call, not a keyword match, and it's easy to get wrong in
the direction of over-committing: a rule like "confirm with me before committing"
can look like process at first glance, get drafted straight into a policy file and
its derived docs, and only on reflection get recognized as being about how one
person wants to review agent work, not a property of the repo — at which point it
belongs in memory instead. That's the shape of mistake to watch for here.

## The actual test

Ask two questions, in order:

1. **Would this rule make sense stated about anyone or anything acting in this
   repo** — not just the current person, not just this agent specifically — **or
   does it only make sense as a statement about how one particular person likes to
   work?** "Automation should never merge, regardless of CI status" passes: it's a
   claim about where human judgment has to sit in this repo's process, true for
   any automation. "Confirm with me before committing" fails at face value — but
   see the next check before concluding that.
2. **Does an existing policy already have the same shape?** Look for a structural
   twin — e.g. a rule like "action A doesn't imply authorization for action B" that
   already exists somewhere in this repo's policy set in different clothes. If the
   proposed rule is really that pattern wearing a different outfit, it's
   policy-shaped even if the first framing sounded like preference — reframe it to
   match the existing pattern rather than discarding it. If instead the rule would
   need to flex depending on mood, context, or trust level rather than being a
   fixed authorization boundary, that's the tell that it's preference, not policy.

If it passes both checks: policy. If it fails: memory (or a local/gitignored doc —
see below for which).

## Don't let a hedge slide past unaddressed

A request phrased with a hedge — "for now," "I think," "maybe," "let's try" —
doesn't settle the verdict by itself, but it does need its own explicit pass;
running the two questions above and never mentioning the hedge is a gap, not a
shortcut. A hedge can mean either of two different things:

- The rule really is temporary or exploratory — leans toward "not yet decided"
  rather than a settled policy, which points toward memory (or simply not placing
  it anywhere yet and asking whether it's a real decision).
- The rule itself is durable and repo-wide, and the hedge is just how the person
  phrased it in the moment — doesn't change the verdict, but say so explicitly
  rather than reasoning as if the hedge weren't there.

Name the hedge in your reasoning and state which of the two it is and why, the same
way you'd name a structural twin or the lack of one. A verdict that never
acknowledges a hedge sitting right in the request reads as having missed it, even
if the verdict itself turns out right.

## Placing the verdict

**Judged as policy** → hand off to the add skill to actually create/extend the
relevant `.policy/<topic>.md`, `CONTRIBUTING.md`, and agent-operational-doc
sections. Don't duplicate that process here.

**Judged as not policy** → it splits further, by durability and relevance:

- **Agent-collaboration style** (how closely to review work, communication
  preferences, risk tolerance) → whatever persistent-memory mechanism this
  session has, as a feedback-type entry. Include the rule, a **Why:** line
  explaining the reasoning (including, if relevant, why it looked like policy at
  first), and a **How to apply:** line.
- **Personal/environment-specific but genuinely durable and project-relevant** (a
  local path, a tool preference tied to working on *this* repo specifically) → a
  gitignored local doc for this repo if one exists (e.g. `CLAUDE.local.md`) —
  that's fine there even though it's not memory.

Either way, say the verdict and the reasoning out loud before placing it — the
person asking should be able to see and override the reasoning, not just receive a
silent placement.
