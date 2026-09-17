# aigeekskills

Consolidated, editable Claude Code skills for the **FENIX SHIP LOOP** — one repo instead of three
loose, untracked installs.

## What's in here

Three upstream skill packs, imported whole via `git subtree` so every file is a real, editable,
committed part of this repo:

| Plugin | Upstream | What it brings |
|---|---|---|
| `mattpocock` | [mattpocock/skills](https://github.com/mattpocock/skills) | Alignment, TDD, spec/ticket flows, code review |
| `compound-engineering` | [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | Plan, work, simplify, review, ship, compound |
| `pstack` | [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude) | Verification, adversarial review, principles |

Thirteen skills — the ones the FENIX SHIP LOOP's Lane C loop actually calls — carry **FENIX
autonomous-mode edits** so they can run unattended under `/lfg`. See [FENIX-AUTONOMOUS.md](FENIX-AUTONOMOUS.md)
for the doctrine: when it activates, the four rules, the decision-trail format, and its honest
limits. Every other skill in all three packs ships as-is and is fully usable — just not yet
autonomy-edited.

## Install

```
claude plugin marketplace add aigeekhub/aigeekskills
claude plugin install mattpocock@aigeekskills
claude plugin install compound-engineering@aigeekskills
claude plugin install pstack@aigeekskills
```

## Pulling upstream updates

```
scripts/sync-upstream.sh mattpocock
scripts/sync-upstream.sh compound-engineering
scripts/sync-upstream.sh pstack
```

Each wraps `git subtree pull`. A pull refuses to run on a dirty tree, and any conflict will only ever
land in one of the 13 autonomy-edited files — the rest of each pack merges silently. After a clean
pull, `scripts/verify-closure.sh` confirms nothing references a component this repo doesn't ship.

## License and attribution

MIT, matching all three upstreams. See [NOTICE.md](NOTICE.md) for per-pack copyright and license
files, preserved in place under each pack's own directory.

## Building this repo

See [docs/plans/2026-09-17-001-feat-aigeekskills-consolidated-repo-plan.md](docs/plans/2026-09-17-001-feat-aigeekskills-consolidated-repo-plan.md)
for the implementation plan this repo is built from.
