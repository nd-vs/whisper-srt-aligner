import unittest

from whisper_srt_aligner.alignment import align_cues, merge_alignment_results
from whisper_srt_aligner.models import (
    AlignedCue,
    AlignmentConfig,
    AlignmentResult,
    SubtitleCue,
    TimedWord,
)
from whisper_srt_aligner.text import tokenize


def cue(index: int, start: float, end: float, text: str) -> SubtitleCue:
    return SubtitleCue(index, start, end, text, tuple(tokenize(text)))


def words(*items: tuple[str, float, float]) -> list[TimedWord]:
    return [TimedWord(tokenize(text)[0], start, end, 1.0, text) for text, start, end in items]


class AlignmentTest(unittest.TestCase):
    def test_uses_whisper_times_and_original_text(self) -> None:
        source = [
            cue(1, 10.0, 12.0, "<i>Hello there.</i>"),
            cue(2, 12.2, 14.0, "Welcome home!"),
        ]
        transcript = words(
            ("hello", 1.0, 1.3),
            ("there", 1.35, 1.7),
            ("welcome", 2.1, 2.45),
            ("home", 2.5, 2.8),
        )
        result = align_cues(source, transcript)
        self.assertEqual(["<i>Hello there.</i>", "Welcome home!"], [item.text for item in result.cues])
        self.assertLess(result.cues[0].start, 1.0)
        self.assertGreater(result.cues[1].end, 2.8)
        self.assertEqual(0, result.summary["dropped_cues"])

    def test_drops_phrase_absent_from_audio(self) -> None:
        source = [
            cue(1, 10.0, 11.0, "Hello there."),
            cue(2, 11.1, 12.0, "This phrase is missing."),
            cue(3, 12.1, 13.0, "Welcome home."),
        ]
        transcript = words(
            ("hello", 1.0, 1.2),
            ("there", 1.3, 1.5),
            ("welcome", 2.0, 2.3),
            ("home", 2.4, 2.6),
        )
        result = align_cues(source, transcript)
        self.assertEqual(["Hello there.", "Welcome home."], [item.text for item in result.cues])
        self.assertEqual("This phrase is missing.", result.dropped[0].text)

    def test_does_not_join_matches_from_distant_scenes(self) -> None:
        source = [cue(1, 1.0, 3.0, "alpha beta gamma delta")]
        transcript = words(
            ("alpha", 1.0, 1.2),
            ("beta", 1.3, 1.5),
            ("noise", 20.0, 20.2),
            ("gamma", 40.0, 40.2),
            ("delta", 40.3, 40.5),
        )
        result = align_cues(source, transcript)
        self.assertEqual(1, len(result.cues))
        self.assertLess(result.cues[0].end, 5.0)

    def test_output_has_no_overlaps(self) -> None:
        source = [
            cue(1, 1.0, 2.0, "one two"),
            cue(2, 2.1, 3.0, "three four"),
        ]
        transcript = words(
            ("one", 1.0, 1.5),
            ("two", 1.5, 2.0),
            ("three", 2.0, 2.2),
            ("four", 2.2, 2.4),
        )
        result = align_cues(source, transcript)
        self.assertLess(result.cues[0].end, result.cues[1].start)

    def test_infers_internal_unmatched_cue_between_confirmed_anchors(self) -> None:
        source = [
            cue(1, 10.0, 11.0, "alpha beta"),
            cue(2, 12.0, 13.0, "quiet line"),
            cue(3, 14.0, 15.0, "gamma delta"),
        ]
        transcript = words(
            ("alpha", 20.0, 20.3),
            ("beta", 20.4, 20.7),
            ("gamma", 24.0, 24.3),
            ("delta", 24.4, 24.7),
        )
        result = align_cues(source, transcript, AlignmentConfig(infer_unmatched=True))
        self.assertEqual(3, len(result.cues))
        self.assertEqual("inferred", result.cues[1].status)
        self.assertEqual("quiet line", result.cues[1].text)

    def test_does_not_infer_unbracketed_suffix(self) -> None:
        source = [
            cue(1, 10.0, 11.0, "alpha beta"),
            cue(2, 12.0, 13.0, "unconfirmed ending"),
        ]
        transcript = words(("alpha", 20.0, 20.3), ("beta", 20.4, 20.7))
        result = align_cues(source, transcript, AlignmentConfig(infer_unmatched=True))
        self.assertEqual(["alpha beta"], [item.text for item in result.cues])
        self.assertEqual("unconfirmed ending", result.dropped[0].text)

    def test_does_not_infer_across_a_compressed_cut(self) -> None:
        source = [
            cue(1, 1.0, 2.0, "alpha beta"),
            cue(2, 10.0, 11.0, "removed scene"),
            cue(3, 20.0, 21.0, "gamma delta"),
        ]
        transcript = words(
            ("alpha", 1.0, 1.2),
            ("beta", 1.3, 1.5),
            ("gamma", 3.0, 3.2),
            ("delta", 3.3, 3.5),
        )
        result = align_cues(source, transcript, AlignmentConfig(infer_unmatched=True))
        self.assertEqual(["alpha beta", "gamma delta"], [item.text for item in result.cues])

    def test_infers_a_quiet_cue_inside_a_long_coherent_scene(self) -> None:
        source = [
            cue(1, 10.0, 12.0, "alpha beta"),
            cue(2, 45.0, 47.0, "quiet line"),
            cue(3, 80.0, 82.0, "gamma delta"),
        ]
        transcript = words(
            ("alpha", 20.0, 20.3),
            ("beta", 20.4, 20.7),
            ("gamma", 90.0, 90.3),
            ("delta", 90.4, 90.7),
        )
        result = align_cues(source, transcript, AlignmentConfig(infer_unmatched=True))
        self.assertEqual(3, len(result.cues))
        self.assertEqual("inferred", result.cues[1].status)

    def test_supplemental_transcript_fills_primary_gap(self) -> None:
        source = [
            cue(1, 10.0, 11.0, "alpha beta"),
            cue(2, 12.0, 13.0, "quiet line"),
            cue(3, 14.0, 15.0, "gamma delta"),
        ]
        primary = align_cues(
            source,
            words(
                ("alpha", 20.0, 20.3),
                ("beta", 20.4, 20.7),
                ("gamma", 24.0, 24.3),
                ("delta", 24.4, 24.7),
            ),
        )
        supplemental = align_cues(
            source,
            words(
                ("alpha", 20.0, 20.3),
                ("beta", 20.4, 20.7),
                ("quiet", 22.0, 22.3),
                ("line", 22.4, 22.7),
                ("gamma", 24.0, 24.3),
                ("delta", 24.4, 24.7),
            ),
        )
        result = merge_alignment_results(source, primary, supplemental)
        self.assertEqual(3, len(result.cues))
        self.assertEqual("supplemented", result.cues[1].status)
        self.assertEqual(1, result.summary["supplemented_cues"])

    def test_rejects_supplemental_match_outside_neighbor_timeline(self) -> None:
        source = [
            cue(1, 10.0, 11.0, "alpha beta"),
            cue(2, 12.0, 13.0, "repeated word"),
            cue(3, 14.0, 15.0, "gamma delta"),
        ]
        primary = align_cues(
            source,
            words(
                ("alpha", 20.0, 20.3),
                ("beta", 20.4, 20.7),
                ("gamma", 24.0, 24.3),
                ("delta", 24.4, 24.7),
            ),
        )
        misplaced = AlignedCue(
            source_index=2,
            source_start=12.0,
            source_end=13.0,
            start=30.0,
            end=30.5,
            text="repeated word",
            status="matched",
            matched_tokens=2,
            total_tokens=2,
            strong_matches=2,
        )
        supplemental = AlignmentResult(
            cues=[misplaced],
            dropped=[],
            summary={"matched_reference_tokens": 2},
        )

        result = merge_alignment_results(source, primary, supplemental)

        middle = next(item for item in result.cues if item.source_index == 2)
        self.assertEqual("inferred", middle.status)
        self.assertLess(middle.end, result.cues[2].start)


if __name__ == "__main__":
    unittest.main()
