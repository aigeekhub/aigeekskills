#!/usr/bin/env bash
# Link this repo's Compound Engineering and Matt Pocock skills into ~/.claude/skills (bare names kept).
# Dry run by default. See scripts/link_install.py for the full contract and the safety guarantees.
#   scripts/link-install.sh                    show what would change
#   scripts/link-install.sh --apply            do it (moves anything in the way to a dated backup)
#   scripts/link-install.sh --rollback <dir>   undo
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    exec "$py" "$here/link_install.py" "$@"
  fi
done
echo "link-install: needs Python 3.8+ (tried python3, python)" >&2
exit 2
