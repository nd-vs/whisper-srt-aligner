# Reports and accuracy

## What the statuses mean

| Status | Evidence | Review priority |
| --- | --- | --- |
| `matched` | Word matches from primary recognition | Sample in the player |
| `supplemented` | Timing supplied by supplemental recognition | Check difficult scenes |
| `rescued` | Weak partial match near confirmed neighbors | Review |
| `inferred` | Original timing mapped between confirmed neighbors | Review; not directly heard |
| `dropped` | No safe placement found | Check whether the line belongs in this cut |

Retained lines keep the SRT's wording, punctuation, markup and line breaks. The
output does **not** necessarily retain every input line. Neither pass guarantees
hearing quiet or short speech. Inference is only allowed inside coherent gaps
bracketed by confirmed neighbors; leading/trailing gaps are not extrapolated.

## Practical review

1. Open the HTML report; account for each dropped line. It may be an absent scene,
   a credit, or a genuine missed utterance.
2. Check inferred/rescued lines in your player, especially groups of several lines.
3. Sample the start, after intros/recaps/cuts, and the ending.
4. Check noisy scenes, overlapping speakers, songs and repeated short replies.
5. Use a subtitle editor to restore/retime lines you can verify. Recognition from a
   short isolated clip can help, but it can also hallucinate.

Token coverage measures word matching, not timestamp accuracy. Keeping 100% of
cues does not establish that they are correctly timed. Reports are diagnostic
outputs, not an automatic quality certificate.

## Choosing an approach

| Situation | Starting point |
| --- | --- |
| Same delay everywhere | Player delay or a lighter synchronizer |
| Changed frame rate / timing splits | Try existing synchronizers such as ALASS or ffsubsync |
| Need speech-word evidence while preserving edited SRT text | Try this tool and review its report |
| Need subtitles in another language | Translation/cross-language workflow; not supported here |
| Substantially rewritten/reordered dialogue | Expect manual work; monotonic matching may fail |

[ALASS](https://github.com/kaegi/alass) supports timing splits and different frame
rates. [ffsubsync](https://github.com/smacke/ffsubsync) offers speech-activity-based
sync and an experimental split mode. [stable-ts](https://github.com/jianfch/stable-ts)
and [Subaligner](https://github.com/baxtree/subaligner) offer other alignment workflows.
No controlled head-to-head benchmark is claimed here.

## Demo versus real-world validation

The [included demo](../demo/README.md) is a controlled clean synthetic-speech
example with known timing jumps. Its measurements are not film/TV accuracy scores.
In a private 23-episode English use case, 16,062 dialogue cues were retained only
after additional human review and timing corrections, including eight restored
short cues. That workflow is not a one-command success rate and is not independently
reproducible from copyrighted episodes distributed with this project (none are included).

SRT is the supported format. Automatic filtering handles some release-title/URL
credits, not every translator credit. Listen to the matching language/audio track
before assuming subtitle text is wrong.
