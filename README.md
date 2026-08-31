# whisper-srt-aligner

`whisper-srt-aligner` rebuilds subtitle timing from the actual audio while keeping
the edited text from an existing SRT file.

It is intended for releases where a subtitle comes from a different cut: a
constant offset, linear stretch, or ordinary subtitle synchronizer cannot handle
inserted and removed scenes. Whisper supplies word timestamps; the source SRT
supplies spelling, punctuation, line breaks, and formatting.

The recommended complete mode combines two Whisper passes so quiet and very
short lines are not lost to voice-activity detection. Cues that still cannot be
heard can be placed between confirmed neighboring cues when the local timing
scale remains coherent. Every supplemented, inferred, or dropped cue is listed
in JSON and HTML reports.

## What it does

1. Selects the requested audio stream using FFprobe metadata.
2. Extracts the selected audio stream with FFmpeg, without re-encoding when possible.
3. Produces word timestamps with `faster-whisper`.
4. Aligns the complete SRT and Whisper word sequences monotonically.
5. Keeps the original SRT text for confirmed cues.
6. In complete mode, merges passes without and with VAD and infers only gaps
   bracketed by confirmed cues.
7. Removes cues that are absent from the audio or cannot be placed safely.
8. Writes a new SRT, reusable transcript caches, and review reports.

Input media and subtitles are never modified. Existing output files are only
replaced when `--overwrite` is passed.

## Requirements

- Python 3.10 or newer
- FFmpeg and FFprobe on `PATH`
- CPU, or an NVIDIA GPU supported by `faster-whisper`

The default model is `large-v3`. It gives stronger matching anchors but requires
more time and memory than smaller models.

## Install

```bash
git clone https://github.com/nd-vs/whisper-srt-aligner.git
cd whisper-srt-aligner
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## One episode

First inspect the audio streams:

```powershell
whisper-srt-align inspect "episode.mkv"
```

Then build an aligned SRT:

```powershell
whisper-srt-align sync "episode.mkv" "source.en.srt" `
  --complete `
  --audio-language eng `
  --language en `
  --device cuda `
  --compute-type float16 `
  --output "episode.aligned.srt"
```

If language metadata is missing or wrong, select the zero-based audio index shown
by `inspect`:

```powershell
whisper-srt-align sync "episode.mkv" "source.en.srt" --audio-stream 1
```

`--complete` is recommended when preserving short or quiet cues matters. It runs
Whisper twice, but loads the model and extracts the audio only once. The first
pass disables VAD; the second pass uses VAD as a supplemental source of anchors.

The default outputs are:

- `episode.aligned.srt`
- `episode.aligned.alignment.json`
- `episode.aligned.alignment.html`
- `.whisper-srt-aligner-cache/...whisper.json` (primary pass)
- `.whisper-srt-aligner-cache/...vad.whisper.json` (complete mode)

## Re-align without running Whisper again

Threshold or formatting changes can be tested against the cached word timestamps:

```powershell
whisper-srt-align align ".whisper-srt-aligner-cache\episode.whisper.json" `
  "source.en.srt" `
  --supplement-transcript ".whisper-srt-aligner-cache\episode.vad.whisper.json" `
  --output "episode.aligned.srt" `
  --overwrite
```

The `align` command also accepts the legacy transcript format consisting of a JSON
array of Whisper segments.

## Batch a season

Preview episode pairing first. Ambiguous episodes are not guessed:

```powershell
whisper-srt-align batch "D:\Video\Season" `
  --video-glob "*.mkv" `
  --subtitle-glob "*eng.srt" `
  --dry-run
```

Run the batch after checking the pairs:

```powershell
whisper-srt-align batch "D:\Video\Season" `
  --video-glob "*.mkv" `
  --subtitle-glob "*eng.srt" `
  --complete `
  --audio-language eng `
  --device cuda `
  --compute-type float16
```

The Whisper model is loaded once and reused for every episode. Each episode gets
its own transcript cache and reports.

## Add the result to an MKV

Muxing is intentionally separate from alignment. Review the generated SRT first,
then create a new MKV without re-encoding:

```powershell
mkvmerge -o "episode.with-subs.mkv" `
  "episode.mkv" `
  --language 0:eng `
  --track-name 0:English `
  --default-track-flag 0:yes `
  "episode.aligned.srt"
```

This preserves the original MKV. Inspect the new file with `mkvmerge -J` and test
track selection in the target player.

## Alignment strategy

The aligner normalizes words while preserving original cue text. It finds a
monotonic sequence of matching words across the entire episode, suppresses common
standalone words as anchors, and splits cue matches that land in distant scenes.

A cue is kept when it has enough coherent evidence. Missing leading or trailing
word timing is estimated only inside a confirmed cue. In complete mode, a cue
missed by the primary no-VAD pass can be supplied by the VAD pass. A remaining
internal gap can be inferred only when it has confirmed anchors on both sides
and their local time scale does not indicate a removed scene. Leading and
trailing gaps are never extrapolated. Everything else is dropped and included
in the report.

Report statuses are:

- `matched`: timed directly by the primary Whisper pass;
- `supplemented`: timed directly by the supplemental VAD pass;
- `rescued`: a weak partial match placed between close anchors;
- `inferred`: source timing mapped between confirmed anchors;
- `dropped`: no safe placement was found.

## Limitations

- The current parser and writer target SRT. ASS/SSA styling is not supported.
- Source subtitles and audio must be in the same language.
- Complete mode is approximately twice as expensive as one transcription pass.
- Songs, overlapping speakers, very short repeated phrases, and heavy paraphrasing
  may still require manual review.
- A high global token-coverage percentage does not prove that every cue is correct;
  inspect the dropped/interpolated lists and sample the beginning, middle, and end.
- Release-title cues containing an `SxxExx` token, and URL-only credit cues, are
  ignored automatically.

## Development

The alignment tests do not download a Whisper model:

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
python -m unittest discover -s tests -v
```

## License

MIT
