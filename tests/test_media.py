import unittest

from whisper_srt_aligner.media import select_audio_stream
from whisper_srt_aligner.models import AudioStream


class MediaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.streams = [
            AudioStream(0, 1, "aac", 2, "rus", None, False),
            AudioStream(1, 2, "eac3", 6, "eng", "English", True),
        ]

    def test_selects_requested_language(self) -> None:
        self.assertEqual(1, select_audio_stream(self.streams, "en").relative_index)

    def test_explicit_stream_wins(self) -> None:
        self.assertEqual(0, select_audio_stream(self.streams, "eng", 0).relative_index)

    def test_does_not_silently_choose_wrong_language(self) -> None:
        with self.assertRaisesRegex(ValueError, "No audio stream matches"):
            select_audio_stream(self.streams, "de")


if __name__ == "__main__":
    unittest.main()
