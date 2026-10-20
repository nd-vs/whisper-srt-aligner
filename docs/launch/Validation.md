# Local validation — 2026-10-20

These checks were performed on Windows/Python 3.12.10. They are not external-user
testing or the remote CI result for a published commit.

| Check | Observed result |
| --- | --- |
| Unit suite, including the existing CP1252 regression | 25 passed |
| Compilation of package and scripts | Passed |
| Markdown local link targets and fenced blocks | Passed |
| Own 57-second audio through the real `sync --complete` CPU/small/int8 command | 6/6 original texts retained, no manual retiming |
| Comparison video | 57 seconds; inspected a rendered frame, no clipped caption text at the checked frame |
| Wheel installation in a new venv, no system site-packages | Passed |
| Cached alignment through installed wheel | Exact match with published example |
| Full dependency installation and CPU transcription in that venv | Passed after the PyAV constraint; exact same SRT |
| `pip check` in the new venv | No broken requirements |
| Local wiki export with rewritten links | Passed; not pushed |

## A real fresh-install failure found

The first fresh environment resolved PyAV 19.0.1 with faster-whisper 1.2.1.
Audio decoding failed at `av.open(..., metadata_errors="ignore")` because PyAV 19
removed that keyword. This is also documented in
[upstream issue 1589](https://github.com/SYSTRAN/faster-whisper/issues/1589).
The package now requires `av>=11,<19`; the retest resolved 18.1.0 and succeeded.

The successful fresh runtime used faster-whisper 1.2.1, CTranslate2 4.8.3,
PyAV 18.1.0, huggingface-hub 2.2.0, tokenizers 0.23.3, onnxruntime 1.31.0,
and NumPy 2.5.4. The separately recorded demo measurement used the versions in
[measurements.json](../demo/measurements.json). Its 8.83-second timing should not
be attributed to the fresh-environment retest.

## Not yet verified

- A person unfamiliar with the project installing from the README.
- Linux/macOS runtime installation and transcription in this change.
- First model download in a completely empty cache (the local `small` model was cached).
- GUI usability, since there is no GUI in this release.
- General accuracy on unseen real media or a head-to-head competitor benchmark.

Do not turn these limits into marketing claims. Record real feedback in the
[first-run study](First-user-study.md) after volunteer participation is approved.
