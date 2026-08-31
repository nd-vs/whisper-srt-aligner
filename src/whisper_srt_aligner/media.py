from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .models import AudioStream


LANGUAGE_ALIASES = {
    "en": {"en", "eng", "english"},
    "eng": {"en", "eng", "english"},
    "ru": {"ru", "rus", "russian"},
    "rus": {"ru", "rus", "russian"},
}


def require_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"Required executable is not on PATH: {name}")
    return executable


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def probe_audio_streams(media: Path) -> list[AudioStream]:
    ffprobe = require_executable("ffprobe")
    result = _run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index,codec_name,channels:stream_tags=language,title:stream_disposition=default",
            "-of",
            "json",
            str(media),
        ]
    )
    payload = json.loads(result.stdout)
    streams: list[AudioStream] = []
    for relative_index, stream in enumerate(payload.get("streams", [])):
        tags = stream.get("tags") or {}
        disposition = stream.get("disposition") or {}
        streams.append(
            AudioStream(
                relative_index=relative_index,
                stream_index=int(stream["index"]),
                codec=str(stream.get("codec_name") or "unknown"),
                channels=int(stream.get("channels") or 0),
                language=tags.get("language"),
                title=tags.get("title"),
                default=bool(disposition.get("default", 0)),
            )
        )
    if not streams:
        raise RuntimeError(f"No audio streams found: {media}")
    return streams


def select_audio_stream(
    streams: list[AudioStream],
    language: str | None,
    relative_index: int | None = None,
) -> AudioStream:
    if relative_index is not None:
        for stream in streams:
            if stream.relative_index == relative_index:
                return stream
        available = ", ".join(str(stream.relative_index) for stream in streams)
        raise ValueError(f"Audio stream {relative_index} not found; available: {available}")
    if language:
        aliases = LANGUAGE_ALIASES.get(language.casefold(), {language.casefold()})
        matching = [
            stream
            for stream in streams
            if (stream.language or "").casefold() in aliases
            or (stream.title or "").casefold() in aliases
        ]
        if matching:
            return sorted(matching, key=lambda stream: (not stream.default, stream.relative_index))[0]
        if len(streams) > 1:
            available = ", ".join(
                f"{stream.relative_index}:{stream.language or 'und'}" for stream in streams
            )
            raise ValueError(
                f"No audio stream matches language '{language}'; available: {available}. "
                "Use --audio-stream to choose explicitly."
            )
    return sorted(streams, key=lambda stream: (not stream.default, stream.relative_index))[0]


def extract_audio(media: Path, stream: AudioStream, output: Path) -> Path:
    ffmpeg = require_executable("ffmpeg")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        _run(
            [
                ffmpeg,
                "-nostdin",
                "-y",
                "-v",
                "error",
                "-i",
                str(media),
                "-map",
                f"0:{stream.stream_index}",
                "-vn",
                "-c:a",
                "copy",
                str(output),
            ]
        )
        return output
    except subprocess.CalledProcessError:
        fallback = output.with_suffix(".wav")
        try:
            _run(
                [
                    ffmpeg,
                    "-nostdin",
                    "-y",
                    "-v",
                    "error",
                    "-i",
                    str(media),
                    "-map",
                    f"0:{stream.stream_index}",
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(fallback),
                ]
            )
            return fallback
        except subprocess.CalledProcessError as error:
            details = (error.stderr or error.stdout or str(error)).strip()
            raise RuntimeError(f"FFmpeg audio extraction failed: {details}") from error


def media_fingerprint(media: Path) -> dict[str, int | str]:
    stat = media.stat()
    return {
        "path": str(media.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
