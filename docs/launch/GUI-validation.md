# Windows GUI validation

Release target: `0.2.0`, Windows 11 x64, Python 3.12 build environment.
The interactive checks below were performed on the `0.2.0.dev0` candidate before
release packaging. The published 0.1.1 release is not modified.

## Checks performed

- 33 unit tests pass, including original-input/hardlink protection, report collisions,
  rollback when saving fails, failed recognition preserving old output, structured
  worker errors and cancellation before publication.
- Real child-process probing and CPU/small/int8 complete-mode recognition passed.
- Cancellation during a new recognition task preserved previous output and removed
  the owned staging directory. A completed task is reported as completed even if
  Cancel is clicked just afterward.
- The windowed EXE ran both Whisper passes on the supplied 57-second WAV without
  a precomputed transcript. It retained all six source cue texts.
- The actual EXE window was operated through computer-use: media/SRT/destination
  entry, audio-track discovery and Align. The resulting SRT exactly matched the
  published controlled-demo result. Russian labels and action availability were
  visually checked at the machine's display scaling.
- Local Markdown links and Python compilation passed.
- The final 0.2.0 ZIP was checked for archive integrity and versioned package
  metadata, extracted into a separate folder and used for CPU/small/int8
  two-pass recognition. All six cues exactly matched the demo reference SRT.

## Distribution

Portable directory ZIP, about 96 MiB. Keep `_internal` next to the EXE. Python is
bundled; FFmpeg/FFprobe, CUDA/cuDNN and speech models are not. The `small` model
was already cached during validation. The binary is unsigned. Runtime license
metadata and Python/project license material are included.

## Not established by these checks

- First model download in an empty cache or installation on a clean Windows machine.
- CUDA operation from the portable bundle (CPU was tested).
- General accuracy on new films or TV episodes.
- Batch processing/muxing in the GUI; these remain existing external workflows.
- External-user usability testing, installer signing or Microsoft Store distribution.
