# Announcement drafts

Not posted. Choose a community that permits project announcements and follow its
rules. One relevant demonstration is preferable to repeated generic promotions.

## Short post

**Subtitle timing changes after an intro or a cut? Keep the text, rebuild the timing.**

I built whisper-srt-aligner for an awkward case: I already had edited SRT subtitles,
but they didn't match the timing of my video release. It uses faster-whisper word
timestamps as anchors while retaining the original subtitle text for kept lines.

It runs locally, supports episode batches and writes a report of dropped or
estimated lines. A CPU-first example and a reproducible before/after demo are in
the README: https://github.com/nd-vs/whisper-srt-aligner

It's an early Python CLI, not a one-click app. Same-language audio/SRT only; noisy
or very short lines can still need manual review. The demo uses clean synthetic
speech, so I'm especially interested in feedback from real-world first runs.

## Longer post / project discussion

Title: **I made a CLI to retime existing SRTs using speech, with reports for uncertain lines**

I wanted to keep an existing subtitle file's wording, punctuation and line breaks,
but rebuild its timing from the video's actual speech. A constant delay was not
enough for the releases I was working with.

whisper-srt-aligner combines word matching with an optional two-pass recognition
mode. It can fill some internal gaps between confirmed anchors, but does not hide
that uncertainty: reports distinguish matched, supplemented, rescued, inferred and
dropped cues. There is batch episode pairing and reusable recognition caches.

It is not the only solution: ALASS and ffsubsync can also handle timing problems,
and forced-alignment tools offer other approaches. I have not established a broad
benchmark advantage. This project's focus is an SRT-preserving workflow with
inspectable decisions.

The README includes a controlled 57-second example you can reproduce on a CPU,
including the input audio, source/result SRTs and transcripts. No film footage is
included. It requires Python and FFmpeg; the model downloads on first use.

I'd appreciate feedback on installation and the first result: where did you get
stuck, which lines needed manual correction, and was the report understandable?

Repository: https://github.com/nd-vs/whisper-srt-aligner

## After posting

Record the actual post URL/date and resulting traffic. Do not infer human adoption
from clone counts or fabricate user quotes. Do not post promotional messages in
unrelated projects' issues or mislabel this as an ffsubsync/ALASS integration.
