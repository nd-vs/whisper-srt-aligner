# Architecture

1. FFprobe lists audio streams. Language metadata or an explicit audio index
   selects one; it does not always choose the first track.
2. FFmpeg extracts audio, using stream copy when possible and a PCM fallback.
3. faster-whisper supplies word timestamps. Complete mode reuses a loaded model
   for a primary no-VAD pass and a supplemental VAD pass.
4. Normalized source and recognized words are aligned monotonically. Common
   standalone words are suppressed as anchors; matches across distant scenes split.
5. Coherent partial matches can be rescued. Supplemental matches add anchors;
   coherent internal gaps can be inferred. Unplaceable cues are dropped.
6. The writer uses original cue text with new timings; JSON/HTML expose decisions.

Main modules: `media.py` (probe/extract), `transcriber.py` (recognition),
`transcript.py` (word representation), `alignment.py` (matching/merge),
`pipeline.py` (orchestration/cache), `batch.py` (episode pairing),
`subtitles.py` (SRT encodings/I/O), `report.py`, `cli.py`.

Caches fingerprint media path/size/mtime plus stream and recognition options.
They are not content-hash verification. Changing these inputs can trigger new
recognition. Reports may contain local paths; review before sharing.
