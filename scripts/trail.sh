#!/usr/bin/env bash
# FENIX autonomous mode — decision trail writer and activation check.
# Doctrine: ../FENIX-AUTONOMOUS.md sections 1 and 3. Skills call this file, never reimplement it.
#
# Usage:
#   source scripts/trail.sh
#   fenix_autonomous_active && echo "autonomous mode is on"
#   fenix_trail_write "<skill>" "<decision>" "<why>" "<evidence-path-or-none>" "<yes|no>"
#
# Or invoke directly for a one-off check/write without sourcing:
#   scripts/trail.sh check
#   scripts/trail.sh write "<skill>" "<decision>" "<why>" "<evidence>" "<reversible>"

set -u

_fenix_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

# Doctrine section 1: four activation signals, first match wins. Off by default.
fenix_autonomous_active() {
  local root
  root="$(_fenix_repo_root)"

  # Signal: repo config
  if grep -qs '^autonomous: on' "$root/.compound-engineering/config.yaml" 2>/dev/null; then
    return 0
  fi

  # Signal: environment override
  if [ "${FENIX_AUTONOMOUS:-}" = "1" ]; then
    return 0
  fi

  # Signal: forced-on pipeline contexts. Harnesses that invoke skills from /lfg or a
  # disable-model-invocation context should export FENIX_PIPELINE=1 before calling in.
  if [ "${FENIX_PIPELINE:-}" = "1" ]; then
    return 0
  fi

  return 1
}

# Doctrine section 3: one TSV row per non-obvious decision. Never blocks — always exits 0
# on a successful write; a directory-creation failure prints to stderr and returns nonzero
# so a calling skill can fall back to reporting inline rather than losing the row silently.
fenix_trail_write() {
  local skill="$1" decision="$2" why="$3" evidence="${4:-none}" reversible="${5:-yes}"
  local root date_str slug trail_dir trail_file timestamp

  root="$(_fenix_repo_root)"
  date_str="$(date -u +%Y-%m-%d)"
  timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  slug="$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null | tr '/' '-' || echo 'no-branch')"
  trail_dir="$root/docs/autonomous"
  trail_file="$trail_dir/${date_str}-${slug}-trail.tsv"

  if [ "$reversible" != "yes" ] && [ "$reversible" != "no" ]; then
    echo "fenix_trail_write: reversible must be 'yes' or 'no', got '$reversible'" >&2
    return 1
  fi

  mkdir -p "$trail_dir" || {
    echo "fenix_trail_write: could not create $trail_dir" >&2
    return 1
  }

  if [ ! -f "$trail_file" ]; then
    printf 'timestamp\tskill\tdecision\twhy\tevidence\treversible\n' > "$trail_file"
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$timestamp" "$skill" "$decision" "$why" "$evidence" "$reversible" >> "$trail_file"

  echo "$trail_file"
  return 0
}

# Direct-invocation entry points, so a skill can shell out instead of sourcing.
if [ "${BASH_SOURCE[0]:-}" = "${0:-}" ]; then
  case "${1:-}" in
    check)
      if fenix_autonomous_active; then
        echo "autonomous: on"
        exit 0
      else
        echo "autonomous: off"
        exit 1
      fi
      ;;
    write)
      shift
      fenix_trail_write "$@"
      ;;
    *)
      echo "usage: $0 {check|write <skill> <decision> <why> <evidence> <reversible>}" >&2
      exit 2
      ;;
  esac
fi
