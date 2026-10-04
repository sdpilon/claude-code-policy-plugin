#!/usr/bin/env bash
# PostToolUse hook: format the file an Edit, Write, or MultiEdit just changed.
# Reads the hook payload on stdin. Always exits 0 so a formatter problem
# never blocks an edit.
set -uo pipefail

project="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
bin="$project/.venv/bin"

file="$(jq -r '.tool_input.file_path // empty' 2>/dev/null)"
[ -n "$file" ] || exit 0

# Only files inside the project; turn the path relative.
case "$file" in
"$project"/*) rel="${file#"$project"/}" ;;
*) exit 0 ;;
esac

# Spec Kit, Claude Code, and the plugin manifest tree are not ours to format.
case "$rel" in
.specify/* | .claude/* | .claude-plugin/*) exit 0 ;;
esac

[ -f "$file" ] || exit 0

case "$rel" in
*.py)
  "$bin/ruff" format --quiet -- "$file" || echo "format-changed: ruff format failed for $rel" >&2
  ;;
*.md)
  # fix exits nonzero when a violation has no automatic fix; the lint step reports those.
  "$bin/pymarkdown" fix "$file" >/dev/null 2>&1 || true
  ;;
*.sh)
  "$bin/shfmt" -i 2 -w -- "$file" || echo "format-changed: shfmt failed for $rel" >&2
  ;;
esac

exit 0
