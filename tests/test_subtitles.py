import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from whisper_srt_aligner.models import AlignedCue
from whisper_srt_aligner.subtitles import parse_srt, render_srt


class SubtitleTest(unittest.TestCase):
    def test_parses_common_srt_and_preserves_multiline_text(self) -> None:
        source = Path(__file__).parent / "fixtures" / "sample.srt"
        cues = parse_srt(source)
        self.assertEqual(1, len(cues))
        self.assertEqual("<i>Hello</i>\nworld!", cues[0].text)
        self.assertEqual(("hello", "world"), cues[0].tokens)

    def test_renders_sequential_indices_and_optional_bom(self) -> None:
        cue = AlignedCue(7, 9.0, 10.0, 1.25, 2.5, "Hello", "matched", 1, 1)
        payload = render_srt([cue], with_bom=True)
        self.assertTrue(payload.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"00:00:01,250 --> 00:00:02,500", payload)

    def test_ignores_release_title_cue(self) -> None:
        source = Path(__file__).parent / "fixtures" / "release-title.srt"
        cues = parse_srt(source)
        self.assertEqual(["Actual dialogue."], [cue.text for cue in cues])

    def test_parses_cp1252_without_mistaking_it_for_utf16(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "cp1252.srt"
            source.write_bytes(
                "1\r\n00:00:01,000 --> 00:00:02,000\r\nWait—what?\r\n".encode("cp1252")
            )
            cues = parse_srt(source)
        self.assertEqual(["Wait—what?"], [cue.text for cue in cues])


if __name__ == "__main__":
    unittest.main()
