# Usage

Prefer a desktop app? See [Windows GUI](Windows-GUI.md) for single-file processing
and [Folder / season mode](Windows-GUI.md#folder--season-mode) for a whole folder.

Below, `whisper-srt-align` means the installed executable. Without activation use
`.\.venv\Scripts\whisper-srt-align.exe` (Windows) or
`.venv/bin/whisper-srt-align` (Linux/macOS).

## Select the right audio

```text
whisper-srt-align inspect "episode.mkv"
```

`INDEX` is the zero-based **audio index**, not the container-wide `STREAM` index.
For missing or incorrect language tags, choose explicitly:

```text
whisper-srt-align sync "episode.mkv" "source.en.srt" --audio-stream 1 --complete --model small --device cpu --compute-type int8 --output "episode.fixed.srt"
```

The default requested audio language is `eng`. A multi-track file with no match
requires explicit selection. A single-track file can fall back to that track;
inspect it if recognition is wrong.

## Languages

Source text and spoken dialogue must use the same language.

| Option | Purpose | English | Russian |
| --- | --- | --- | --- |
| `--audio-language` | Select tagged audio | `eng` | `rus` |
| `--language` | Whisper recognition language | `en` | `ru` |

```text
whisper-srt-align sync "episode.mkv" "source.ru.srt" --audio-language rus --language ru --complete --model small --device cpu --compute-type int8 --output "episode.fixed.srt"
```

These are supported settings, not evidence that every language was validated on
real episodes. English is the development/demo scenario documented here.

## One file and its outputs

```text
whisper-srt-align sync "episode.mkv" "source.en.srt" --complete --model small --device cpu --compute-type int8 --output "episode.fixed.srt"
```

- `episode.fixed.srt`: newly timed subtitles.
- `episode.fixed.alignment.html`: browser review report.
- `episode.fixed.alignment.json`: per-cue timings, statuses and metadata.
- `.whisper-srt-aligner-cache/`: reusable primary and supplemental transcripts.

Input files are unchanged. Existing output SRTs require `--overwrite`. This switch
replaces output files; use a separate output directory while experimenting.

## Batch a season

Names must contain a recognizable episode key, such as `S01E01`. Preview matching;
ambiguous pairs are reported rather than guessed.

```text
whisper-srt-align batch "D:\Video\Season" --video-glob "*.mkv" --subtitle-glob "*.srt" --dry-run
```

```text
whisper-srt-align batch "D:\Video\Season" --video-glob "*.mkv" --subtitle-glob "*.srt" --output-dir "D:\Video\Season\fixed" --complete --model small --device cpu --compute-type int8
```

Use a narrower subtitle glob if each episode has several languages. Keep generated
MKVs outside the input folder to avoid duplicate matches. The model is loaded once
and reused; reports/caches are per episode. Batch exits nonzero on pairing or
processing errors even if some episodes succeed. Existing SRTs are errors unless
`--overwrite` is supplied; they are not silently skipped.

## Reuse recognition

Copy the exact cache paths printed by `sync` (names can contain a digest):

```text
whisper-srt-align align "primary.whisper.json" "source.en.srt" --supplement-transcript "supplement.vad.whisper.json" --output "episode.fixed.srt" --overwrite
```

Supplying a supplemental transcript enables complete-mode merging/inference. With
one transcript, inference requires `--infer-unmatched`. Legacy Whisper JSON segment
arrays are accepted. `--force-transcribe` ignores matching caches; changing model,
language or runtime options may invalidate them.

## Add the result to an MKV

After reviewing the SRT, install [MKVToolNix](https://mkvtoolnix.download/) and create
a new MKV without re-encoding:

```text
mkvmerge -o "episode.with-subs.mkv" "episode.mkv" --language 0:eng --track-name 0:English --default-track-flag 0:yes "episode.fixed.srt"
```

This adds a selectable subtitle track. It does not change existing tracks' default
flags, so multiple defaults may need adjustment. Inspect IDs using `mkvmerge -J` and
check selection in your player. Never reuse the source path as the output. Muxing
is not performed by the aligner.

## Reference

Subcommands: `inspect`, `sync`, `batch`, `transcribe`, `align`. Use `--help` on each
for exact options. The default model remains `large-v3`; beginner examples choose
`small` explicitly. Recommended `--complete` remains opt-in.
