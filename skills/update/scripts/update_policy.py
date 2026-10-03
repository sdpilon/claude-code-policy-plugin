#!/usr/bin/env python3
"""Backs /policy:update: apply newer shipped templates to unmodified files and report the rest.

Only `stale` files are overwritten, and only `new` files absent from disk are created (FR-006,
FR-010). Customized, missing, no-longer-shipped, and user-owned paths are reported, never changed
(FR-007..FR-009). Exit: 0 clean, 1 customized or missing, 2 fail-closed (manifest problems).
See specs/002-policy-init-update/contracts/commands.md.
"""

import sys
from pathlib import Path

PLUGIN_ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "scripts" / "policy_manifest.py").exists()
)
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
import policy_manifest as pm

SHIPPED = {".policy/README.md": PLUGIN_ROOT / "templates" / "policy-readme.md"}

# Report label for each classification state, in output order.
LABELS = {
    "stale": "updated",
    "new": "created",
    "current": "current",
    "customized": "customized",
    "missing": "missing",
    "no-longer-shipped": "no-longer-shipped",
    "user-owned": "user-owned",
}


def main():
    repo = Path.cwd()
    manifest_path = repo / ".policy" / "manifest.json"
    try:
        manifest = pm.load_manifest(manifest_path)
    except pm.ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    files = dict(manifest["files"])
    shipped_version = pm.plugin_version()

    groups = {label: [] for label in LABELS.values()}
    diffs = []
    changed = False

    for path in sorted(set(files) | set(SHIPPED)):
        entry = files.get(path)
        target = repo / path
        exists = target.exists()
        file_hash = pm.fingerprint(target) if exists else None
        template = SHIPPED.get(path)
        template_hash = pm.fingerprint(template) if template else None
        state = pm.classify(entry, file_hash, template_hash, exists)

        if state is None:
            continue
        if state == "stale":
            old_version = entry["shipped_version"]
            pm.atomic_write_bytes(target, template.read_bytes())
            files[path] = {"shipped_version": shipped_version, "sha256": template_hash}
            groups["updated"].append(f"{path}  ({old_version} -> {shipped_version})")
            changed = True
        elif state == "new":
            pm.atomic_write_bytes(target, template.read_bytes())
            files[path] = {"shipped_version": shipped_version, "sha256": template_hash}
            groups["created"].append(path)
            changed = True
        elif state == "customized":
            groups["customized"].append(path)
            project_text = target.read_text(encoding="utf-8", errors="replace")
            diffs.append(pm.unified_diff(project_text, template.read_text(encoding="utf-8"), path))
        else:
            groups[LABELS[state]].append(path)

    for label, items in groups.items():
        for item in items:
            print(f"{label}: {item}")
    for diff in diffs:
        print(f"--- diff {diff.splitlines()[0][4:]}")
        print("".join(diff.splitlines(keepends=True)[1:]), end="")

    if changed or manifest["plugin_version"] != shipped_version:
        pm.write_manifest(
            manifest_path,
            {
                "format_version": pm.FORMAT_VERSION,
                "plugin_version": shipped_version,
                "files": files,
            },
        )

    print(
        f"summary: {len(groups['updated'])} updated, {len(groups['created'])} created, "
        f"{len(groups['customized'])} customized, {len(groups['missing'])} missing"
    )
    return 1 if groups["customized"] or groups["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
