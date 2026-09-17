# NOTICE

This repository distributes MIT-licensed work from three upstream projects, each imported whole via
`git subtree` into its own directory under `skills/`. Every upstream's own `LICENSE` and `NOTICE`
files are preserved in place, unmodified. This file is a root-level index so attribution is visible
without walking three subdirectories.

FENIX DIGITAL ENTERPRISE LLC's own contributions — the marketplace manifest, `FENIX-AUTONOMOUS.md`,
the sync and verification scripts, and the autonomous-mode edits described below — are covered by the
root [LICENSE](LICENSE).

## Upstream sources

| Directory | Upstream | Copyright | License | Files |
| --- | --- | --- | --- | --- |
| `skills/mattpocock/` | [mattpocock/skills](https://github.com/mattpocock/skills) | (c) 2026 Matt Pocock | MIT — [LICENSE](skills/mattpocock/LICENSE) | 169 |
| `skills/compound-engineering/` | [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | (c) 2025 Every | MIT — [LICENSE](skills/compound-engineering/LICENSE) | 1294 |
| `skills/pstack/` | [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude) | (c) 2026 Lauren Tan (pstack skills, principles), (c) 2026 Cursor (`deslop`, `thermo-nuclear-code-quality-review`, `make-pr-easy-to-review`, `fix-ci`, `fix-merge-conflicts`, `get-pr-comments`, `what-did-i-get-done`) | MIT — [LICENSE](skills/pstack/LICENSE), [LICENSE-cursor-team-kit](skills/pstack/LICENSE-cursor-team-kit) | 216 |

pstack's own two-tier attribution — [NOTICE.md](skills/pstack/NOTICE.md) (full provenance, mapping
every affected skill to its exact upstream commit) and [NOTICE-skills.md](skills/pstack/NOTICE-skills.md)
(the skills-only distribution summary) — travels with it unmodified, since it already does this job
more precisely than a root-level table can.

## Import method

Each pack was imported at the commit shown in its subtree merge commit message, via:

```
git subtree add --prefix=skills/<pack> <upstream-remote> main --squash
```

`--squash` collapses each import to one commit rather than replaying the upstream's full history.
Full upstream history remains available at the source repositories linked above. Updates are pulled
with `scripts/sync-upstream.sh <pack>`, which wraps `git subtree pull` the same way.

## FENIX autonomous-mode edits

Thirteen skills across the three packs carry edits described in [FENIX-AUTONOMOUS.md](FENIX-AUTONOMOUS.md)
so they can run unattended under the FENIX SHIP LOOP's Lane E. These edits are additive — inserted as
an `## Autonomous mode` section per skill — and are FENIX DIGITAL ENTERPRISE LLC's own contribution,
layered on top of, not a replacement for, the upstream work each skill remains built on:

- `skills/mattpocock/`: `grill-with-docs`, `tdd`
- `skills/compound-engineering/`: `ce-plan`, `ce-work`, `ce-simplify-code`, `ce-code-review`, `ce-commit-push-pr`, `ce-compound`
- `skills/pstack/`: `poteto-mode`, `interrogate`, `blast-radius`, `create-verification-skill`, `babysit`

Every other skill in all three packs ships as imported, unmodified, and fully usable on its own.
