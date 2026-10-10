#!/usr/bin/env python3
"""Closure check for aigeekskills (plan requirement R7).

Fails when any shipped skill or agent points at something this repo does not ship:
  token     a ce-* name, pstack:<name>, or Skill-tool quoted name that resolves to no skill or agent
  link      a relative markdown link whose target file does not exist
  manifest  a marketplace source, plugin.json, or plugin.json skill path that does not exist

Known false positives (temp-file names, schema tokens, example paths) live in
scripts/closure-allowlist.txt, one `kind|value|reason` per line. Anything not listed fails.
"""
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {"tests", "docs", "site", "node_modules", "fixtures", ".changeset", ".git"}
SKIP_FILES = {"CHANGELOG.md"}
# Claude Code built-ins a Skill-tool reference may legitimately name without shipping them.
BUILTINS = {"loop", "verify", "run", "schedule", "simplify", "init", "review", "batch"}

CE_TOKEN = re.compile(r"\bce-[a-z][a-z0-9-]*")
# Personas are listed by bare backticked role name (e.g. `correctness-reviewer`), never with a ce- prefix.
ROLE_TOKEN = re.compile(r"`([a-z][a-z0-9-]*-(?:reviewer|researcher|agent))`")
PSTACK_TOKEN = re.compile(r"\bpstack:([a-z][a-z0-9-]*)")
SKILL_TOOL = re.compile(r"Skill tool[^\"`\n]{0,40}[\"`]([a-z][a-z0-9-]*)[\"`]")
MD_LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:")


def load_allowlist(path):
    allowed = {"token": set(), "link": set()}
    if not path.is_file():
        return allowed
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, value, *_ = (line.split("|") + ["", ""])[:3]
        if kind in allowed:
            allowed[kind].add(value.strip())
    return allowed


def in_scope(rel_to_skills):
    """Skill and agent content only; pack-root docs (README, AGENTS.md) describe the pack, not a skill."""
    parts = rel_to_skills.parts
    if any(p in SKIP_DIRS for p in parts) or parts[-1] in SKIP_FILES or not parts[-1].endswith(".md"):
        return False
    return any(p in ("skills", "agents") for p in parts[1:-1])


def collect(skills_dir):
    files, skills, agents = [], set(), set()
    for dirpath, dirnames, filenames in os.walk(skills_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            full = Path(dirpath) / name
            rel = full.relative_to(skills_dir)
            if not in_scope(rel):
                continue
            files.append(full)
            if name == "SKILL.md":
                skills.add(full.parent.name)
            if full.parent.name in ("agents", "personas"):
                agents.add(full.stem)
    return files, skills, agents


def check_text(files, skills, agents, allowed, root, used):
    findings = []
    known = skills | agents
    for f in files:
        rel = f.relative_to(root).as_posix()
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for m in CE_TOKEN.finditer(line):
                tok = m.group(0)
                if tok.endswith("-"):
                    continue  # trailing hyphen = filename prefix such as ce-polish-<id>
                if tok not in known and tok[3:] not in agents:
                    if tok in allowed["token"]:
                        used.add(tok)
                    else:
                        findings.append(("token", rel, n, tok))
            for m in ROLE_TOKEN.finditer(line):
                role = m.group(1)
                if role not in known:
                    if role in allowed["token"]:
                        used.add(role)
                    else:
                        findings.append(("token", rel, n, role))
            for m in PSTACK_TOKEN.finditer(line):
                if m.group(1).endswith("-"):
                    continue  # placeholder prefix such as pstack:effort-<level>
                if m.group(1) not in known and f"pstack:{m.group(1)}" not in allowed["token"]:
                    findings.append(("token", rel, n, f"pstack:{m.group(1)}"))
            for m in SKILL_TOOL.finditer(line):
                name = m.group(1)
                if name not in known and name not in BUILTINS and name not in allowed["token"]:
                    findings.append(("token", rel, n, name))
            for m in MD_LINK.finditer(line):
                target = m.group(1)
                if SCHEME.match(target) or target[0] in "/~<" or "<" in target:
                    continue
                if not (f.parent / target).resolve().exists():
                    if target in allowed["link"]:
                        used.add(target)
                    else:
                        findings.append(("link", rel, n, target))
    return findings


def roster_of(files, root):
    """Every skill, agent, and persona file. A sync that drops one must be a visible, reviewed event."""
    keep = [f for f in files if f.name == "SKILL.md" or f.parent.name in ("agents", "personas")]
    return sorted(f.relative_to(root).as_posix() for f in keep)


def check_roster(files, root):
    roster_file = root / "scripts" / "closure-roster.txt"
    if not roster_file.is_file():
        return [("roster", "scripts/closure-roster.txt", 0, "missing; generate with: verify-closure.sh --write-roster")]
    expected = [l.strip() for l in roster_file.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    present = set(roster_of(files, root))
    return [("roster", path, 0, "in closure-roster.txt but missing on disk") for path in expected if path not in present]


def check_manifests(root):
    findings = []
    market = root / ".claude-plugin" / "marketplace.json"
    if not market.is_file():
        return [("manifest", ".claude-plugin/marketplace.json", 0, "missing")]
    for plugin in json.loads(market.read_text(encoding="utf-8")).get("plugins", []):
        src = root / plugin["source"]
        label = f"plugin '{plugin['name']}'"
        if not src.is_dir():
            findings.append(("manifest", ".claude-plugin/marketplace.json", 0, f"{label} source {plugin['source']} missing"))
            continue
        pj = src / ".claude-plugin" / "plugin.json"
        if not pj.is_file() and not (src / "plugin.json").is_file():
            findings.append(("manifest", plugin["source"], 0, f"{label} has no plugin.json"))
            continue
        manifest = json.loads((pj if pj.is_file() else src / "plugin.json").read_text(encoding="utf-8"))
        for skill_path in manifest.get("skills", []):
            if not (src / skill_path / "SKILL.md").is_file():
                findings.append(("manifest", pj.relative_to(root).as_posix(), 0, f"{label} lists {skill_path} but it has no SKILL.md"))
    return findings


def run(root):
    root = Path(root).resolve()
    allowed = load_allowlist(root / "scripts" / "closure-allowlist.txt")
    files, skills, agents = collect(root / "skills")
    used = set()
    findings = check_text(files, skills, agents, allowed, root, used) + check_manifests(root) + check_roster(files, root)
    dead = sorted((allowed["token"] | allowed["link"]) - used)
    return findings, dead, files, skills, agents


def main(argv):
    root = Path(__file__).resolve().parent.parent
    if "--root" in argv:
        root = Path(argv[argv.index("--root") + 1])
    root = root.resolve()

    if "--write-roster" in argv:
        files, _, _ = collect(root / "skills")
        entries = roster_of(files, root)
        header = "# Every skill, agent, and persona file expected to ship. Regenerate ONLY after reviewing a sync:\n# verify-closure.sh --write-roster\n"
        (root / "scripts" / "closure-roster.txt").write_text(header + "\n".join(entries) + "\n", encoding="utf-8")
        print(f"wrote scripts/closure-roster.txt: {len(entries)} entries")
        return 0

    findings, dead, files, skills, agents = run(root)
    unique = sorted(set(findings))
    for kind, rel, line, what in unique:
        print(f"FAIL {kind:<8} {rel}:{line}  {what}")
    if dead:
        print(f"NOTE: {len(dead)} allowlist entr{'y' if len(dead) == 1 else 'ies'} matched nothing (safe to prune): {', '.join(dead)}")
    status = "FAIL" if unique else "PASS"
    print(f"{status}: {len(unique)} dangling reference(s); scanned {len(files)} files, {len(skills)} skills, {len(agents)} agents/personas")
    return 1 if unique else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
