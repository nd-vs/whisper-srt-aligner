from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


EPISODE_PATTERNS = (
    re.compile(r"[Ss](\d{1,2})[\s._-]*[Ee](\d{1,3})"),
    re.compile(r"(?<!\d)(\d{1,2})x(\d{2,3})(?!\d)"),
)


@dataclass(frozen=True)
class MediaSubtitlePair:
    key: str
    media: Path
    subtitle: Path


def episode_key(path: Path) -> str | None:
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(path.name)
        if match:
            return f"S{int(match.group(1)):02}E{int(match.group(2)):02}"
    return None


def _discover(folder: Path, pattern: str, recursive: bool) -> list[Path]:
    iterator = folder.rglob(pattern) if recursive else folder.glob(pattern)
    return sorted(path for path in iterator if path.is_file())


def discover_pairs(
    folder: Path,
    video_glob: str,
    subtitle_glob: str,
    recursive: bool = False,
) -> tuple[list[MediaSubtitlePair], list[str]]:
    videos = _discover(folder, video_glob, recursive)
    subtitles = [
        path
        for path in _discover(folder, subtitle_glob, recursive)
        if ".aligned." not in path.name.casefold()
    ]
    videos_by_key: dict[str, list[Path]] = {}
    subtitles_by_key: dict[str, list[Path]] = {}
    for video in videos:
        key = episode_key(video)
        if key:
            videos_by_key.setdefault(key, []).append(video)
    for subtitle in subtitles:
        key = episode_key(subtitle)
        if key:
            subtitles_by_key.setdefault(key, []).append(subtitle)

    pairs: list[MediaSubtitlePair] = []
    errors: list[str] = []
    keys = sorted(set(videos_by_key) | set(subtitles_by_key))
    for key in keys:
        matching_videos = videos_by_key.get(key, [])
        matching_subtitles = subtitles_by_key.get(key, [])
        if len(matching_videos) != 1 or len(matching_subtitles) != 1:
            errors.append(
                f"{key}: expected one video and one subtitle, got "
                f"{len(matching_videos)} video(s) and {len(matching_subtitles)} subtitle(s)"
            )
            continue
        pairs.append(MediaSubtitlePair(key, matching_videos[0], matching_subtitles[0]))
    if not keys and len(videos) == 1 and len(subtitles) == 1:
        pairs.append(MediaSubtitlePair(videos[0].stem, videos[0], subtitles[0]))
    return pairs, errors
