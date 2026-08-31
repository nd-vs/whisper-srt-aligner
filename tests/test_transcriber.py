import unittest
from pathlib import Path
from types import SimpleNamespace

from whisper_srt_aligner.models import TranscriptionOptions
from whisper_srt_aligner.transcriber import WhisperTranscriber


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def transcribe(self, _audio: str, **options):
        self.calls.append(options)
        word = SimpleNamespace(word=" hello", start=1.0, end=1.4, probability=0.9)
        segment = SimpleNamespace(start=1.0, end=1.4, text=" hello", words=[word])
        info = SimpleNamespace(language="en", language_probability=1.0)
        return iter([segment]), info


class TranscriberTest(unittest.TestCase):
    def test_no_vad_uses_plain_model_without_batch_size(self) -> None:
        model = FakeBackend()
        pipeline = FakeBackend()
        transcriber = WhisperTranscriber(TranscriptionOptions(vad_filter=False))
        transcriber._model = model
        transcriber._pipeline = pipeline
        payload = transcriber.transcribe(Path("audio.mka"), {})
        self.assertEqual(1, len(model.calls))
        self.assertEqual([], pipeline.calls)
        self.assertNotIn("batch_size", model.calls[0])
        self.assertFalse(model.calls[0]["vad_filter"])
        self.assertEqual(" hello", payload["segments"][0]["words"][0]["word"])

    def test_vad_uses_batched_pipeline(self) -> None:
        model = FakeBackend()
        pipeline = FakeBackend()
        transcriber = WhisperTranscriber(TranscriptionOptions(vad_filter=True, batch_size=4))
        transcriber._model = model
        transcriber._pipeline = pipeline
        transcriber.transcribe(Path("audio.mka"), {})
        self.assertEqual([], model.calls)
        self.assertEqual(4, pipeline.calls[0]["batch_size"])

    def test_reuses_model_for_vad_and_no_vad_passes(self) -> None:
        model = FakeBackend()
        pipeline = FakeBackend()
        base = TranscriptionOptions(vad_filter=False)
        transcriber = WhisperTranscriber(base)
        transcriber._model = model
        transcriber._pipeline = pipeline
        transcriber.transcribe(Path("audio.mka"), {}, options=base)
        transcriber.transcribe(
            Path("audio.mka"),
            {},
            options=TranscriptionOptions(vad_filter=True, batch_size=3),
        )
        self.assertEqual(1, len(model.calls))
        self.assertEqual(1, len(pipeline.calls))
        self.assertEqual(3, pipeline.calls[0]["batch_size"])


if __name__ == "__main__":
    unittest.main()
