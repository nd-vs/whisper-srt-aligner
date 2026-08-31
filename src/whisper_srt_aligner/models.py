from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SubtitleCue:
    source_index: int
    start: float
    end: float
    text: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class TimedWord:
    token: str
    start: float
    end: float
    probability: float = 0.0
    original: str = ""


@dataclass
class AlignedCue:
    source_index: int
    source_start: float
    source_end: float
    start: float
    end: float
    text: str
    status: str
    matched_tokens: int
    total_tokens: int
    strong_matches: int = 0

    @property
    def coverage(self) -> float:
        return self.matched_tokens / max(1, self.total_tokens)


@dataclass(frozen=True)
class AlignmentConfig:
    minimum_coverage: float = 0.4
    maximum_neighbor_distance: int = 2
    maximum_rescue_gap: float = 8.0
    minimum_duration: float = 0.35
    infer_unmatched: bool = False
    minimum_inference_scale: float = 0.5
    maximum_inference_scale: float = 1.5
    maximum_inference_cues: int = 8
    maximum_inference_source_span: float = 120.0


@dataclass
class AlignmentResult:
    cues: list[AlignedCue]
    dropped: list[SubtitleCue]
    summary: dict[str, Any]


@dataclass(frozen=True)
class AudioStream:
    relative_index: int
    stream_index: int
    codec: str
    channels: int
    language: str | None
    title: str | None
    default: bool


@dataclass(frozen=True)
class TranscriptionOptions:
    model: str = "large-v3"
    device: str = "auto"
    compute_type: str = "default"
    language: str | None = "en"
    beam_size: int = 5
    batch_size: int = 8
    vad_filter: bool = True


@dataclass(frozen=True)
class OutputPaths:
    subtitle: Path
    report_json: Path
    report_html: Path
    transcript: Path
