import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import policy_manifest as pm  # noqa: E402


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, data):
        path = self.dir / name
        path.write_bytes(data)
        return path

    def test_crlf_and_lf_copies_have_identical_digests(self):
        lf = self._write("lf.md", b"line one\nline two\n")
        crlf = self._write("crlf.md", b"line one\r\nline two\r\n")
        self.assertEqual(pm.fingerprint(lf), pm.fingerprint(crlf))

    def test_digest_is_64_lowercase_hex_characters(self):
        path = self._write("a.md", b"content\n")
        self.assertRegex(pm.fingerprint(path), re.compile(r"^[0-9a-f]{64}$"))

    def test_non_utf8_file_is_hashed_over_raw_bytes(self):
        raw = b"\xff\xfe\x00bad\r\n"
        path = self._write("binary.md", raw)
        self.assertEqual(pm.fingerprint(path), hashlib.sha256(raw).hexdigest())

    def test_content_change_changes_digest(self):
        a = self._write("a.md", b"one\n")
        b = self._write("b.md", b"two\n")
        self.assertNotEqual(pm.fingerprint(a), pm.fingerprint(b))


VALID_HASH = "a" * 64


def _manifest(**overrides):
    data = {
        "format_version": 1,
        "plugin_version": "0.2.0",
        "files": {".policy/README.md": {"shipped_version": "0.2.0", "sha256": VALID_HASH}},
    }
    data.update(overrides)
    return data


class ManifestIOTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "manifest.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_round_trip_preserves_fields(self):
        pm.write_manifest(self.path, _manifest())
        loaded = pm.load_manifest(self.path)
        self.assertEqual(loaded["format_version"], 1)
        self.assertEqual(loaded["plugin_version"], "0.2.0")
        self.assertEqual(loaded["files"][".policy/README.md"]["sha256"], VALID_HASH)

    def test_written_file_is_two_space_indented_with_trailing_newline(self):
        pm.write_manifest(self.path, _manifest())
        text = self.path.read_text(encoding="utf-8")
        self.assertTrue(text.endswith("\n"))
        self.assertIn('\n  "format_version": 1', text)

    def test_missing_file_names_policy_init(self):
        with self.assertRaises(pm.ManifestError) as ctx:
            pm.load_manifest(self.path)
        self.assertIn("/policy:init", str(ctx.exception))

    def test_invalid_json_names_manifest_path(self):
        self.path.write_text("{ not json", encoding="utf-8")
        with self.assertRaises(pm.ManifestError) as ctx:
            pm.load_manifest(self.path)
        self.assertIn(str(self.path), str(ctx.exception))

    def test_newer_format_version_says_newer_plugin(self):
        pm.write_manifest(self.path, _manifest(format_version=99))
        with self.assertRaises(pm.ManifestError) as ctx:
            pm.load_manifest(self.path)
        self.assertIn("newer plugin", str(ctx.exception))

    def test_missing_format_version_is_corrupt(self):
        data = _manifest()
        del data["format_version"]
        pm.write_manifest(self.path, data)
        with self.assertRaises(pm.ManifestError):
            pm.load_manifest(self.path)

    def test_entry_without_sha256_is_corrupt(self):
        data = _manifest(files={".policy/README.md": {"shipped_version": "0.2.0"}})
        pm.write_manifest(self.path, data)
        with self.assertRaises(pm.ManifestError):
            pm.load_manifest(self.path)


class PluginVersionTests(unittest.TestCase):
    def test_reads_version_from_plugin_json(self):
        import json
        manifest = Path(pm.__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
        expected = json.loads(manifest.read_text(encoding="utf-8"))["version"]
        self.assertEqual(pm.plugin_version(), expected)


class ClassifyTests(unittest.TestCase):
    H1 = "1" * 64
    H2 = "2" * 64

    def entry(self, sha=H1):
        return {"shipped_version": "0.1.0", "sha256": sha}

    def test_current(self):
        self.assertEqual(pm.classify(self.entry(self.H1), self.H1, self.H1, exists=True), "current")

    def test_stale_when_unmodified_and_template_changed(self):
        self.assertEqual(pm.classify(self.entry(self.H1), self.H1, self.H2, exists=True), "stale")

    def test_customized_when_hash_differs(self):
        self.assertEqual(pm.classify(self.entry(self.H1), self.H2, self.H2, exists=True), "customized")

    def test_missing_when_entry_but_no_file(self):
        self.assertEqual(pm.classify(self.entry(self.H1), None, self.H1, exists=False), "missing")

    def test_no_longer_shipped_when_entry_but_no_template(self):
        self.assertEqual(pm.classify(self.entry(self.H1), self.H1, None, exists=True), "no-longer-shipped")

    def test_new_when_no_entry_and_no_file(self):
        self.assertEqual(pm.classify(None, None, self.H1, exists=False), "new")

    def test_user_owned_when_no_entry_but_file_present(self):
        self.assertEqual(pm.classify(None, self.H2, self.H1, exists=True), "user-owned")


class UnifiedDiffTests(unittest.TestCase):
    def test_diff_header_names_file_and_shipped_side(self):
        out = pm.unified_diff("a\nb\n", "a\nc\n", ".policy/README.md")
        self.assertIn(".policy/README.md", out)
        self.assertIn("shipped", out)
        self.assertIn("-b", out)
        self.assertIn("+c", out)


if __name__ == "__main__":
    unittest.main()
