"""GitHub issue tracker for audit_checks.py, through the gh CLI.

Search and create only. Nothing here closes an issue (FR-016). Auth comes from gh itself; the
consuming project's token needs Issues read and write, as documented in SKILL.md.
"""

import json
import os
import subprocess
import tempfile


class TrackerError(Exception):
    pass


class GitHubTracker:
    def __init__(self, repo=None, gh="gh"):
        self.repo = repo
        self.gh = gh

    def _run(self, *args):
        cmd = [self.gh, *args]
        if self.repo:
            cmd += ["--repo", self.repo]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            detail = proc.stderr.strip() or f"exit {proc.returncode}"
            raise TrackerError(f"gh {' '.join(args[:2])} failed: {detail}")
        return proc.stdout

    def find_open(self, label):
        out = self._run(
            "issue", "list", "--label", label, "--state", "open", "--json", "url", "--limit", "100"
        )
        return json.loads(out or "[]")

    def create(self, title, body, label):
        # Idempotent: --force updates an existing label instead of failing.
        self._run("label", "create", label, "--force")
        fd, path = tempfile.mkstemp(suffix=".md", prefix="policy-audit-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(body)
            out = self._run(
                "issue", "create", "--title", title, "--body-file", path, "--label", label
            )
        finally:
            os.unlink(path)
        return out.strip()
