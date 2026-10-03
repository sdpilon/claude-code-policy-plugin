import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(script, *args, cwd=None):
    proc = subprocess.run([sys.executable, str(REPO / script), *args], cwd=cwd,
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def scratch():
    return tempfile.TemporaryDirectory()


def load(stdout):
    return json.loads(stdout)
