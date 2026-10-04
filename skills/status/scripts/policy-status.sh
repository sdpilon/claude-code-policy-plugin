#!/usr/bin/env bash
# Thin, defensive entrypoint for policy_status.py -- see that file for the
# actual logic. Checked by *success*, not just availability: a `python3`
# that resolves to a non-functional stub (seen in the wild on some Windows
# setups, where it passes `command -v` but fails at runtime) must not be
# silently treated as "available" only to fail with a confusing error later.
set -euo pipefail

dir="$(CDPATH="" cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; raise SystemExit(sys.version_info.major != 3)' >/dev/null 2>&1; then
  echo "ERROR: a working python3 is required to run policy-status" >&2
  exit 1
fi

exec python3 "$dir/policy_status.py" "$@"
