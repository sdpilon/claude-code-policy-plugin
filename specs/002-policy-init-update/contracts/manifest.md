# Contract: `.policy/manifest.json`

## Location

`<repo root>/.policy/manifest.json`, UTF-8 JSON, two-space indentation, trailing newline.

## Shape

```json
{
  "format_version": 1,
  "plugin_version": "0.2.0",
  "files": {
    ".policy/README.md": {
      "shipped_version": "0.2.0",
      "sha256": "<64 lowercase hex characters>"
    }
  }
}
```

Keys are written in the order shown. Readers MUST NOT depend on key order.

## Version rules

- `format_version` MUST be an integer. This contract defines version `1`.
- A reader that finds `format_version` greater than `1` MUST stop and report that the manifest needs a newer plugin (exit `2`, no file changes).
- A reader that finds a missing or non-integer `format_version` MUST treat the manifest as corrupt (exit `2`, no file changes).
- Adding fields within version `1` is not allowed. A schema change requires a new `format_version`.

## Fingerprint

`sha256` = SHA-256 hex digest of the file's bytes after replacing every `\r\n` with `\n`. The file is read as UTF-8; if it is not valid UTF-8, the digest is taken over the raw bytes, and the file is classified as `customized`.

## Failure behavior

| Condition | Result |
|---|---|
| File absent | Missing manifest: exit `2`, message names `/policy:init` or restoring the file |
| Not valid JSON | Corrupt manifest: exit `2`, message names the manifest path |
| Top level not an object, or `files` not an object | Corrupt manifest: exit `2` |
| Entry missing `sha256` or `shipped_version` | Corrupt manifest: exit `2` |

No failure path modifies any project file.
