# Troubleshooting

| Symptom | What to do |
| --- | --- |
| `py` / `python3` not found | Install Python; reopen your terminal. On Windows check the Python launcher. |
| `Required executable is not on PATH` | Install both FFmpeg and FFprobe, add their directory to PATH, reopen the terminal. |
| PowerShell refuses activation | Do not activate. Use `.\.venv\Scripts\whisper-srt-align.exe` directly. |
| No matching English audio stream | Run `inspect`, then choose the audio `INDEX` with `--audio-stream`. |
| CUDA/cuDNN/cuBLAS DLL error | Follow the upstream runtime setup, or retry with `--device cpu --compute-type int8 --model small`. |
| GPU memory error | Reduce batch size/model; close other GPU tasks, or use CPU. |
| Model download fails | Check network/cache access. Offline mode requires a previously cached model. |
| `open() got an unexpected keyword argument 'metadata_errors'` | Upgrade to this package's 0.1.1 build, which constrains PyAV below 19. Do not independently upgrade PyAV past that bound. |
| Existing output error | Choose a new output path or explicitly use `--overwrite`. |
| Batch finds no pair / ambiguous pair | Check episode keys, globs and duplicate media/SRTs; run `--dry-run`. |
| Very poor coverage | Confirm spoken language, chosen audio track and matching dialogue before tuning. |
| Missing quiet line | Use `--complete`; inspect dropped/inferred cues. Manually review unresolved lines. |
| CPU run is slow | Try a shorter clip/smaller model first. No ETA is guaranteed across hardware. |

SRT encoding support includes BOM-marked UTF-16 and common UTF-8/Windows encodings.
If non-English text is garbled, convert a copy to UTF-8 in a subtitle editor and
retry. Encoding detection cannot disambiguate every legacy code page.

When reporting a problem, include OS, version, command, error, selected audio
metadata, and a small shareable example. Redact personal paths from reports and
check that you have permission to share any audio/video. Whole episodes are not needed.

The PyAV compatibility bound follows the diagnosed
[upstream faster-whisper issue](https://github.com/SYSTRAN/faster-whisper/issues/1589).
Re-evaluate it when a compatible faster-whisper release is adopted.
