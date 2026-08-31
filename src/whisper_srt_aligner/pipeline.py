from __future__ import annotations

import hashlib
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from .alignment import align_cues, merge_alignment_results
from .media import extract_audio, media_fingerprint, probe_audio_streams, select_audio_stream
from .models import (
    AlignmentConfig,
    AlignmentResult,
    AudioStream,
    OutputPaths,
    TranscriptionOptions,
)
from .report import build_report_payload, write_html_report, write_json_report
from .subtitles import parse_srt, write_srt
from .transcriber import ProgressCallback, WhisperTranscriber
from .transcript import build_timed_words, load_transcript, write_transcript


def derive_output_paths(
    media: Path | None,
    subtitle: Path,
    output: Path | None = None,
    report_json: Path | None = None,
    transcript: Path | None = None,
) -> OutputPaths:
    base = media.with_suffix("") if media is not None else subtitle.with_suffix("")
    output_subtitle = output or base.with_name(f"{base.name}.aligned.srt")
    report_base = output_subtitle.with_suffix("")
    json_path = report_json or report_base.with_name(f"{report_base.name}.alignment.json")
    html_path = json_path.with_suffix(".html")
    if transcript is None:
        cache_dir = output_subtitle.parent / ".whisper-srt-aligner-cache"
        fingerprint_source = f"{media.resolve() if media else subtitle.resolve()}\0{subtitle.resolve()}"
        digest = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:12]
        transcript = cache_dir / f"{base.name}.{digest}.whisper.json"
    return OutputPaths(
        subtitle=output_subtitle,
        report_json=json_path,
        report_html=html_path,
        transcript=transcript,
    )


def align_transcript(
    transcript: Path,
    subtitle: Path,
    output: Path,
    report_json: Path,
    report_html: Path | None = None,
    with_bom: bool = False,
    metadata: dict[str, Any] | None = None,
    config: AlignmentConfig | None = None,
) -> AlignmentResult:
    segments, transcript_metadata = load_transcript(transcript)
    timed_words = build_timed_words(segments)
    source_cues = parse_srt(subtitle)
    result = align_cues(source_cues, timed_words, config=config)
    write_srt(output, result.cues, with_bom=with_bom)
    report_metadata = {
        "subtitle": str(subtitle),
        "transcript": str(transcript),
        "output": str(output),
        "transcription": transcript_metadata.get("transcription"),
        **(metadata or {}),
    }
    payload = build_report_payload(result, report_metadata)
    write_json_report(report_json, payload)
    write_html_report(report_html or report_json.with_suffix(".html"), payload)
    return result


def align_complete_transcripts(
    primary_transcript: Path,
    supplemental_transcript: Path,
    subtitle: Path,
    output: Path,
    report_json: Path,
    report_html: Path | None = None,
    with_bom: bool = False,
    metadata: dict[str, Any] | None = None,
) -> AlignmentResult:
    primary_segments, primary_metadata = load_transcript(primary_transcript)
    supplemental_segments, supplemental_metadata = load_transcript(supplemental_transcript)
    source_cues = parse_srt(subtitle)
    primary = align_cues(source_cues, build_timed_words(primary_segments))
    supplemental = align_cues(source_cues, build_timed_words(supplemental_segments))
    result = merge_alignment_results(
        source_cues,
        primary,
        supplemental,
        config=AlignmentConfig(infer_unmatched=True),
    )
    write_srt(output, result.cues, with_bom=with_bom)
    report_metadata = {
        "subtitle": str(subtitle),
        "transcript": str(primary_transcript),
        "supplemental_transcript": str(supplemental_transcript),
        "output": str(output),
        "transcription": primary_metadata.get("transcription"),
        "supplemental_transcription": supplemental_metadata.get("transcription"),
        "alignment_mode": "complete",
        **(metadata or {}),
    }
    payload = build_report_payload(result, report_metadata)
    write_json_report(report_json, payload)
    write_html_report(report_html or report_json.with_suffix(".html"), payload)
    return result


def _stream_metadata(stream: AudioStream) -> dict[str, Any]:
    return {
        "relative_index": stream.relative_index,
        "stream_index": stream.stream_index,
        "codec": stream.codec,
        "channels": stream.channels,
        "language": stream.language,
        "title": stream.title,
        "default": stream.default,
    }


def supplemental_transcript_path(transcript: Path) -> Path:
    ending = ".whisper.json"
    if transcript.name.endswith(ending):
        base = transcript.name[: -len(ending)]
        return transcript.with_name(f"{base}.vad{ending}")
    return transcript.with_name(f"{transcript.stem}.vad{transcript.suffix}")


def _transcript_cache_matches(
    transcript: Path,
    fingerprint: dict[str, Any],
    selected: AudioStream,
    options: TranscriptionOptions,
) -> bool:
    if not transcript.exists():
        return False
    _, cached = load_transcript(transcript)
    cached_options = cached.get("transcription") or {}
    return bool(
        cached.get("media") == fingerprint
        and (cached.get("audio_stream") or {}).get("relative_index")
        == selected.relative_index
        and cached_options.get("model") == options.model
        and cached_options.get("device") == options.device
        and cached_options.get("compute_type") == options.compute_type
        and cached_options.get("requested_language") == options.language
        and cached_options.get("beam_size") == options.beam_size
        and cached_options.get("batch_size") == options.batch_size
        and cached_options.get("vad_filter") == options.vad_filter
    )


def _write_audio_transcript(
    audio: Path,
    transcript: Path,
    fingerprint: dict[str, Any],
    selected: AudioStream,
    options: TranscriptionOptions,
    transcriber: WhisperTranscriber,
) -> None:
    payload = transcriber.transcribe(
        audio,
        {
            "media": fingerprint,
            "audio_stream": _stream_metadata(selected),
        },
        options=options,
    )
    write_transcript(transcript, payload)


def transcribe_media(
    media: Path,
    transcript: Path,
    options: TranscriptionOptions,
    audio_language: str | None,
    audio_stream: int | None,
    force: bool = False,
    transcriber: WhisperTranscriber | None = None,
    progress: ProgressCallback | None = None,
) -> tuple[Path, AudioStream]:
    streams = probe_audio_streams(media)
    selected = select_audio_stream(streams, audio_language, audio_stream)
    fingerprint = media_fingerprint(media)
    if not force and _transcript_cache_matches(transcript, fingerprint, selected, options):
        if progress:
            progress(f"Using cached transcript: {transcript}")
        return transcript, selected
    runner = transcriber or WhisperTranscriber(options, progress=progress)
    with tempfile.TemporaryDirectory(prefix="whisper-srt-aligner-") as temp_dir:
        audio = Path(temp_dir) / "audio.mka"
        if progress:
            progress(
                f"Extracting audio stream {selected.relative_index} "
                f"({selected.language or 'und'}, {selected.codec})"
            )
        audio = extract_audio(media, selected, audio)
        _write_audio_transcript(
            audio,
            transcript,
            fingerprint,
            selected,
            options,
            runner,
        )
    return transcript, selected


def transcribe_media_complete(
    media: Path,
    primary_transcript: Path,
    supplemental_transcript: Path,
    options: TranscriptionOptions,
    audio_language: str | None,
    audio_stream: int | None,
    force: bool = False,
    transcriber: WhisperTranscriber | None = None,
    progress: ProgressCallback | None = None,
) -> tuple[Path, Path, AudioStream]:
    primary_options = replace(options, vad_filter=False)
    supplemental_options = replace(options, vad_filter=True)
    streams = probe_audio_streams(media)
    selected = select_audio_stream(streams, audio_language, audio_stream)
    fingerprint = media_fingerprint(media)
    primary_cached = not force and _transcript_cache_matches(
        primary_transcript, fingerprint, selected, primary_options
    )
    supplemental_cached = not force and _transcript_cache_matches(
        supplemental_transcript, fingerprint, selected, supplemental_options
    )
    if primary_cached and progress:
        progress(f"Using cached transcript: {primary_transcript}")
    if supplemental_cached and progress:
        progress(f"Using cached transcript: {supplemental_transcript}")
    if primary_cached and supplemental_cached:
        return primary_transcript, supplemental_transcript, selected

    runner = transcriber or WhisperTranscriber(primary_options, progress=progress)
    with tempfile.TemporaryDirectory(prefix="whisper-srt-aligner-") as temp_dir:
        audio = Path(temp_dir) / "audio.mka"
        if progress:
            progress(
                f"Extracting audio stream {selected.relative_index} "
                f"({selected.language or 'und'}, {selected.codec})"
            )
        audio = extract_audio(media, selected, audio)
        if not primary_cached:
            if progress:
                progress("Complete pass 1/2: Whisper without VAD")
            _write_audio_transcript(
                audio,
                primary_transcript,
                fingerprint,
                selected,
                primary_options,
                runner,
            )
        if not supplemental_cached:
            if progress:
                progress("Complete pass 2/2: Whisper with VAD")
            _write_audio_transcript(
                audio,
                supplemental_transcript,
                fingerprint,
                selected,
                supplemental_options,
                runner,
            )
    return primary_transcript, supplemental_transcript, selected


def sync_media(
    media: Path,
    subtitle: Path,
    paths: OutputPaths,
    options: TranscriptionOptions,
    audio_language: str | None,
    audio_stream: int | None,
    force_transcribe: bool = False,
    with_bom: bool = False,
    transcriber: WhisperTranscriber | None = None,
    progress: ProgressCallback | None = None,
    complete: bool = False,
) -> AlignmentResult:
    if complete:
        supplemental = supplemental_transcript_path(paths.transcript)
        primary_transcript, supplemental_transcript, selected = transcribe_media_complete(
            media=media,
            primary_transcript=paths.transcript,
            supplemental_transcript=supplemental,
            options=options,
            audio_language=audio_language,
            audio_stream=audio_stream,
            force=force_transcribe,
            transcriber=transcriber,
            progress=progress,
        )
        return align_complete_transcripts(
            primary_transcript=primary_transcript,
            supplemental_transcript=supplemental_transcript,
            subtitle=subtitle,
            output=paths.subtitle,
            report_json=paths.report_json,
            report_html=paths.report_html,
            with_bom=with_bom,
            metadata={
                "media": str(media),
                "audio_stream": _stream_metadata(selected),
            },
        )
    transcript, selected = transcribe_media(
        media=media,
        transcript=paths.transcript,
        options=options,
        audio_language=audio_language,
        audio_stream=audio_stream,
        force=force_transcribe,
        transcriber=transcriber,
        progress=progress,
    )
    return align_transcript(
        transcript=transcript,
        subtitle=subtitle,
        output=paths.subtitle,
        report_json=paths.report_json,
        report_html=paths.report_html,
        with_bom=with_bom,
        metadata={
            "media": str(media),
            "audio_stream": _stream_metadata(selected),
        },
    )
