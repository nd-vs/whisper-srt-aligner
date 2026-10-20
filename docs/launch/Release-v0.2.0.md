# v0.2.0 — Windows desktop app

Align an existing SRT to speech without using a terminal. This release adds a
portable Windows x64 app; the existing command-line tool is still available.

## Download and run

1. Download `WhisperSrtAligner-0.2.0-windows-x64.zip` below.
2. Extract the **entire** archive and run `WhisperSrtAligner.exe`. Keep `_internal`
   next to the EXE. Python is included; no separate Python installation is needed.
3. Install **FFmpeg and FFprobe** separately. If they are not on PATH, select
   their `bin` folder in the app.
4. Select your media, original SRT, output SRT, spoken language and audio track.
   Start with **CPU / small / int8**, then click **Align subtitles**.

The first use downloads the chosen speech model. Media processing stays local.
The app is unsigned; do not disable Windows security protections. Source launch
is available if your policy blocks unsigned applications.

[Windows guide](https://github.com/nd-vs/whisper-srt-aligner/wiki/Windows-GUI) ·
[FFmpeg setup](https://github.com/nd-vs/whisper-srt-aligner/wiki/Installation#prerequisites) ·
[Source and CLI instructions](https://github.com/nd-vs/whisper-srt-aligner#command-line--install-from-source)

## What is included

- Audio-track selection, spoken language and model/device settings.
- CPU-first defaults and two-pass recovery for short and quiet lines.
- Responsive background processing, cancellation, progress log and report shortcuts.
- Staged saving and overwrite confirmation to protect inputs and previous results.
- System-language selection: Russian or English fallback, with a manual switch.
- A reproducible Windows build recipe and runtime license metadata.

## Scope and checks

The GUI handles **one media/SRT pair**. Batch processing and MKV muxing remain
CLI/separate-tool workflows. Audio and subtitles must use the same language.
Quiet or overlapping speech and inferred timing still need review.

33 unit tests passed locally. The Windows app was checked with real CPU/small/int8
two-pass recognition and the controlled demo; output matched its reference SRT.
Cancellation and source/output protection were also checked. The model was cached:
an empty-cache first run and a clean Windows installation were not tested.
CUDA operation from this bundle was not tested; CUDA/cuDNN are not bundled.

The Windows ZIP, Python wheel and source ZIP are listed in `SHA256SUMS.txt`.
See [validation details](https://github.com/nd-vs/whisper-srt-aligner/blob/main/docs/launch/GUI-validation.md).
