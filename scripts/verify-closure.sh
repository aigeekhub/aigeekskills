#!/usr/bin/env bash
# Closure check (plan R7): fail if any skill or agent references something this repo does not ship.
# Usage: scripts/verify-closure.sh [--root DIR]
# Exit:  0 clean, 1 dangling reference(s) found, 2 no Python interpreter available.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    exec "$py" "$here/verify_closure.py" "$@"
  fi
done

echo "verify-closure: needs Python 3.8+ (tried python3, python)" >&2
exit 2
