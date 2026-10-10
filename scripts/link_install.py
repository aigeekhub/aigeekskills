#!/usr/bin/env python3
"""Point ~/.claude/skills at this repo, so bare skill names keep working (/ce-plan, /tdd, /grill-with-docs).

Compound Engineering and Matt Pocock skills are self-contained, so each one can be linked on its own.
pstack is NOT linked: it needs its plugin hook and agents, so it stays a plugin (/pstack:<name>).

  link_install.py                       dry run, changes nothing
  link_install.py --apply               do it
  link_install.py --rollback <dir>      undo an --apply using the dir it printed

Safety: nothing is deleted. A real directory in the way is MOVED into a dated backup folder, an old link
is recorded and replaced, and --rollback restores both. Any failure mid-apply undoes what was done so far.
Links are junctions on Windows (symlinks need admin there), plain symlinks elsewhere.
Never remove a junction with `rm -rf`: it can follow the link and delete the target's contents.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WIN = os.name == "nt"


def desired(repo):
    """name -> source dir for every skill that should be linked."""
    want = {}
    ce = repo / "skills" / "compound-engineering" / "skills"
    for d in sorted(ce.iterdir()):
        if (d / "SKILL.md").is_file():
            want[d.name] = d
    matt = repo / "skills" / "mattpocock"
    listed = json.loads((matt / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("skills", [])
    for rel in listed:  # only what Matt's own manifest publishes, never his in-progress or deprecated folders
        d = (matt / rel).resolve()
        if (d / "SKILL.md").is_file():
            want.setdefault(d.name, d)
    return want


def _ps(command):
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip() or f"powershell exit {r.returncode}")
    return r.stdout


def inspect(target):
    """name -> {kind, target} for everything directly inside target."""
    entries = {}
    if not target.exists():
        return entries
    if WIN:
        quoted = str(target).replace("'", "''")
        out = _ps(f"Get-ChildItem -LiteralPath '{quoted}' -Force | ForEach-Object {{ [pscustomobject]@{{ n=$_.Name; lt=[string]$_.LinkType; t=($_.Target -join ';'); d=[bool]$_.PSIsContainer }} }} | ConvertTo-Json -Compress").strip()
        rows = json.loads(out) if out else []
        for row in [rows] if isinstance(rows, dict) else rows:
            kind = row["lt"].lower() if row["lt"] else ("dir" if row["d"] else "file")
            # Trust LinkType, never Target alone: children of a junctioned folder report a Target
            # even though they are plain directories, and treating those as links would replace real data.
            entries[row["n"]] = {"kind": kind, "target": (row["t"] or None) if row["lt"] else None}
    else:
        for p in target.iterdir():
            if p.is_symlink():
                entries[p.name] = {"kind": "symlink", "target": os.readlink(p)}
            else:
                entries[p.name] = {"kind": "dir" if p.is_dir() else "file", "target": None}
    return entries


def same_path(a, b):
    norm = lambda p: os.path.normcase(os.path.normpath(str(p)))
    return norm(a) == norm(b)


def make_link(src, dst):
    if WIN:
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"mklink failed for {dst}: {(r.stdout + r.stderr).strip()}")
    else:
        os.symlink(src, dst)


def remove_link(path):
    """Remove a link without touching what it points at."""
    if WIN:
        quoted = str(path).replace("'", "''")
        _ps(f"(Get-Item -LiteralPath '{quoted}' -Force).Delete()")
    else:
        os.unlink(path)


def managed_elsewhere(target):
    """Reasons this folder may belong to something else (it is a link, or sits inside a git repo)."""
    reasons = []
    shown, real = os.path.normcase(os.path.abspath(target)), Path(os.path.realpath(target))
    if shown != os.path.normcase(str(real)):
        reasons.append(f"{target} is itself a link to {real}")
    probe = real if real.exists() else real.parent
    r = subprocess.run(["git", "-C", str(probe), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        reasons.append(f"it lives inside the git repository {r.stdout.strip()}, so --apply would change that repository's tracked files")
    return reasons


def make_plan(want, have):
    plan = []
    for name, src in sorted(want.items()):
        e = have.get(name)
        if e is None:
            plan.append(("link", name, src, None))
        elif e["target"] and same_path(e["target"], src):
            plan.append(("keep", name, src, None))
        elif e["target"]:
            plan.append(("repoint", name, src, e["target"]))
        else:
            plan.append(("move+link", name, src, e["kind"]))
    return plan


def summarize(plan, have, want):
    counts = {}
    for op, *_ in plan:
        counts[op] = counts.get(op, 0) + 1
    labels = {"link": "new links", "repoint": "old links repointed at the repo", "move+link": "real dirs moved to backup, then linked", "keep": "already linked here"}
    for op in ("link", "repoint", "move+link", "keep"):
        if counts.get(op):
            names = [n for o, n, *_ in plan if o == op]
            print(f"  {counts[op]:>3}  {labels[op]}   e.g. {', '.join(names[:4])}{' ...' if len(names) > 4 else ''}")
    stale = sorted(n for n in have if n.startswith("ce-") and n not in want)
    if stale:
        print(f"  {len(stale):>3}  stale ce-* entries this repo no longer ships (left alone): {', '.join(stale[:6])}{' ...' if len(stale) > 6 else ''}")


def apply(plan, target, backups, repo):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = backups / stamp
    (bdir / "moved").mkdir(parents=True)
    manifest = {"target": str(target), "repo": str(repo), "created": [], "repointed": {}, "moved": []}
    save = lambda: (bdir / "MANIFEST.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    save()
    try:
        for op, name, src, extra in plan:
            dst = target / name
            if op == "keep":
                continue
            if op == "repoint":
                remove_link(dst)
                manifest["repointed"][name] = extra
            elif op == "move+link":
                shutil.move(str(dst), str(bdir / "moved" / name))
                manifest["moved"].append(name)
            make_link(src, dst)
            manifest["created"].append(name)
            save()
        for op, name, src, extra in plan:  # prove every link resolves to a real skill
            if not (target / name / "SKILL.md").is_file():
                raise RuntimeError(f"{name} does not resolve to a SKILL.md after linking")
    except Exception as exc:
        print(f"FAILED: {exc}\nundoing this run ...", file=sys.stderr)
        rollback(bdir, quiet=True)
        raise
    return bdir


def rollback(bdir, quiet=False):
    m = json.loads((bdir / "MANIFEST.json").read_text(encoding="utf-8"))
    target = Path(m["target"])
    for name in reversed(m["created"]):
        p = target / name
        if p.exists() or p.is_symlink():
            remove_link(p)
        if name in m["repointed"]:
            make_link(m["repointed"][name], p)
        elif name in m["moved"]:
            shutil.move(str(bdir / "moved" / name), str(p))
    if not quiet:
        print(f"rolled back {len(m['created'])} entries; backups in {bdir} are untouched")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", metavar="DIR")
    ap.add_argument("--force-managed-target", action="store_true", help="apply even though the target belongs to a link or a git repo")
    ap.add_argument("--target", type=Path, default=Path.home() / ".claude" / "skills")
    ap.add_argument("--backups", type=Path, default=Path.home() / ".claude" / "skills-backups")
    args = ap.parse_args(argv)
    repo = Path(__file__).resolve().parent.parent

    if args.rollback:
        rollback(Path(args.rollback))
        return 0

    want, have = desired(repo), inspect(args.target)
    plan = make_plan(want, have)
    print(f"target: {args.target}\nsource: {repo}\n{len(want)} skills to expose (pstack stays a plugin):")
    summarize(plan, have, want)
    reasons = managed_elsewhere(args.target)
    if reasons:
        print("\nWARNING: this target belongs to something else:")
        for why in reasons:
            print(f"  - {why}")
        print("  Applying would rewrite files that other tooling or other machines may rely on.")
        if args.apply and not args.force_managed_target:
            print("\nrefusing to --apply. Decide how this should fit first, or pass --force-managed-target.")
            return 3
    if not args.apply:
        print("\ndry run, nothing changed. Re-run with --apply to do it.")
        return 0
    if not any(op != "keep" for op, *_ in plan):
        print("\nnothing to do.")
        return 0
    args.target.mkdir(parents=True, exist_ok=True)
    bdir = apply(plan, args.target, args.backups, repo)
    print(f"\ndone. {sum(1 for p in plan if p[0] != 'keep')} entries changed and verified.\nundo with: link-install.sh --rollback \"{bdir}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
