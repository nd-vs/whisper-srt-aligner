from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .batch import discover_pairs
from .media import probe_audio_streams
from .models import AlignmentConfig, TranscriptionOptions
from .pipeline import (
    align_complete_transcripts,
    align_transcript,
    derive_output_paths,
    supplemental_transcript_path,
    sync_media,
    transcribe_media,
)
from .transcriber import WhisperTranscriber


DEFAULT_MODEL = "large-v3"
DEFAULT_AUDIO_LANGUAGE = "eng"
DEFAULT_TRANSCRIPT_LANGUAGE = "en"


def _path(value: str) -> Path:
    return Path(value).expanduser()


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")


def _ensure_writable_output(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {path}. Use --overwrite to replace it.")


def _progress(message: str) -> None:
    print(message, flush=True)


def _transcription_options(args: argparse.Namespace) -> TranscriptionOptions:
    return TranscriptionOptions(
        model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        beam_size=args.beam_size,
        batch_size=args.batch_size,
        vad_filter=not args.no_vad,
    )


def _add_transcription_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=DEFAULT_MODEL, help="faster-whisper model name")
    parser.add_argument("--device", default="auto", help="auto, cpu, or cuda")
    parser.add_argument("--compute-type", default="default", help="default, float16, int8, ...")
    parser.add_argument("--language", default=DEFAULT_TRANSCRIPT_LANGUAGE, help="spoken language")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--no-vad", action="store_true", help="disable faster-whisper VAD")
    parser.add_argument("--audio-language", default=DEFAULT_AUDIO_LANGUAGE)
    parser.add_argument(
        "--audio-stream",
        type=int,
        help="zero-based audio stream index, as shown by the inspect command",
    )
    parser.add_argument("--force-transcribe", action="store_true", help="ignore transcript cache")


def _print_result(result, paths) -> None:
    summary = result.summary
    print(
        f"Aligned {summary['output_cues']}/{summary['source_cues']} cues; "
        f"dropped {summary['dropped_cues']}; rescued {summary['rescued_cues']}; "
        f"supplemented {summary['supplemented_cues']}; "
        f"inferred {summary['inferred_cues']}; "
        f"token coverage {summary['token_coverage']:.1%}"
    )
    print(f"Subtitle: {paths.subtitle}")
    print(f"JSON report: {paths.report_json}")
    print(f"HTML report: {paths.report_html}")


def _run_align(args: argparse.Namespace) -> int:
    _require_file(args.transcript, "Transcript")
    _require_file(args.subtitle, "Subtitle")
    if args.supplement_transcript is not None:
        _require_file(args.supplement_transcript, "Supplemental transcript")
    paths = derive_output_paths(
        media=None,
        subtitle=args.subtitle,
        output=args.output,
        report_json=args.report,
        transcript=args.transcript,
    )
    _ensure_writable_output(paths.subtitle, args.overwrite)
    if args.supplement_transcript is not None:
        result = align_complete_transcripts(
            primary_transcript=args.transcript,
            supplemental_transcript=args.supplement_transcript,
            subtitle=args.subtitle,
            output=paths.subtitle,
            report_json=paths.report_json,
            report_html=paths.report_html,
            with_bom=args.bom,
        )
    else:
        result = align_transcript(
            transcript=args.transcript,
            subtitle=args.subtitle,
            output=paths.subtitle,
            report_json=paths.report_json,
            report_html=paths.report_html,
            with_bom=args.bom,
            config=AlignmentConfig(infer_unmatched=args.infer_unmatched),
        )
    _print_result(result, paths)
    return 0


def _run_sync(args: argparse.Namespace) -> int:
    _require_file(args.media, "Media")
    _require_file(args.subtitle, "Subtitle")
    paths = derive_output_paths(
        media=args.media,
        subtitle=args.subtitle,
        output=args.output,
        report_json=args.report,
        transcript=args.transcript_cache,
    )
    _ensure_writable_output(paths.subtitle, args.overwrite)
    options = _transcription_options(args)
    result = sync_media(
        media=args.media,
        subtitle=args.subtitle,
        paths=paths,
        options=options,
        audio_language=args.audio_language,
        audio_stream=args.audio_stream,
        force_transcribe=args.force_transcribe,
        with_bom=args.bom,
        progress=_progress,
        complete=args.complete,
    )
    _print_result(result, paths)
    print(f"Transcript cache: {paths.transcript}")
    if args.complete:
        print(f"Supplemental transcript cache: {supplemental_transcript_path(paths.transcript)}")
    return 0


def _run_transcribe(args: argparse.Namespace) -> int:
    _require_file(args.media, "Media")
    options = _transcription_options(args)
    transcript, stream = transcribe_media(
        media=args.media,
        transcript=args.output,
        options=options,
        audio_language=args.audio_language,
        audio_stream=args.audio_stream,
        force=args.force_transcribe,
        progress=_progress,
    )
    print(
        f"Transcript: {transcript}\n"
        f"Audio stream: {stream.relative_index} ({stream.language or 'und'}, {stream.codec})"
    )
    return 0


def _run_inspect(args: argparse.Namespace) -> int:
    _require_file(args.media, "Media")
    streams = probe_audio_streams(args.media)
    if args.json:
        print(json.dumps([stream.__dict__ for stream in streams], indent=2, ensure_ascii=False))
        return 0
    print("INDEX  STREAM  LANG  DEFAULT  CODEC  CHANNELS  TITLE")
    for stream in streams:
        print(
            f"{stream.relative_index:<5}  {stream.stream_index:<6}  "
            f"{(stream.language or 'und'):<4}  {str(stream.default):<7}  "
            f"{stream.codec:<5}  {stream.channels:<8}  {stream.title or ''}"
        )
    return 0


def _run_batch(args: argparse.Namespace) -> int:
    if not args.folder.is_dir():
        raise ValueError(f"Folder does not exist: {args.folder}")
    pairs, errors = discover_pairs(
        args.folder,
        video_glob=args.video_glob,
        subtitle_glob=args.subtitle_glob,
        recursive=args.recursive,
    )
    for error in errors:
        print(f"warning: {error}", file=sys.stderr)
    if not pairs:
        raise ValueError("No unambiguous video/subtitle pairs found")
    for pair in pairs:
        print(f"{pair.key}: {pair.media.name} <- {pair.subtitle.name}")
    if args.dry_run:
        return 1 if errors else 0

    options = _transcription_options(args)
    transcriber = WhisperTranscriber(options, progress=_progress)
    failed = len(errors)
    for pair in pairs:
        output_folder = args.output_dir or pair.media.parent
        output = output_folder / f"{pair.key}.aligned.srt"
        report = output_folder / f"{pair.key}.alignment.json"
        transcript = output_folder / ".whisper-srt-aligner-cache" / f"{pair.key}.whisper.json"
        paths = derive_output_paths(
            media=pair.media,
            subtitle=pair.subtitle,
            output=output,
            report_json=report,
            transcript=transcript,
        )
        try:
            _ensure_writable_output(paths.subtitle, args.overwrite)
            print(f"[{pair.key}] starting")
            result = sync_media(
                media=pair.media,
                subtitle=pair.subtitle,
                paths=paths,
                options=options,
                audio_language=args.audio_language,
                audio_stream=args.audio_stream,
                force_transcribe=args.force_transcribe,
                with_bom=args.bom,
                transcriber=transcriber,
                progress=lambda message, key=pair.key: _progress(f"[{key}] {message}"),
                complete=args.complete,
            )
            _print_result(result, paths)
        except Exception as error:
            failed += 1
            print(f"[{pair.key}] error: {error}", file=sys.stderr)
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whisper-srt-align",
        description="Retain original SRT text but rebuild its timing from Whisper word timestamps.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    align = subparsers.add_parser("align", help="align an SRT using an existing Whisper JSON")
    align.add_argument("transcript", type=_path)
    align.add_argument("subtitle", type=_path)
    align.add_argument("-o", "--output", type=_path)
    align.add_argument("--report", type=_path)
    align.add_argument("--overwrite", action="store_true")
    align.add_argument("--bom", action="store_true", help="write UTF-8 BOM")
    align.add_argument(
        "--supplement-transcript",
        type=_path,
        help="merge a second Whisper transcript and infer only bracketed gaps",
    )
    align.add_argument(
        "--infer-unmatched",
        action="store_true",
        help="infer unmatched internal cues between confirmed anchors",
    )
    align.set_defaults(handler=_run_align)

    sync = subparsers.add_parser("sync", help="transcribe media and align one SRT")
    sync.add_argument("media", type=_path)
    sync.add_argument("subtitle", type=_path)
    sync.add_argument("-o", "--output", type=_path)
    sync.add_argument("--report", type=_path)
    sync.add_argument("--transcript-cache", type=_path)
    sync.add_argument("--overwrite", action="store_true")
    sync.add_argument("--bom", action="store_true", help="write UTF-8 BOM")
    sync.add_argument(
        "--complete",
        action="store_true",
        help="combine Whisper passes without and with VAD, then infer bracketed gaps",
    )
    _add_transcription_arguments(sync)
    sync.set_defaults(handler=_run_sync)

    transcribe = subparsers.add_parser("transcribe", help="create a reusable Whisper JSON")
    transcribe.add_argument("media", type=_path)
    transcribe.add_argument("-o", "--output", type=_path, required=True)
    _add_transcription_arguments(transcribe)
    transcribe.set_defaults(handler=_run_transcribe)

    inspect = subparsers.add_parser("inspect", help="show audio streams")
    inspect.add_argument("media", type=_path)
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(handler=_run_inspect)

    batch = subparsers.add_parser("batch", help="align season-style episode pairs")
    batch.add_argument("folder", type=_path)
    batch.add_argument("--video-glob", default="*.mkv")
    batch.add_argument("--subtitle-glob", default="*.srt")
    batch.add_argument("--output-dir", type=_path)
    batch.add_argument("--recursive", action="store_true")
    batch.add_argument("--dry-run", action="store_true")
    batch.add_argument("--overwrite", action="store_true")
    batch.add_argument("--bom", action="store_true", help="write UTF-8 BOM")
    batch.add_argument(
        "--complete",
        action="store_true",
        help="combine Whisper passes without and with VAD, then infer bracketed gaps",
    )
    _add_transcription_arguments(batch)
    batch.set_defaults(handler=_run_batch)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
