---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.
disable-model-invocation: true
---

Call the Skill tool twice, for "grilling" and "domain-modeling".

## Autonomous mode

**This skill is exempt from FENIX-AUTONOMOUS.md Rule 1 by design, not by oversight.** Its entire
purpose is a relentless interview that sharpens what to build — exactly the judgment doctrine
section 5 says autonomy is worst at: "Autonomous runs are worse than supervised ones at taste,
naming, and product judgment... Do not use it to decide what to build." Suppressing its questions
would not make it autonomous-safe; it would make it produce an unexamined plan under the appearance
of one that was interrogated.

If `scripts/trail.sh check` reports autonomous mode on and this skill is reached anyway, that is a
signal the run has stepped outside well-specified work, not a cue to answer the interview yourself.
Stop, log why via `scripts/trail.sh write` with `reversible=no`, and surface it for a human — per
FENIX_SHIP_LOOP.md's own Lane C, this step is already marked user-invoked, and Lane E's autonomous
path already runs alignment before autonomy starts, never during it.
