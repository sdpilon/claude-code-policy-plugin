"""Serialize rule writes between record_sync and edit (T029, edge case: concurrent edits).

Every writer takes write_lock(rule_dir) around its read-compare-write, so two writers cannot
interleave. The lock is an advisory flock on <rule_dir>/.write.lock. The file name does not end
in .md, so the rule scans never see it. Advisory locks only protect writers that take them: any
other tool that writes rule files directly is still unprotected.
"""

import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path

LOCK_NAME = ".write.lock"


class LockTimeout(Exception):
    pass


class ChangedDuringWrite(Exception):
    pass


@contextmanager
def write_lock(rule_dir, timeout=10.0, poll=0.05):
    """Hold the rule-directory write lock, or raise LockTimeout after timeout seconds."""
    path = Path(rule_dir) / LOCK_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LockTimeout(str(path)) from None
                time.sleep(poll)
        yield
    finally:
        os.close(fd)  # closing the descriptor releases the flock


def write_if_unchanged(path, expected, updated, write=None):
    """Replace path with updated only if it still holds expected.

    Callers must hold write_lock. Without it, a change can land between the check and the replace.
    """
    from policy_manifest import atomic_write_bytes

    write = write or atomic_write_bytes
    if Path(path).read_text(encoding="utf-8") != expected:
        raise ChangedDuringWrite(str(path))
    write(path, updated.encode("utf-8"))
