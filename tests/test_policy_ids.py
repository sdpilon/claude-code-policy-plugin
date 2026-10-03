import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import policy_ids as ids  # noqa: E402


class FormatParseTests(unittest.TestCase):
    def test_zero_pads_to_three_digits(self):
        self.assertEqual(ids.format_id(47), "047")
        self.assertEqual(ids.format_id(1), "001")

    def test_grows_past_three_digits_without_repadding(self):
        self.assertEqual(ids.format_id(1000), "1000")

    def test_parse_round_trips_and_accepts_unpadded(self):
        self.assertEqual(ids.parse_id(ids.format_id(47)), 47)
        self.assertEqual(ids.parse_id("47"), 47)

    def test_parse_rejects_non_digits(self):
        self.assertIsNone(ids.parse_id("SEC-7"))
        self.assertIsNone(ids.parse_id("readme"))


class HighestAndAllocateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rule = self.root / "rule"
        self.retired = self.root / "retired"

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_or_missing_tree_is_zero(self):
        self.assertEqual(ids.highest_id(self.rule, self.retired), 0)

    def test_finds_max_across_nested_subdirectories(self):
        (self.rule / "ci").mkdir(parents=True)
        (self.rule / "001.md").write_text("x")
        (self.rule / "ci" / "047.md").write_text("x")
        self.assertEqual(ids.highest_id(self.rule, self.retired), 47)

    def test_tombstones_count_toward_highest(self):
        self.rule.mkdir()
        self.retired.mkdir()
        (self.rule / "001.md").write_text("x")
        (self.retired / "066.md").write_text("x")
        self.assertEqual(ids.highest_id(self.rule, self.retired), 66)

    def test_allocate_skips_retired_id(self):
        self.retired.mkdir()
        (self.retired / "002.md").write_text("x")
        self.rule.mkdir()
        (self.rule / "001.md").write_text("x")
        n = ids.allocate_id(self.rule, self.retired, ids.reserve_file(self.rule))
        self.assertEqual(n, 3)
        self.assertTrue((self.rule / "003.md").exists())

    def test_allocate_retries_past_collision_then_raises(self):
        calls = []

        def always_taken(n):
            calls.append(n)
            return False

        with self.assertRaises(RuntimeError):
            ids.allocate_id(self.rule, self.retired, always_taken, max_attempts=5)
        self.assertEqual(len(calls), 5)

    def test_allocate_retries_on_reservation_failure(self):
        outcomes = iter([False, True])
        n = ids.allocate_id(self.rule, self.retired, lambda _n: next(outcomes))
        self.assertEqual(n, 2)


if __name__ == "__main__":
    unittest.main()
