import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from whisper_srt_aligner.gui_jobs import job_paths, publish_outputs, run_job, worker_main
from whisper_srt_aligner.models import AlignedCue, AlignmentResult


def fake_sync(media, subtitle, paths, options, **kwargs):
    paths.subtitle.write_text('new subtitles')
    summary = dict(source_cues=1, output_cues=1, dropped_cues=0, rescued_cues=0,
                   supplemented_cues=0, inferred_cues=0, token_coverage=1, dropped=[])
    paths.report_json.write_text(json.dumps(dict(
        metadata=dict(output=str(paths.subtitle)), summary=summary, cues=[], dropped=[])))
    return AlignmentResult([], [], summary)


class GuiJobTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.media = self.root/'video.wav'; self.media.write_bytes(b'original media')
        self.srt = self.root/'source.srt'
        self.srt.write_text('1\n00:00:01,000 --> 00:00:02,000\nHello world.\n',encoding='utf-8')
        self.config = dict(action='align',media=str(self.media),subtitle=str(self.srt),
                           output=str(self.root/'fixed.srt'),audio_stream=0)

    def tearDown(self):self.temp.cleanup()

    def test_cannot_overwrite_source_even_when_overwrite_is_enabled(self):
        self.config.update(output=str(self.srt),overwrite=True)
        with self.assertRaisesRegex(ValueError,'original inputs'):job_paths(self.config)

    def test_cannot_overwrite_an_input_through_a_hardlink(self):
        target=self.root/'alias.srt'
        os.link(self.srt,target); self.config.update(output=str(target),overwrite=True)
        with self.assertRaisesRegex(ValueError,'original inputs'):job_paths(self.config)

    def test_existing_report_also_requires_overwrite(self):
        (self.root/'fixed.alignment.html').write_text('previous report')
        with self.assertRaises(FileExistsError):job_paths(self.config)

    def test_publish_rolls_back_prior_outputs_on_later_failure(self):
        stage=self.root/'stage';stage.mkdir()
        first=self.root/'one';first.write_text('old one')
        second=self.root/'two';second.write_text('old two')
        pending=stage/'new';pending.write_text('new one')
        with self.assertRaises(FileNotFoundError):
            publish_outputs([(pending,first),(stage/'missing',second)],stage,True)
        self.assertEqual('old one',first.read_text())
        self.assertEqual('old two',second.read_text())

    def test_alignment_failure_leaves_previous_result_and_source_unchanged(self):
        output=Path(self.config['output']);output.write_text('previous result')
        self.config['overwrite']=True
        with patch('whisper_srt_aligner.gui_jobs.require_executable'), patch(
                'whisper_srt_aligner.gui_jobs.sync_media',side_effect=RuntimeError('recognition failed')):
            with self.assertRaises(RuntimeError):run_job(self.config,lambda event:None)
        self.assertEqual('previous result',output.read_text())
        self.assertEqual(b'original media',self.media.read_bytes())
        self.assertFalse(list(self.root.glob('.subtitle-align-*')))

    def test_reports_point_to_final_output_not_temporary_staging(self):
        with patch('whisper_srt_aligner.gui_jobs.require_executable'), patch('whisper_srt_aligner.gui_jobs.sync_media',side_effect=fake_sync):
            result=run_job(self.config,lambda event:None)
        report=json.loads((self.root/'fixed.alignment.json').read_text())
        # Windows TEMP may use an 8.3 alias (RUNNER~1), while job_paths resolves it.
        self.assertEqual(str((self.root/'fixed.srt').resolve()),report['metadata']['output'])
        self.assertTrue(Path(report['metadata']['output']).samefile(self.root/'fixed.srt'))
        self.assertTrue(Path(result['report']).exists())

    def test_cancellation_before_commit_cannot_replace_existing_outputs(self):
        output=Path(self.config['output']);output.write_text('previous result')
        cancel=self.root/'cancel';cancel.touch()
        self.config.update(overwrite=True,cancel_file=str(cancel),commit_file=str(self.root/'committing'))
        with patch('whisper_srt_aligner.gui_jobs.require_executable'), patch(
                'whisper_srt_aligner.gui_jobs.sync_media',side_effect=fake_sync):
            with self.assertRaisesRegex(RuntimeError,'Cancelled'):run_job(self.config,lambda event:None)
        self.assertEqual('previous result',output.read_text())
        self.assertFalse((self.root/'committing').exists())

    def test_worker_errors_are_structured_and_do_not_silently_succeed(self):
        config=self.root/'job.json';events=self.root/'events.jsonl'
        config.write_text(json.dumps(self.config))
        with patch('whisper_srt_aligner.gui_jobs.run_job',side_effect=RuntimeError('missing DLL')):
            code=worker_main(str(config),str(events))
        event=json.loads(events.read_text())
        self.assertEqual(1,code);self.assertEqual('error',event['type'])
        self.assertEqual('missing DLL',event['message'])
