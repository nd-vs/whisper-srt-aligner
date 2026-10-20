"""GUI job boundary: validation, staged outputs, and the existing engine."""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from .media import probe_audio_streams, require_executable
from .models import TranscriptionOptions
from .pipeline import derive_output_paths, sync_media
from .report import write_html_report, write_json_report
from .subtitles import parse_srt


def job_paths(config: dict):
    media = Path(config['media']).expanduser().resolve()
    subtitle = Path(config['subtitle']).expanduser().resolve()
    output = Path(config['output']).expanduser().resolve()
    if not media.is_file():
        raise ValueError(f'Media file not found: {media}')
    if not subtitle.is_file() or subtitle.suffix.lower() != '.srt':
        raise ValueError(f'Choose an existing SRT file: {subtitle}')
    if output.suffix.lower() != '.srt':
        raise ValueError('The output filename must end in .srt')
    paths = derive_output_paths(media, subtitle, output)
    targets = (paths.subtitle, paths.report_json, paths.report_html)
    inputs = (media, subtitle)
    for target in targets:
        if any(target == original or (target.exists() and target.samefile(original)) for original in inputs):
            raise ValueError('Output files must be different from the original inputs')
        if target.exists() and not config.get('overwrite', False):
            raise FileExistsError(f'Output already exists: {target}')
        if target.exists() and not target.is_file():
            raise ValueError(f'Output is not a regular file: {target}')
    return media, subtitle, paths


def publish_outputs(pairs: list[tuple[Path, Path]], backup_dir: Path, overwrite: bool) -> None:
    """Replace a set of staged files; restore previous outputs on I/O failure."""
    backups = []
    published = []
    try:
        for index, (source, target) in enumerate(pairs):
            if target.exists():
                if not overwrite:
                    raise FileExistsError(f'Output already exists: {target}')
                backup = backup_dir / f'previous-{index}'
                target.replace(backup)
                backups.append((backup, target))
            # A hard link provides no-clobber publication, including a late collision.
            os.link(source, target)
            published.append(target)
    except Exception:
        for target in reversed(published):
            target.unlink(missing_ok=True)
        for backup, target in reversed(backups):
            backup.replace(target)
        raise


def run_job(config: dict, emit: Callable[[dict], None]) -> dict:
    directory = config.get('ffmpeg_dir', '').strip()
    if directory:
        if not Path(directory).is_dir():
            raise ValueError(f'FFmpeg folder not found: {directory}')
        os.environ['PATH'] = directory + os.pathsep + os.environ.get('PATH', '')
    require_executable('ffprobe')
    require_executable('ffmpeg')
    if config['action'] == 'scan_batch':
        from .gui_batch import scan_folder
        return scan_folder(config, emit)
    media = Path(config['media']).expanduser().resolve()
    if config['action'] == 'probe':
        return {'streams': [asdict(stream) for stream in probe_audio_streams(media)]}
    media, subtitle, paths = job_paths(config)
    if not parse_srt(subtitle):
        raise ValueError('No usable subtitle cues were found in the SRT file')
    options = TranscriptionOptions(
        model=config.get('model', 'small'), device=config.get('device', 'cpu'),
        compute_type=config.get('compute_type', 'int8'), language=config.get('language', 'en'),
        batch_size=int(config.get('batch_size', 8)),
    )
    paths.subtitle.parent.mkdir(parents=True, exist_ok=True)
    context = (nullcontext(config['stage_dir']) if config.get('stage_dir') else
               tempfile.TemporaryDirectory(prefix='.subtitle-align-', dir=paths.subtitle.parent))
    with context as work:
        staging = Path(work)
        pending = derive_output_paths(media, subtitle, staging / paths.subtitle.name,
                                      transcript=paths.transcript)
        result = sync_media(
            media, subtitle, pending, options,
            audio_language=None, audio_stream=int(config['audio_stream']),
            complete=bool(config.get('complete', True)),
            progress=lambda message: emit({'type': 'progress', 'message': message}),
        )
        payload = json.loads(pending.report_json.read_text(encoding='utf-8'))
        payload['metadata']['output'] = str(paths.subtitle)
        write_json_report(pending.report_json, payload)
        write_html_report(pending.report_html, payload)
        # Handshake with the parent: cancellation may kill native inference, but
        # must not kill us midway through replacing a set of output files.
        cancel = Path(config['cancel_file']) if config.get('cancel_file') else None
        if cancel and cancel.exists():
            raise RuntimeError('Cancelled before saving output')
        if config.get('commit_file'):
            Path(config['commit_file']).touch()
        if cancel and cancel.exists():
            raise RuntimeError('Cancelled before saving output')
        publish_outputs(list(zip(
            (pending.subtitle, pending.report_json, pending.report_html),
            (paths.subtitle, paths.report_json, paths.report_html),
        )), staging, bool(config.get('overwrite', False)))
    return {'summary': result.summary, 'output': str(paths.subtitle),
            'report': str(paths.report_html), 'folder': str(paths.subtitle.parent)}


def worker_main(config_path: str, events_path: str) -> int:
    import traceback
    with Path(events_path).open('a', encoding='utf-8', buffering=1) as events:
        def emit(value):
            events.write(json.dumps(value, ensure_ascii=False) + '\n')
            events.flush()
        try:
            config = json.loads(Path(config_path).read_text(encoding='utf-8'))
            emit({'type': 'done', **run_job(config, emit)})
            return 0
        except Exception as error:
            emit({'type': 'error', 'message': str(error), 'details': traceback.format_exc()})
            return 1
