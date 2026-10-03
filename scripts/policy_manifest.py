"""Shared, dependency-free manifest logic for /policy:init and /policy:update.

The manifest (`.policy/manifest.json`) records the content fingerprint of each file the plugin
wrote, so a later update can tell an unmodified file from a customized one.
See specs/002-policy-init-update/contracts/manifest.md.
"""

import difflib
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

FORMAT_VERSION = 1


class ManifestError(Exception):
    """The manifest is missing, unparseable, or from an unsupported format."""


def load_manifest(path):
    """Read and validate the manifest. Raises ManifestError; never guesses a baseline."""
    path = Path(path)
    if not path.exists():
        raise ManifestError(f"no manifest at {path}; run /policy:init or restore the file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ManifestError(f"manifest {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError(f"manifest {path} must be a JSON object")
    version = data.get("format_version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ManifestError(f"manifest {path} has no integer format_version; treating it as corrupt")
    if version > FORMAT_VERSION:
        raise ManifestError(f"manifest {path} uses format_version {version}; this plugin needs a newer plugin")
    files = data.get("files")
    if not isinstance(files, dict):
        raise ManifestError(f"manifest {path} has no files object")
    for name, entry in files.items():
        if not isinstance(entry, dict) or "sha256" not in entry or "shipped_version" not in entry:
            raise ManifestError(f"manifest {path} entry {name} is missing sha256 or shipped_version")
    return data


def _target_mode(path):
    """Mode to give a replaced file: keep the existing file's bits, or the umask default for a new one."""
    if path.exists():
        return stat.S_IMODE(path.stat().st_mode)
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


def atomic_write_bytes(path, data):
    """Replace path atomically: temp file in the same directory, chmod, then os.replace.

    The temp file is created 0600 by mkstemp, so its mode is set explicitly to the target's
    mode (plan research.md §6). Without this, a 0644 README becomes 0600 after an update.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = _target_mode(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".policy-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_manifest(path, data):
    """Write the manifest as two-space JSON with a trailing newline, atomically."""
    atomic_write_bytes(path, (json.dumps(data, indent=2) + "\n").encode("utf-8"))


def fingerprint(path):
    """SHA-256 hex digest over the file's bytes with CRLF normalized to LF (research.md §2).

    Non-UTF-8 content is hashed over its raw bytes, so it can never match a text template.
    """
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return hashlib.sha256(raw).hexdigest()
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def plugin_version():
    """The shipped plugin version, read from .claude-plugin/plugin.json (research.md §3)."""
    manifest = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["version"]


def classify(entry, file_hash, template_hash, exists):
    """Return the update state for one path (data-model.md's classification table).

    entry: the manifest entry dict, or None if the path is untracked.
    file_hash: fingerprint of the project's file, or None if absent.
    template_hash: fingerprint of the current shipped template, or None if not shipped.
    exists: whether the project file exists.
    """
    if entry is None:
        if template_hash is None:
            return None
        return "user-owned" if exists else "new"
    if template_hash is None:
        return "no-longer-shipped"
    if not exists:
        return "missing"
    if file_hash != entry["sha256"]:
        return "customized"
    return "current" if template_hash == entry["sha256"] else "stale"


def unified_diff(project_text, template_text, name):
    """Unified diff from the project's file to the current shipped template (FR-007)."""
    return "".join(
        difflib.unified_diff(
            project_text.splitlines(keepends=True),
            template_text.splitlines(keepends=True),
            fromfile=f"{name} (project)",
            tofile=f"{name} (shipped)",
        )
    )
