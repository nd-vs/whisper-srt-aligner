# Changelog

## 0.1.1 — 2026-10-20

- Simpler CPU-first setup, a controlled before/after demo, and separate technical documentation.
- UTF-16 decoding now requires a byte-order mark, preventing some Windows-1252
  subtitle files from being silently decoded as UTF-16. Includes regression coverage.
- Clearer accuracy/review guidance; retained cue count is not presented as timing accuracy.
- Constrain PyAV to `<19` while released faster-whisper 1.2.x passes the removed
  `metadata_errors` argument. A fresh installation otherwise fails to decode audio.

The CLI default model and complete-mode behavior are unchanged. No GUI, automatic
MKV muxing, or cross-language alignment is added.

## 0.1.0

- Initial CLI: audio inspection, recognition, SRT alignment, complete mode, batch
  episode matching, reusable transcripts, JSON/HTML reports.
