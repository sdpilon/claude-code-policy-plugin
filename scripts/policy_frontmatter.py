"""Dependency-free read/write for the restricted YAML subset used in rule frontmatter.

Supported: `key: scalar`, inline lists `[a, b]`, block lists (`- item`), and one level of
nested mapping (indented `key: value`). Anything else raises FrontmatterError rather than
being guessed at. See specs/001-rule-per-file-restructure/contracts/policy_frontmatter.md.
"""

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

KEY_ORDER = ["title", "tags", "created", "modified", "audience", "verification", "synced_hash"]
AUDIENCES = {"human", "agent"}
METHODS = {"ci-blocking", "ci-checked", "human-verified", "written-only"}
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z?)?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")
NESTED_RE = re.compile(r"^  ([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


class FrontmatterError(Exception):
    def __init__(self, message, line=None):
        self.line = line
        super().__init__(f"line {line}: {message}" if line else message)


def _scalar(raw, line):
    raw = raw.strip()
    if raw == "":
        return ""
    if raw[0] in "\"'":
        quote = raw[0]
        if len(raw) < 2 or raw[-1] != quote:
            raise FrontmatterError("unterminated quoted string", line)
        body = raw[1:-1]
        if quote == '"':
            return json.loads(raw)
        return body
    return raw


def _inline_list(raw, line):
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        raise FrontmatterError("malformed inline list", line)
    inner = raw[1:-1].strip()
    if inner == "":
        return []
    return [_scalar(part, line) for part in inner.split(",")]


def parse(text):
    """Return the frontmatter of a rule file as a dict. Raises FrontmatterError."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("no frontmatter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise FrontmatterError("frontmatter block is not closed")

    fields = {}
    i = 1
    while i < end:
        line_no = i + 1
        raw = lines[i]
        i += 1
        if raw.strip() == "" or raw.lstrip().startswith("#"):
            continue
        m = KEY_RE.match(raw)
        if not m:
            raise FrontmatterError(f"unsupported syntax: {raw!r}", line_no)
        key, value = m.group(1), m.group(2)
        if value.strip() != "":
            fields[key] = (
                _inline_list(value, line_no)
                if value.lstrip().startswith("[")
                else _scalar(value, line_no)
            )
            continue
        # Empty value: a block list or a nested mapping follows.
        if i < end and lines[i].startswith("- "):
            items = []
            while i < end and lines[i].startswith("- "):
                items.append(_scalar(lines[i][2:], i + 1))
                i += 1
            fields[key] = items
        elif i < end and NESTED_RE.match(lines[i]):
            nested = {}
            while i < end and NESTED_RE.match(lines[i]):
                nm = NESTED_RE.match(lines[i])
                nested[nm.group(1)] = _scalar(nm.group(2), i + 1)
                i += 1
            fields[key] = nested
        else:
            fields[key] = ""
    return fields


def _render_scalar(value):
    if isinstance(value, list):
        return "[" + ", ".join(_render_scalar(v) for v in value) + "]"
    text = str(value)
    if text == "" or text != text.strip() or re.search(r"[:#\[\]{},&*!|>'\"%@`]", text):
        return json.dumps(text)
    return text


def render(fields):
    """Serialize fields back into the restricted subset, in KEY_ORDER then insertion order."""
    keys = [k for k in KEY_ORDER if k in fields] + [k for k in fields if k not in KEY_ORDER]
    out = ["---"]
    for key in keys:
        value = fields[key]
        if value is None:
            continue
        if isinstance(value, dict):
            out.append(f"{key}:")
            for sub_key, sub_value in value.items():
                out.append(f"  {sub_key}: {_render_scalar(sub_value)}")
        else:
            out.append(f"{key}: {_render_scalar(value)}")
    out.append("---")
    return "\n".join(out) + "\n"


def validate(fields):
    """Return a list of problems against the Rule schema (empty list means valid)."""
    errors = []
    title = fields.get("title")
    if not isinstance(title, str) or title.strip() == "":
        errors.append("title is required and must be a non-empty string")
    if "tags" in fields and not isinstance(fields["tags"], list):
        errors.append("tags must be a list")
    for key in ("created", "modified"):
        value = fields.get(key)
        if not isinstance(value, str) or not ISO_RE.match(value):
            errors.append(f"{key} is required and must be an ISO 8601 timestamp")
    audience = fields.get("audience")
    if not isinstance(audience, list) or not audience:
        errors.append("audience is required and must be a non-empty list")
    else:
        bad = [a for a in audience if a not in AUDIENCES]
        if bad:
            errors.append(f"audience values must be human or agent, got {bad}")
    verification = fields.get("verification")
    if not isinstance(verification, dict):
        errors.append("verification is required and must be a mapping with method and via")
    else:
        method = verification.get("method")
        if method not in METHODS:
            errors.append(f"verification.method must be one of {sorted(METHODS)}")
    synced = fields.get("synced_hash")
    if synced is not None and not (isinstance(synced, str) and SHA256_RE.match(synced)):
        errors.append("synced_hash must be a sha256 hex string when present")
    return errors


MODAL_RE = re.compile(r"\b(MUST NOT|SHOULD NOT|MUST|SHOULD|MAY)\b")
SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+")


def validate_statement(text):
    """Check a rule statement: one sentence with exactly one modal verb (constitution, Principle II).

    Returns a list of problems. Shared by add and edit so both writers enforce the same rule.
    """
    stripped = (text or "").strip()
    if not stripped:
        return ["statement must be non-empty"]
    problems = []
    if len(SENTENCE_BREAK_RE.split(stripped)) != 1:
        problems.append("statement must be one sentence")
    modals = MODAL_RE.findall(stripped)
    if len(modals) != 1:
        problems.append(
            f"statement must have exactly one modal verb (MUST, SHOULD, MUST NOT, MAY), found {len(modals)}"
        )
    return problems


def validate_tombstone(fields):
    """Schema for .policy/retired/<id>.md. Returns a list of problems."""
    errors = []
    title = fields.get("title")
    if not isinstance(title, str) or title.strip() == "":
        errors.append("title is required")
    retired = fields.get("retired")
    if not isinstance(retired, str) or not ISO_RE.match(retired):
        errors.append("retired is required and must be an ISO 8601 date")
    reason = fields.get("reason")
    if not isinstance(reason, str) or reason.strip() == "":
        errors.append("reason is required")
    superseded = fields.get("superseded_by")
    if superseded is not None and not (isinstance(superseded, str) and superseded.isdigit()):
        errors.append("superseded_by must be an integer ID when present")
    return errors


def now_utc():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_file(path):
    return parse(Path(path).read_text(encoding="utf-8"))


def _cli(argv):
    if len(argv) != 2 or argv[0] not in ("read", "validate"):
        print("usage: policy_frontmatter.py {read|validate} <rule-file>", file=sys.stderr)
        return 2
    command, path = argv
    try:
        fields = read_file(path)
    except FrontmatterError as e:
        print(json.dumps({"error": str(e)}))
        return 2
    if command == "read":
        print(json.dumps(fields))
        return 0
    errors = validate(fields)
    print(json.dumps({"valid": not errors, **({"errors": errors} if errors else {})}))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
