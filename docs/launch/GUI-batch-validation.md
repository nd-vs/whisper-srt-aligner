# Folder GUI validation — 0.3.0

Release target: 0.3.0, Windows 11 x64. The interactive checks below were performed
on the 0.3.0.dev0 candidate before release packaging.

- 45 unit tests passed. New cases cover episode pairing, ambiguous names,
  unrecognized names, per-file audio-track order, wrong-language rejection,
  explicit invalid indexes, existing-output skipping, recursive discovery and
  generated-subtitle exclusion, sequential execution, failures and cancellation.
- The frozen Windows app was operated through its actual GUI: folder mode,
  file masks, pairing preview, batch confirmation and alignment.
- Two copies of the controlled demo WAV/SRT were paired as S01E01 and S01E02.
  Each ran CPU/small/int8, both recognition passes, with no precomputed transcripts.
  Both output SRT files exactly matched `docs/demo/result.srt`; inputs were unchanged.
- Two further episodes were added. Rechecking skipped the two completed results.
  Cancelling S01E03 during recognition prevented S01E04 from starting, produced
  neither new SRT and removed the owned staging directory. Earlier results survived.
- Russian UI and the preview were visually checked at the host display scaling.
- The final ZIP passed archive-integrity and package-version checks. Its extracted
  worker scanned all four demo episodes and returned two skipped and two ready.
- A reduced-height window was checked: the page scrolls and the launch controls
  and log remain reachable instead of being clipped.
- Python compilation and local Markdown link/fence checks passed.
- The release 0.3.0 ZIP was also extracted into a separate folder. Its worker
  returned the expected two skipped / two ready episodes and performed a real
  CPU/small/int8 two-pass alignment whose six cues exactly matched the reference.

The demo model was already cached. A clean Windows installation, CUDA processing
from the portable bundle, long-season endurance and arbitrary subtitle accuracy
were not established by these checks. MKV muxing is not part of this feature.
