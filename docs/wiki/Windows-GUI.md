# Windows GUI

The Windows app wraps the same alignment engine for one video/audio file and SRT.
[Download the Windows x64 ZIP for 0.2.0](https://github.com/nd-vs/whisper-srt-aligner/releases/download/v0.2.0/WhisperSrtAligner-0.2.0-windows-x64.zip),
or see [all release files and checksums](https://github.com/nd-vs/whisper-srt-aligner/releases/tag/v0.2.0).

## Portable build

Extract the entire ZIP to a writable folder. Run `WhisperSrtAligner.exe`
inside it; keep the `_internal` folder next to the EXE. No separate Python install
is required. The build is unsigned. Do not disable Windows security protections;
source launch remains available if your organization's policy blocks unsigned apps.

FFmpeg and FFprobe must be installed separately. Either add their folder to PATH
or select their `bin` folder in the GUI. Use the official FFmpeg download page
linked by the setup button. Models are not included; the first use downloads the
selected model. Media processing runs locally.

## First alignment

1. Select a video or audio file. The app reads its audio tracks in the background.
2. Select the original SRT and destination for a new SRT.
3. Set the spoken language (`en`, `ru`, etc.) and select the matching audio track.
4. Start with `small`, `cpu`, `int8`. Two-pass recovery is enabled by default.
5. Click Align subtitles. The window stays responsive; Cancel stops the worker
   and its child processes. There is a stage indicator/log, not a made-up ETA.
6. Open the report and output folder. Review dropped/inferred lines in your player.

For CUDA choose `cuda` and `float16`, with a compatible NVIDIA runtime already
installed. The portable CPU build does not bundle CUDA/cuDNN. Larger models need
more memory and may run much longer.

Inputs cannot be selected as output targets. Overwriting an existing generated
SRT/report requires confirmation. Alignment writes into staging first; failed or
cancelled recognition does not replace previous completed outputs. Closing during
a task asks to cancel and waits for the worker to exit.

The interface follows the system language: Russian for `ru`, English otherwise.
It can also be switched manually between English and Russian. Batch processing and
MKV muxing remain CLI/separate-tool workflows; the GUI does not burn in subtitles.

## Launch from source

After installing the project, run `whisper-srt-align-gui`, or:

```powershell
.\.venv\Scripts\pythonw.exe -m whisper_srt_aligner.gui
```

## Build from source (Windows)

Use an isolated environment to avoid collecting unrelated packages:

```text
python -m pip install ".[windows-build]"
python scripts/build_windows.py --work-dir <temporary-build-folder>
```

Output: `dist/windows/WhisperSrtAligner-0.2.0-windows-x64.zip` and its SHA-256.
The package includes runtime license metadata. Keep licenses when redistributing.
Building the bundle is not permission to publish it as a new GitHub release.
