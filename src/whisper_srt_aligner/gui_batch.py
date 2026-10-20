"""Folder preflight and a sequential queue, independent of Tk widgets."""
from __future__ import annotations

from pathlib import Path

from .batch import discover_pairs, episode_key
from .media import LANGUAGE_ALIASES, probe_audio_streams, select_audio_stream


def scan_folder(config: dict, emit) -> dict:
    # Import here to keep the single-job boundary independent of the GUI.
    from .gui_jobs import job_paths

    if not config.get('folder', '').strip() or not config.get('output_dir', '').strip():
        raise ValueError('Choose an input folder and a separate output folder')
    folder = Path(config['folder']).expanduser().resolve()
    output = Path(config['output_dir']).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f'Input folder not found: {folder}')
    if output.exists() and not output.is_dir():
        raise ValueError(f'Output folder is not a directory: {output}')
    pairs, issues = discover_pairs(folder, config.get('video_glob', '*.mkv'),
                                  config.get('subtitle_glob', '*.srt'),
                                  bool(config.get('recursive', False)))
    paired_paths = {path.resolve() for pair in pairs for path in (pair.media, pair.subtitle)}
    for pattern in (config.get('video_glob', '*.mkv'), config.get('subtitle_glob', '*.srt')):
        files = folder.rglob(pattern) if config.get('recursive') else folder.glob(pattern)
        for path in sorted(files):
            if (path.is_file() and '.aligned.' not in path.name.casefold()
                    and path.resolve() not in paired_paths and episode_key(path) is None):
                issues.append(f'No episode number (S01E02 or 1x02): {path.relative_to(folder)}')
    items = []
    for pair in pairs:
        emit({'type': 'progress', 'message': f'Checking {pair.key}: {pair.media.name}'})
        item = dict(key=pair.key, media=str(pair.media.resolve()),
                    subtitle=str(pair.subtitle.resolve()),
                    output=str(output / f'{pair.media.stem}.aligned.srt'),
                    state='ready', message='', audio='')
        try:
            _, _, paths = job_paths({**item, 'overwrite': True})
            targets = (paths.subtitle, paths.report_json, paths.report_html)
            if not config.get('overwrite') and any(path.exists() for path in targets):
                item.update(state='skipped', message='Output or report already exists')
            else:
                streams = probe_audio_streams(pair.media)
                index = (int(config['batch_audio_index'])
                         if config.get('batch_audio_mode') == 'index' else None)
                language = config.get('language', 'en')
                selected = select_audio_stream(streams, language, index)
                # Do not silently use a lone, explicitly wrong-language track.
                aliases = LANGUAGE_ALIASES.get(language.casefold(), {language.casefold()})
                if index is None and selected.language and selected.language.casefold() not in ('und', ''):
                    if selected.language.casefold() not in aliases and (selected.title or '').casefold() not in aliases:
                        raise ValueError(f'Audio language is {selected.language}, not {language}; choose an explicit track index')
                item['audio_stream'] = selected.relative_index
                item['audio'] = (f'{selected.relative_index} · {selected.language or "und"} · '
                                 f'{selected.codec} · {selected.title or ""}')
        except Exception as error:
            item.update(state='error', message=str(error))
        items.append(item)
    # Every output must be unique, even if duplicate basenames occur in subfolders.
    targets: dict[Path, list[dict]] = {}
    for item in items:
        targets.setdefault(Path(item['output']), []).append(item)
    for collisions in targets.values():
        if len(collisions) > 1:
            for item in collisions:
                item.update(state='error', message='Multiple episodes would write the same output')
    return {'items': items, 'issues': issues, 'folder': str(output)}


class BatchQueue:
    """One active episode at a time; a stop never starts another episode."""

    def __init__(self, items: list[dict]):
        self.items = [dict(item) for item in items]
        self.active: int | None = None
        self.stopped = False
        self.total = sum(item['state'] == 'ready' for item in self.items)

    def next(self) -> dict | None:
        if self.active is not None:
            raise RuntimeError('The current episode has not finished')
        if self.stopped:
            return None
        for index, item in enumerate(self.items):
            if item['state'] == 'ready':
                self.active = index
                item['state'] = 'running'
                return item
        return None

    def finish(self, state: str, message: str = '') -> None:
        if self.active is None or state not in ('completed', 'failed', 'cancelled'):
            raise ValueError('No active episode or invalid completion state')
        self.items[self.active].update(state=state, message=message)
        self.active = None

    def stop(self) -> None:
        self.stopped = True

    @property
    def counts(self) -> dict[str, int]:
        states = ('ready', 'running', 'completed', 'failed', 'cancelled', 'skipped', 'error')
        return {state: sum(item['state'] == state for item in self.items) for state in states}
