from __future__ import annotations

import os
import site
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .models import TranscriptionOptions
from .transcript import TRANSCRIPT_SCHEMA_VERSION


ProgressCallback = Callable[[str], None]
_DLL_DIRECTORY_HANDLES: list[Any] = []


def prepare_windows_nvidia_runtime() -> None:
    if sys.platform != "win32":
        return
    roots: list[Path] = []
    for package_root in [*site.getsitepackages(), site.getusersitepackages()]:
        nvidia_root = Path(package_root) / "nvidia"
        if nvidia_root.is_dir():
            roots.extend(path for path in nvidia_root.glob("*/bin") if path.is_dir())
    if not roots:
        return
    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join([*(str(path) for path in roots), current_path])
    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is not None:
        for path in roots:
            _DLL_DIRECTORY_HANDLES.append(add_dll_directory(str(path)))


class WhisperTranscriber:
    def __init__(
        self,
        options: TranscriptionOptions,
        progress: ProgressCallback | None = None,
    ) -> None:
        self.options = options
        self.progress = progress or (lambda _: None)
        self._model: Any = None
        self._pipeline: Any = None

    def _load_backend(self) -> tuple[Any, Any]:
        if self._model is not None and self._pipeline is not None:
            return self._model, self._pipeline
        prepare_windows_nvidia_runtime()
        try:
            from faster_whisper import BatchedInferencePipeline, WhisperModel
        except ImportError as error:
            raise RuntimeError(
                "faster-whisper is not installed; install the package normally or use "
                "the 'align' command with an existing transcript JSON"
            ) from error
        self.progress(
            f"Loading Whisper {self.options.model} "
            f"({self.options.device}, {self.options.compute_type})"
        )
        self._model = WhisperModel(
            self.options.model,
            device=self.options.device,
            compute_type=self.options.compute_type,
        )
        self._pipeline = BatchedInferencePipeline(model=self._model)
        return self._model, self._pipeline

    def transcribe(
        self,
        audio: Path,
        metadata: dict[str, Any],
        options: TranscriptionOptions | None = None,
    ) -> dict[str, Any]:
        effective_options = options or self.options
        backend_identity = (
            effective_options.model,
            effective_options.device,
            effective_options.compute_type,
        )
        loaded_identity = (
            self.options.model,
            self.options.device,
            self.options.compute_type,
        )
        if backend_identity != loaded_identity:
            raise ValueError(
                "A reused WhisperTranscriber requires the same model, device, and compute type"
            )
        model, pipeline = self._load_backend()
        common_options = {
            "language": effective_options.language,
            "beam_size": effective_options.beam_size,
            "vad_filter": effective_options.vad_filter,
            "word_timestamps": True,
            "condition_on_previous_text": False,
        }
        if effective_options.vad_filter:
            segments_iterator, info = pipeline.transcribe(
                str(audio),
                batch_size=effective_options.batch_size,
                **common_options,
            )
        else:
            segments_iterator, info = model.transcribe(str(audio), **common_options)
        segments: list[dict[str, Any]] = []
        for index, segment in enumerate(segments_iterator, 1):
            words = [
                {
                    "word": word.word,
                    "start": round(float(word.start), 3),
                    "end": round(float(word.end), 3),
                    "probability": round(float(word.probability), 4),
                }
                for word in (segment.words or [])
                if word.start is not None and word.end is not None
            ]
            segments.append(
                {
                    "start": round(float(segment.start), 3),
                    "end": round(float(segment.end), 3),
                    "text": segment.text.strip(),
                    "words": words,
                }
            )
            if index % 25 == 0:
                self.progress(f"Whisper: {index} segments, {segment.end / 60:.1f} min")
        return {
            "schema_version": TRANSCRIPT_SCHEMA_VERSION,
            **metadata,
            "transcription": {
                "model": effective_options.model,
                "device": effective_options.device,
                "compute_type": effective_options.compute_type,
                "requested_language": effective_options.language,
                "detected_language": getattr(info, "language", None),
                "language_probability": getattr(info, "language_probability", None),
                "beam_size": effective_options.beam_size,
                "batch_size": effective_options.batch_size,
                "vad_filter": effective_options.vad_filter,
            },
            "segments": segments,
        }
