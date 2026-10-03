#!/usr/bin/env python3
"""Backs /policy:init: create the minimal .policy/ skeleton and its manifest (FR-001..FR-003).

Never overwrites an existing file (FR-002). A README that exists without a manifest is
user-owned and left untracked. See specs/002-policy-init-update/contracts/commands.md.
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        next(
            p
            for p in Path(__file__).resolve().parents
            if (p / "scripts" / "policy_manifest.py").exists()
        )
        / "scripts"
    ),
)
import policy_manifest as pm

PLUGIN_ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "scripts" / "policy_manifest.py").exists()
)
TEMPLATE = PLUGIN_ROOT / "templates" / "policy-readme.md"


def main():
    repo = Path.cwd()
    policy = repo / ".policy"
    manifest_path = policy / "manifest.json"
    if manifest_path.exists():
        print("already initialized: .policy/manifest.json")
        return 0

    for directory in (policy / "rule", policy / "retired"):
        directory.mkdir(parents=True, exist_ok=True)

    files = {}
    readme = policy / "README.md"
    shipped = pm.plugin_version()
    if readme.exists():
        print("user-owned: .policy/README.md (not tracked)")
    else:
        shutil.copyfile(TEMPLATE, readme)
        files[".policy/README.md"] = {"shipped_version": shipped, "sha256": pm.fingerprint(readme)}
        print("created: .policy/README.md")

    pm.write_manifest(
        manifest_path,
        {"format_version": pm.FORMAT_VERSION, "plugin_version": shipped, "files": files},
    )
    print("created: .policy/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
