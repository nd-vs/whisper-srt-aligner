from __future__ import annotations

import re
from pathlib import Path

from .models import AlignedCue, SubtitleCue
from .text import tokenize, visible_text


TIMING_PATTERN = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{3})"
)
SUPPORTED_ENCODINGS = ("utf-8-sig", "utf-16", "utf-8", "cp1252", "cp1251", "latin-1")
IGNORED_RELEASE_CUE_PATTERNS = (
    re.compile(r"\bS\d{1,2}E\d{1,3}\b", re.IGNORECASE),
    re.compile(r"^\s*(?:https?://|www\.)", re.IGNORECASE),
)


def read_text(path: Path) -> str:
    payload = path.read_bytes()
    for encoding in SUPPORTED_ENCODINGS:
        try:
            return payload.decode(encoding)
        except UnicodeError:
            continue
    raise ValueError(f"Cannot decode subtitle: {path}")


def parse_timestamp(value: str) -> float:
    hours, minutes, rest = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def format_timestamp(value: float) -> str:
    total_ms = int(round(max(0.0, value) * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def parse_srt(path: Path) -> list[SubtitleCue]:
    text = read_text(path).replace("\r\n", "\n").replace("\r", "\n")
    cues: list[SubtitleCue] = []
    fallback_index = 1
    for block in re.split(r"\n{2,}", text.strip()):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        timing_position = next(
            (position for position, line in enumerate(lines) if TIMING_PATTERN.search(line)),
            None,
        )
        if timing_position is None:
            continue
        timing = TIMING_PATTERN.search(lines[timing_position])
        if timing is None:
            continue
        source_index = fallback_index
        if timing_position > 0 and lines[timing_position - 1].isdigit():
            source_index = int(lines[timing_position - 1])
        cue_text = "\n".join(lines[timing_position + 1 :]).strip()
        cue_tokens = tuple(tokenize(cue_text))
        if any(pattern.search(visible_text(cue_text)) for pattern in IGNORED_RELEASE_CUE_PATTERNS):
            fallback_index += 1
            continue
        if cue_text and cue_tokens:
            cues.append(
                SubtitleCue(
                    source_index=source_index,
                    start=parse_timestamp(timing.group("start")),
                    end=parse_timestamp(timing.group("end")),
                    text=cue_text,
                    tokens=cue_tokens,
                )
            )
        fallback_index += 1
    return cues


def render_srt(cues: list[AlignedCue], with_bom: bool = False) -> bytes:
    lines: list[str] = []
    for index, cue in enumerate(cues, 1):
        lines.extend(
            [
                str(index),
                f"{format_timestamp(cue.start)} --> {format_timestamp(cue.end)}",
                cue.text,
                "",
            ]
        )
    encoding = "utf-8-sig" if with_bom else "utf-8"
    return "\n".join(lines).encode(encoding)


def write_srt(path: Path, cues: list[AlignedCue], with_bom: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_srt(cues, with_bom=with_bom))
