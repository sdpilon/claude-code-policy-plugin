import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(script, *args, cwd=None):
    proc = subprocess.run(
        [sys.executable, str(REPO / script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def scratch():
    return tempfile.TemporaryDirectory()


def load(stdout):
    return json.loads(stdout)


def settle_docs(root, wording, rule_id=1):
    """Write derived docs the way a sync leaves them: each holds its audience's wording (R14)."""
    root = Path(root)
    if "human" in wording:
        (root / "CONTRIBUTING.md").write_text(wording["human"] + "\n", encoding="utf-8")
    if "agent" in wording:
        (root / "CLAUDE.md").write_text(wording["agent"] + "\n", encoding="utf-8")
        (root / ".claude" / "rules").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "rules" / f"{rule_id:03d}.md").write_text(
            wording["agent"] + "\n", encoding="utf-8"
        )
