#!/usr/bin/env bash
# Pull upstream improvements into one imported pack (plan R5, KTD5).
#
#   scripts/sync-upstream.sh status                     where each pack is pinned vs upstream
#   scripts/sync-upstream.sh <pack> [--no-verify]       git subtree pull, then closure check
#
# Packs: see scripts/upstreams.txt. Conflicts can only land in files FENIX edited (the ones that
# mention scripts/trail.sh); this script names them, and flags any conflict outside that set.
#
# Exit: 0 ok or already current | 2 usage | 3 dirty tree | 4 merge conflicts
#       5 merged but closure check failed | 6 git or network failure
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/.." && pwd)"
upstreams="${AIGEEKSKILLS_UPSTREAMS:-$here/upstreams.txt}"
cd "$repo" || exit 2

usage() { sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

lookup() { # pack -> "pack|remote|url|prefix|branch" or empty
  grep -v '^[[:space:]]*#' "$upstreams" | awk -F'|' -v p="$1" '$1 == p { print; exit }'
}

ensure_remote() { # remote url
  git remote get-url "$1" >/dev/null 2>&1 || git remote add "$1" "$2"
}

pinned_sha() { # prefix -> sha recorded by the most recent subtree squash commit
  git log -1 -E --grep="^git-subtree-dir: $1\$" --format=%B 2>/dev/null | sed -n 's/^git-subtree-split: //p' | head -1
}

edited_files() { # prefix -> files FENIX edited, one per line (those mentioning scripts/trail.sh)
  git grep -l 'scripts/trail.sh' HEAD -- "$1" 2>/dev/null | sed 's/^HEAD://'
}

cmd_status() {
  printf '%-22s %-9s %-9s %-8s %s\n' PACK PINNED UPSTREAM BEHIND "FENIX-EDITED FILES"
  local line pack remote url prefix branch pin up behind
  while IFS= read -r line; do
    IFS='|' read -r pack remote url prefix branch <<<"$line"
    ensure_remote "$remote" "$url"
    pin="$(pinned_sha "$prefix")"
    if ! git fetch -q "$remote" "$branch" 2>/dev/null; then
      printf '%-22s %-9s %-9s %-8s %s\n' "$pack" "${pin:0:7}" "?" "?" "(fetch failed)"; continue
    fi
    up="$(git rev-parse FETCH_HEAD)"
    behind="$(git rev-list --count "$pin..$up" 2>/dev/null || echo '?')"
    printf '%-22s %-9s %-9s %-8s %s\n' "$pack" "${pin:0:7}" "${up:0:7}" "$behind" "$(edited_files "$prefix" | wc -l | tr -d ' ')"
  done < <(grep -v '^[[:space:]]*#' "$upstreams" | grep -v '^[[:space:]]*$')
}

cmd_pull() { # pack verify(1|0)
  local pack="$1" verify="$2" line remote url prefix branch before rc out conflicts
  line="$(lookup "$pack")"
  [ -n "$line" ] || { echo "unknown pack '$pack'. Known: $(grep -v '^[[:space:]]*#' "$upstreams" | cut -d'|' -f1 | tr '\n' ' ')" >&2; return 2; }
  IFS='|' read -r pack remote url prefix branch <<<"$line"

  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "refusing to pull: tracked changes in the working tree (commit or stash them first):" >&2
    git status --short --untracked-files=no >&2
    return 3
  fi

  ensure_remote "$remote" "$url"
  before="$(git rev-parse HEAD)"
  out="$(git subtree pull --prefix="$prefix" "$remote" "$branch" --squash -m "subtree: pull $pack upstream" 2>&1)"; rc=$?

  if [ $rc -ne 0 ]; then
    conflicts="$(git diff --name-only --diff-filter=U)"
    if [ -n "$conflicts" ]; then
      echo "merge conflicts in $(echo "$conflicts" | wc -l | tr -d ' ') file(s):"
      local edited f
      edited="$(edited_files "$prefix")"
      while IFS= read -r f; do
        if echo "$edited" | grep -qxF -- "$f"; then echo "  expected (FENIX-edited): $f"
        else echo "  UNEXPECTED (not a FENIX edit, someone changed this file): $f"; fi
      done <<<"$conflicts"
      echo "Resolve each, then: git add <files> && git commit   |   or back out the merge: git merge --abort"
      return 4
    fi
    echo "git subtree pull failed:" >&2; echo "$out" | tail -5 >&2
    return 6
  fi

  if [ "$(git rev-parse HEAD)" = "$before" ]; then
    echo "$pack: already up to date (pinned at $(pinned_sha "$prefix" | cut -c1-7))"
    return 0
  fi
  echo "$pack: merged $(pinned_sha "$prefix" | cut -c1-7) cleanly. Changes:"
  git diff --stat "$before" HEAD | tail -4

  if [ "$verify" = 1 ] && [ -x "$here/verify-closure.sh" ]; then
    if ! bash "$here/verify-closure.sh"; then
      echo
      echo "closure check FAILED after merging $pack. The merge is committed, nothing was rolled back."
      echo "Review the findings above. Real dangling reference: fix it. Noise: add it to scripts/closure-allowlist.txt with a reason."
      echo "A skill or persona intentionally removed upstream: regenerate the lock with scripts/verify-closure.sh --write-roster."
      echo "To discard this merge entirely (your call, destructive): git reset --hard $before"
      return 5
    fi
  fi
  return 0
}

case "${1:-}" in
  ""|-h|--help|help) usage; [ -z "${1:-}" ] && exit 2 || exit 0 ;;
  status) cmd_status ;;
  *) verify=1; [ "${2:-}" = "--no-verify" ] && verify=0; cmd_pull "$1" "$verify" ;;
esac
