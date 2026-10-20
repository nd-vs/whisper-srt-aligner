import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from whisper_srt_aligner.gui_batch import BatchQueue, scan_folder
from whisper_srt_aligner.models import AudioStream


def stream(index=0, language='eng'):
    return AudioStream(index, index+1, 'aac', 2, language, None, index==0)


class FolderScanTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = dict(folder=str(self.root), output_dir=str(self.root/'aligned'),
                           language='en', batch_audio_mode='auto')

    def tearDown(self):
        self.temp.cleanup()

    def episode(self, key, subtitle_name=None):
        (self.root/f'Show.{key}.mkv').touch()
        (self.root/(subtitle_name or f'Source.{key}.srt')).write_text(
            '1\n00:00:01,000 --> 00:00:02,000\nHello.\n', encoding='utf-8')

    def scan(self, tracks=None):
        with patch('whisper_srt_aligner.gui_batch.probe_audio_streams',
                   return_value=tracks or [stream()]):
            return scan_folder(self.config, lambda e: None)

    def test_preflight_pairs_episodes_and_does_not_create_output_folder(self):
        self.episode('S01E02'); self.episode('S01E01')
        result = self.scan()
        self.assertEqual(['S01E01', 'S01E02'], [i['key'] for i in result['items']])
        self.assertTrue(all(i['state']=='ready' for i in result['items']))
        self.assertFalse((self.root/'aligned').exists())

    def test_selects_language_separately_when_track_order_changes(self):
        self.episode('S01E01'); self.episode('S01E02')
        with patch('whisper_srt_aligner.gui_batch.probe_audio_streams', side_effect=[
                [stream(0,'rus'), stream(1,'eng')], [stream(0,'eng'), stream(1,'rus')]]):
            result = scan_folder(self.config, lambda e: None)
        self.assertEqual([1,0], [i['audio_stream'] for i in result['items']])

    def test_ambiguous_pair_is_not_queued(self):
        self.episode('S01E01')
        (self.root/'Alternative.S01E01.srt').touch()
        result = self.scan()
        self.assertEqual([], result['items'])
        self.assertEqual(1, len(result['issues']))

    def test_unrecognized_names_are_reported_instead_of_silently_omitted(self):
        self.episode('S01E01')
        (self.root/'Episode Two.mkv').touch()
        self.assertIn('No episode number', self.scan()['issues'][0])

    def test_wrong_language_and_missing_explicit_index_are_errors(self):
        self.episode('S01E01')
        self.assertEqual('error', self.scan([stream(0,'rus')])['items'][0]['state'])
        self.config.update(batch_audio_mode='index', batch_audio_index='2')
        self.assertEqual('error', self.scan()['items'][0]['state'])

    def test_single_untagged_track_is_available_for_review(self):
        self.episode('S01E01')
        item = self.scan([stream(0,None)])['items'][0]
        self.assertEqual('ready', item['state'])
        self.assertIn('und', item['audio'])

    def test_existing_output_or_report_is_skipped_unless_overwrite_enabled(self):
        self.episode('S01E01')
        output = self.root/'aligned'; output.mkdir()
        report = output/'Show.S01E01.aligned.alignment.html'; report.write_text('keep me')
        self.assertEqual('skipped', self.scan()['items'][0]['state'])
        self.config['overwrite'] = True
        self.assertEqual('ready', self.scan()['items'][0]['state'])
        self.assertEqual('keep me', report.read_text())

    def test_recursive_scan_ignores_generated_aligned_subtitles(self):
        self.episode('S01E01')
        output = self.root/'aligned'; output.mkdir()
        (output/'Show.S01E01.aligned.srt').touch()
        self.config['recursive'] = True
        result = self.scan()
        self.assertEqual([], result['issues'])
        self.assertEqual('skipped', result['items'][0]['state'])

    def test_empty_paths_are_rejected_instead_of_using_working_directory(self):
        self.config['folder'] = ''
        with self.assertRaises(ValueError):self.scan()


class BatchQueueTest(unittest.TestCase):
    def queue(self):
        return BatchQueue([dict(key='S01E01', state='ready'), dict(key='S01E02',state='ready'),
                           dict(key='S01E03',state='skipped'), dict(key='S01E04',state='error')])

    def test_only_ready_items_run_sequentially_and_failures_can_continue(self):
        queue = self.queue()
        self.assertEqual(2, queue.total)
        self.assertEqual('S01E01', queue.next()['key'])
        with self.assertRaises(RuntimeError):queue.next()
        queue.finish('failed', 'unreadable audio')
        self.assertEqual('S01E02', queue.next()['key'])
        queue.finish('completed')
        self.assertIsNone(queue.next())
        self.assertEqual(1, queue.counts['failed'])
        self.assertEqual(1, queue.counts['completed'])

    def test_cancel_stops_queue_and_keeps_unstarted_items_ready_for_resume(self):
        queue = self.queue(); queue.next(); queue.stop(); queue.finish('cancelled')
        self.assertIsNone(queue.next())
        self.assertEqual(1, queue.counts['ready'])
        self.assertEqual(1, queue.counts['cancelled'])

    def test_completion_wins_if_cancel_arrives_just_after_output_publication(self):
        queue = self.queue(); queue.next(); queue.stop(); queue.finish('completed')
        self.assertEqual(1, queue.counts['completed'])
        self.assertIsNone(queue.next())
