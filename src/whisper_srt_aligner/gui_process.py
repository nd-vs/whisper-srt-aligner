"""A file-event worker protocol also works with a windowed frozen executable."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from .gui_jobs import job_paths


class JobProcess:
    def __init__(self, config: dict):
        self.work = tempfile.TemporaryDirectory(prefix='subtitle-align-gui-')
        self.stage = None
        self.process = None
        self.killer = None
        self.cancelled = False
        self.offset = 0
        self.buffer = b''
        self.terminal = False
        self.folder = Path(self.work.name)
        self.events = self.folder / 'events.jsonl'
        self.log_path = self.folder / 'worker.log'
        self.log = None
        try:
            config = dict(config)
            config['cancel_file'] = str(self.folder/'cancel')
            config['commit_file'] = str(self.folder/'committing')
            if config['action'] == 'align':
                _, _, paths = job_paths(config)
                paths.subtitle.parent.mkdir(parents=True, exist_ok=True)
                self.stage = tempfile.TemporaryDirectory(prefix='.subtitle-align-', dir=paths.subtitle.parent)
                config['stage_dir'] = self.stage.name
            job = self.folder / 'job.json'
            job.write_text(json.dumps(config), encoding='utf-8')
            command = [sys.executable]
            if not getattr(sys, 'frozen', False):
                command += ['-u', '-m', 'whisper_srt_aligner.gui']
            command += ['--worker', str(job), str(self.events)]
            self.log = self.log_path.open('wb')
            self.process = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=self.log, stderr=self.log,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                start_new_session=(os.name != 'nt'),
            )
        except Exception:
            self.close()
            raise

    def poll(self) -> list[dict]:
        result = []
        if self.events.exists():
            with self.events.open('rb') as handle:
                handle.seek(self.offset)
                self.buffer += handle.read()
                self.offset = handle.tell()
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                if line:
                    event = json.loads(line.decode('utf-8'))
                    self.terminal |= event['type'] in ('done', 'error')
                    result.append(event)
        return result

    @property
    def finished(self) -> bool:
        return (self.process is not None and self.process.poll() is not None
                and (self.killer is None or self.killer.poll() is not None))

    def cancel(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.cancelled = True
        (self.folder/'cancel').touch()
        if (self.folder/'committing').exists():
            return
        if os.name == 'nt':
            self.killer = subprocess.Popen(
                ['taskkill', '/PID', str(self.process.pid), '/T', '/F'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def diagnostic(self) -> str:
        return self.log_path.read_text(encoding='utf-8', errors='replace')[-6000:]

    def close(self) -> None:
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError('Cannot clean up a running worker')
        if self.log is not None:
            self.log.close()
        if self.stage is not None:
            self.stage.cleanup()
        self.work.cleanup()
