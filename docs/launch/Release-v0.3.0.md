# v0.3.0 — Folder and season processing in the Windows app

Process a whole season without running a command for every episode.
Single-file mode and the existing CLI remain available.

## Download and run

Download **WhisperSrtAligner-0.3.0-windows-x64.zip** below, extract the entire
archive and run `WhisperSrtAligner.exe`. Keep `_internal` next to the EXE.
Python is bundled; **FFmpeg and FFprobe must be installed separately**. Select
their `bin` folder in the app if they are not on PATH.

The app is unsigned; keep Windows security protections enabled. The first use
downloads the selected speech model. Media processing stays local.

## Process a season

1. Choose **Folder / season**, the season folder and an output folder.
2. Set the video/SRT masks and enable subfolders if needed.
3. Choose the spoken language, then click **Check folder**.
4. Review the episode pairs and audio tracks in **Show episodes**.
5. Click **Align subtitles** and confirm the ready-episode count.

Pairing supports `S01E02` and `1x02`. Ambiguous or missing pairs are reported,
not guessed. Audio is selected separately for every episode by language, or
by an explicit zero-based track index. Check untagged audio yourself.

Episodes run sequentially with episode-count progress and recognition-stage
details. Existing results are skipped by default. Replacement requires
confirmation. Cancel stops the current worker and prevents the next episode
from starting; completed files are retained. Recheck the folder to resume.
An episode failure is shown in the log/preview and the queue continues.

Outputs are new `.aligned.srt` files with JSON/HTML review reports. This does not
mux subtitles into MKV. Audio and subtitles must use the same language; inferred
timing and difficult speech still need review.

[Windows and folder guide](https://github.com/nd-vs/whisper-srt-aligner/wiki/Windows-GUI) ·
[FFmpeg setup](https://github.com/nd-vs/whisper-srt-aligner/wiki/Installation#prerequisites)

## Checks and release files

45 unit tests passed locally. The Windows GUI processed two controlled demo
episodes with CPU/small/int8 and both recognition passes; both SRT files matched
the reference exactly. Existing-output skipping, queue cancellation, input
preservation and reduced-height window scrolling were also checked.

The model was cached. A clean Windows installation, CUDA operation from the
portable bundle, long-season endurance and general subtitle accuracy were not
established. CUDA/cuDNN are not bundled.

The Windows ZIP, Python wheel and source ZIP are listed in `SHA256SUMS.txt`.
[Validation details](https://github.com/nd-vs/whisper-srt-aligner/blob/main/docs/launch/GUI-batch-validation.md).
