#!/usr/bin/env bash
# Run the same checks as .github/workflows/checks.yml, in the same order.
# Stops at the first failing step.
set -euo pipefail

cd "$(dirname "$0")/.."

md_files() {
  git ls-files -z '*.md' ':!.specify/**' ':!.claude/**' ':!.claude-plugin/**'
}

# Hash of every markdown file's current contents, so a fix pass can be checked
# for changes without depending on a clean git tree.
md_fingerprint() {
  md_files | xargs -0 git hash-object
}

echo "==> Verify lock file matches pyproject.toml"
uv lock --check

echo "==> Install locked dev tools"
uv sync --locked

echo "==> Lint"
uv run ruff check .

echo "==> Format check"
uv run ruff format --check .

echo "==> Markdown lint"
md_files | xargs -0 uv run pymarkdown scan

echo "==> Markdown format check"
before=$(md_fingerprint)
md_files | xargs -0 uv run pymarkdown fix
if [ "$before" != "$(md_fingerprint)" ]; then
  echo "Markdown is not formatted. Run: git ls-files -z '*.md' ':!.specify/**' ':!.claude/**' ':!.claude-plugin/**' | xargs -0 uv run pymarkdown fix"
  exit 1
fi

echo "==> Shell lint"
sh_files() { git ls-files -z '*.sh' ':!.specify/**' ':!.claude/**' ':!.claude-plugin/**'; }
sh_files | xargs -0 uv run shellcheck

echo "==> Shell format check"
sh_files | xargs -0 uv run shfmt -i 2 -d

echo "==> Unit tests"
uv run python -m unittest discover -s tests
