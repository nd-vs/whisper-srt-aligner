import unittest
from pathlib import Path

from whisper_srt_aligner.batch import discover_pairs, episode_key


class BatchTest(unittest.TestCase):
    def test_extracts_episode_key(self) -> None:
        self.assertEqual("S04E09", episode_key(Path("Show.S4E9.1080p.mkv")))
        self.assertEqual("S02E103", episode_key(Path("Show 2x103.srt")))

    def test_pairs_by_episode_despite_different_names(self) -> None:
        folder = Path(__file__).parent / "fixtures" / "batch_valid"
        pairs, errors = discover_pairs(folder, "*.mkv", "*.srt")
        self.assertEqual([], errors)
        self.assertEqual("S01E01", pairs[0].key)

    def test_reports_ambiguous_pairs(self) -> None:
        folder = Path(__file__).parent / "fixtures" / "batch_ambiguous"
        pairs, errors = discover_pairs(folder, "*.mkv", "*.srt")
        self.assertEqual([], pairs)
        self.assertIn("expected one video", errors[0])


if __name__ == "__main__":
    unittest.main()
