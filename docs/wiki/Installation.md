# Installation

## Prerequisites

Install Python 3.10+ from [python.org](https://www.python.org/downloads/). On Windows,
include the Python launcher (`py`). Python 3.10 and 3.12 are covered by CI; not every
newer Python version has been tested here.

This application needs both `ffmpeg` and `ffprobe` on `PATH` to inspect and extract
audio, even though faster-whisper itself can decode audio through PyAV. See the
[official FFmpeg download page](https://ffmpeg.org/download.html).

- **Windows:** extract a build containing both executables. Add its `bin` folder
  to your user `Path` in Environment Variables, then open a new terminal.
- **macOS with Homebrew:** `brew install ffmpeg`.
- **Debian/Ubuntu:** `sudo apt install ffmpeg python3-venv`.

Check both:

```text
ffmpeg -version
ffprobe -version
```

## Install the application

Download **Code → Download ZIP** from the repository, extract it, and open a
terminal in the folder containing `pyproject.toml`. Git users can clone
`https://github.com/nd-vs/whisper-srt-aligner.git` instead.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\whisper-srt-align.exe --version
```

Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/whisper-srt-align --version
```

Using the environment's executable directly avoids activation and PowerShell
execution-policy changes. Installation downloads dependencies. First transcription
downloads the selected model from Hugging Face; later runs reuse it. No hosted
transcription API is used, and media are processed locally.

## Start on the CPU

Use `--model small --device cpu --compute-type int8` for a first attempt without
CUDA. A smaller model may miss more difficult speech. For another language, change
both language options in [Usage](Usage.md). Apple Silicon uses the CPU path here;
the application does not configure an MPS backend.

## NVIDIA GPU (optional)

GPU support depends on the installed faster-whisper/CTranslate2 versions.
Follow the [upstream GPU requirements](https://github.com/SYSTRAN/faster-whisper#gpu)
for compatible NVIDIA drivers, cuBLAS and cuDNN. Installing this package alone does
not guarantee a working CUDA runtime.

With the runtime configured, use the installed executable (or its full path):

```text
whisper-srt-align sync "episode.mkv" "source.en.srt" --complete --model large-v3 --device cuda --compute-type float16 --output "episode.fixed.srt"
```

If memory is exhausted, try `--batch-size 1`, a smaller model, or the CPU path.
Not every GPU can run `large-v3` at the default batch size.

## Time, memory, downloads

Model downloads can be substantial. A full episode can take minutes or much longer
on a CPU. Memory depends on the model, precision, batch size and runtime. This
project does not yet provide verified cross-hardware time or RAM guarantees.
Try the [short demo](../demo/README.md) before queuing a season. Upstream
[benchmarks](https://github.com/SYSTRAN/faster-whisper#benchmark) are context, not
two-pass end-to-end measurements of this application.

Complete mode recognizes the audio twice but loads the model and extracts audio
once. It is not necessarily exactly twice as slow because the passes use different
inference paths. For offline work, cache the model and dependencies first; setting
`HF_HUB_OFFLINE=1` with an uncached model fails.
