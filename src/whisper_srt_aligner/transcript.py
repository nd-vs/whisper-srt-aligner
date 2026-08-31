from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import TimedWord
from .text import tokenize


TRANSCRIPT_SCHEMA_VERSION = 1


def load_transcript(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload, {"schema_version": 0, "source": "legacy-list"}
    if not isinstance(payload, dict) or not isinstance(payload.get("segments"), list):
        raise ValueError(f"Unsupported transcript JSON: {path}")
    return payload["segments"], payload


def build_timed_words(segments: list[dict[str, Any]]) -> list[TimedWord]:
    words: list[TimedWord] = []
    for segment in segments:
        for item in segment.get("words", []):
            original = str(item.get("word", ""))
            tokens = tokenize(original)
            for token in tokens:
                words.append(
                    TimedWord(
                        token=token,
                        start=float(item["start"]),
                        end=float(item["end"]),
                        probability=float(item.get("probability", 0.0)),
                        original=original,
                    )
                )
    return words


def write_transcript(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
