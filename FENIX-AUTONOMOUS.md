# FENIX autonomous mode

Shared doctrine for the FENIX SHIP LOOP. This file is the contract every forked skill honors.
Owner: Mista Boo, FENIX DIGITAL ENTERPRISE LLC. Workflow: `FENIX_SHIP_LOOP.md` v1.2.

This fork exists to make the Lane C loop survive an unattended run. Upstream skills are written for
a human sitting at the keyboard who can answer a question. Autonomous mode is what happens when
nobody is there.

---

## 1. Activation

Autonomous mode is **off by default**. It turns on when any of these is true:

| Signal | Where | Meaning |
|---|---|---|
| `autonomous: on` | `<repo-root>/.compound-engineering/config.yaml` | Per-repo default |
| `FENIX_AUTONOMOUS=1` | environment | Per-run override |
| Invoked from `/lfg`, a pipeline, or any `disable-model-invocation` context | harness | Forced on, cannot be overridden off |
| User says "autonomous", "unattended", "overnight", "don't ask me" | prompt | On for that run |

Check it the same way pstack's SessionStart hook checks its own sheet:

```bash
grep -s '^autonomous: on' "$(git rev-parse --show-toplevel)/.compound-engineering/config.yaml" >/dev/null \
  || [ "$FENIX_AUTONOMOUS" = "1" ]
```

When off, the skill behaves exactly as upstream wrote it. Nothing below applies.

---

## 2. The four rules

### Rule 1 — Never block. Decide, record, continue.

Every point where the upstream skill would call `AskUserQuestion` (or `request_user_input`,
`ask_user`) becomes: pick the documented default, write one line to the decision trail saying what
was picked and why, and keep going.

A question you cannot answer from the repo, the plan, or this doctrine is **not** a reason to stop.
It is a reason to pick the reversible option and flag it for review.

**The single exception, which never yields:** an irreversible or outward-facing action still stops
and waits. See Rule 4.

### Rule 2 — Prefer the reversible branch.

When the default is genuinely unclear, take the option that is easiest to undo:

- Narrower scope over wider scope
- A new file over editing an existing one
- Additive change over destructive change
- Feature-flagged over enabled-by-default
- Deferred to `Parking lot` over built speculatively

An autonomous run that did too little is a nuisance. One that did too much is a cleanup job.

### Rule 3 — Proof, or it did not happen.

No unit is complete without an artifact from the **running app**. Not "it compiles". Not "tests
pass". An artifact means a screenshot, a recording, a captured response body, or a diffed output
file, produced by `/verify` against the real thing.

This rule tightens under autonomy rather than relaxing. A human watching can smell a false
"done". Nobody is watching. The evidence is the only thing standing between a green run and a
silently broken branch.

If verification cannot run, **stop the unit and record why**. Do not proceed to the next unit on an
unverified one, and do not mark it complete.

### Rule 4 — Irreversible actions still stop.

Autonomous mode never authorizes:

- `git push --force`, `reset --hard`, `branch -D`, history rewrites
- Merging any PR
- Deleting data, dropping tables, running destructive migrations against a real database
- Rotating, writing, or printing secrets
- Publishing, deploying, or sending anything outward facing
- Spending money

Hitting one of these ends the run cleanly: commit what is proven, write the trail, open the PR if
one is warranted, and report what is waiting on a human. An autonomous agent that force-pushes at
3am is not a productivity gain.

---

## 3. The decision trail

Every autonomous run writes `docs/autonomous/<YYYY-MM-DD>-<slug>-trail.tsv`, one row per decision,
tab separated:

```
timestamp	skill	decision	why	evidence	reversible
```

- `decision` — what was chosen, in plain words
- `why` — the reason, referencing the plan, the repo, or a rule above
- `evidence` — path to the artifact, or `none`
- `reversible` — `yes` or `no`. Any `no` row must also appear in the PR description

This is the audit surface. When Mista Boo reads an overnight run, the trail is what he reads first.
It follows pstack's `show-me-your-work` pattern; skills that already implement that use it directly
instead of writing a second log.

Write a row when the decision was non-obvious. Do not log every file read.

---

## 4. What lands at the end

An autonomous run finishes with:

1. A branch with small, verified commits
2. The decision trail
3. Evidence artifacts under `docs/autonomous/evidence/`
4. An open PR whose description carries: what was built, what was assumed, every irreversible thing
   that was skipped and why, and the `Parking lot` of ideas deliberately not built
5. **No merge.** Ever. The PR is where the human re-enters.

---

## 5. Honest limits

- Autonomous runs are worse than supervised ones at taste, naming, and product judgment. Use Lane C
  autonomously for mechanical and well-specified work. Do not use it to decide what to build.
- A hallucinated verification feature map makes every downstream proof worthless. Keep the verify
  skill current and re-check the feature map after upstream changes.
- Cross-model review may send diffs to another vendor. That is a per-repo setting, not an autonomy
  setting. Client repos stay off.
- These skills are edited in place, imported via `git subtree` rather than a wrapper layer. Each
  edit is a small `## Autonomous mode` section inserted after the frontmatter, with the upstream
  body left otherwise untouched — that discipline is what keeps `git subtree pull` tractable later.
  Only 13 of the ~131 imported skills carry this edit; a future conflict on `sync-upstream.sh` can
  only ever land in one of those 13. Do not restructure upstream content beyond that one section.
