# v0.1.1 — Easier first run, a reproducible demo, and an encoding fix

Release notes approved for publication on 2026-10-20.

Have subtitle text you trust, but timings that drift after an intro or scene cut?
whisper-srt-aligner matches it to recognized speech and writes a newly timed SRT
plus a report showing which lines need review.

This first packaged release includes:

- A shorter, CPU-first getting-started guide; no Git or environment activation is
  required when installing from a source ZIP.
- Separate technical documentation for languages, audio tracks, seasons, caches,
  reports and troubleshooting, ready to export to a GitHub wiki.
- A reproducible 57-second before/after demo with original synthetic speech,
  source/result SRTs, recognition transcripts and measured timing differences.
- A fix for Windows-1252 SRTs being misread as UTF-16, covered by a regression test.
- A PyAV compatibility bound fixing fresh installations that failed during audio
  decoding with `metadata_errors` (released faster-whisper/PyAV 19 incompatibility).

## Downloads

Assets: `whisper_srt_aligner-0.1.1-py3-none-any.whl`,
`whisper-srt-aligner-0.1.1-source.zip`, and `SHA256SUMS.txt`.
These are a Python wheel and source package, **not a standalone executable**.
Use Python 3.10+ and install FFmpeg/FFprobe separately. The model downloads on the
first transcription. There is no PyPI release claimed by these instructions.

For a downloaded wheel, create a virtual environment and run its Python with:

```text
python -m pip install whisper_srt_aligner-0.1.1-py3-none-any.whl
```

Use the resulting `whisper-srt-align` executable. For the source ZIP, extract it
and follow README's three installation commands.

## Scope and checks

This remains an early CLI. Source subtitles and audio must use the same language;
SRT is the supported format. Recommended complete mode can recover more lines,
but dropped/inferred cues still need review. No general accuracy or competitor
superiority claim is made. Default model/complete-mode behavior is unchanged.

Local checks: 25 unit tests passed; the CPU demo retained 6/6 source texts without
manual retiming. Packaging/clean-environment checks are recorded in the local
validation summary. Windows/Linux CI on Python 3.10/3.12 is checked on the release
commit before tagging; the published release links to that run.
