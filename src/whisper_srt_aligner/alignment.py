from __future__ import annotations

import difflib
from dataclasses import replace

from .models import (
    AlignedCue,
    AlignmentConfig,
    AlignmentResult,
    SubtitleCue,
    TimedWord,
)
from .subtitles import format_timestamp
from .text import visible_text


MINIMUM_STRONG_BLOCK_SIZE = 2
MINIMUM_MATCHED_TOKENS = 2
MAXIMUM_CLUSTER_TIME_GAP = 8.0
MINIMUM_CLUSTER_TIME_GAP = 2.5
MAXIMUM_TARGET_SPAN_FACTOR = 2.2
MINIMUM_TARGET_SPAN = 6.0
CHARACTERS_PER_SECOND = 8.0
MINIMUM_TOKEN_DURATION = 0.12
MAXIMUM_TOKEN_DURATION = 0.45
START_PADDING = 0.06
END_PADDING = 0.10
MINIMUM_READING_DURATION = 0.55
MAXIMUM_READING_DURATION = 5.5
CHARACTERS_PER_READING_SECOND = 20.0
OVERLAP_GAP = 0.04


Match = tuple[int, int, int]


def _select_coherent_cluster(
    cue: SubtitleCue,
    matches: list[Match],
    timed_words: list[TimedWord],
) -> list[Match]:
    if not matches:
        return []
    clusters: list[list[Match]] = [[matches[0]]]
    maximum_time_gap = max(
        MINIMUM_CLUSTER_TIME_GAP,
        min(MAXIMUM_CLUSTER_TIME_GAP, (cue.end - cue.start) * 1.5),
    )
    maximum_word_gap = max(10, len(cue.tokens) * 3)
    for match in matches[1:]:
        previous_match = clusters[-1][-1]
        previous_word = timed_words[previous_match[1]]
        current_word = timed_words[match[1]]
        if (
            current_word.start - previous_word.end <= maximum_time_gap
            and match[1] - previous_match[1] <= maximum_word_gap
        ):
            clusters[-1].append(match)
        else:
            clusters.append([match])
    return max(
        clusters,
        key=lambda cluster: (
            sum(1 for _, _, block_size in cluster if block_size >= MINIMUM_STRONG_BLOCK_SIZE),
            len(cluster),
            -(timed_words[cluster[-1][1]].end - timed_words[cluster[0][1]].start),
        ),
    )


def _is_accepted(
    cue: SubtitleCue,
    matched_count: int,
    strong_count: int,
    minimum_coverage: float,
) -> bool:
    coverage = matched_count / max(1, len(cue.tokens))
    return (
        strong_count >= min(MINIMUM_MATCHED_TOKENS, len(cue.tokens))
        or (matched_count >= MINIMUM_MATCHED_TOKENS and coverage >= minimum_coverage)
        or (len(cue.tokens) <= MINIMUM_MATCHED_TOKENS and matched_count == len(cue.tokens))
    )


def _create_matched_cue(
    cue: SubtitleCue,
    matches: list[Match],
    timed_words: list[TimedWord],
    strong_count: int,
) -> AlignedCue | None:
    unique_word_positions = sorted({hypothesis_position for _, hypothesis_position, _ in matches})
    first_token_position = min(token_position for token_position, _, _ in matches)
    last_token_position = max(token_position for token_position, _, _ in matches)
    first_word = timed_words[unique_word_positions[0]]
    last_word = timed_words[unique_word_positions[-1]]
    maximum_expected_span = max(
        MINIMUM_TARGET_SPAN,
        (cue.end - cue.start) * MAXIMUM_TARGET_SPAN_FACTOR,
        len(visible_text(cue.text)) / CHARACTERS_PER_SECOND,
    )
    if last_word.end - first_word.start > maximum_expected_span:
        return None

    source_duration_per_token = max(
        MINIMUM_TOKEN_DURATION,
        min(MAXIMUM_TOKEN_DURATION, (cue.end - cue.start) / len(cue.tokens)),
    )
    start = first_word.start - first_token_position * source_duration_per_token - START_PADDING
    missing_suffix = len(cue.tokens) - 1 - last_token_position
    end = last_word.end + missing_suffix * source_duration_per_token + END_PADDING
    minimum_duration = min(
        MAXIMUM_READING_DURATION,
        max(MINIMUM_READING_DURATION, len(visible_text(cue.text)) / CHARACTERS_PER_READING_SECOND),
    )
    if end - start < minimum_duration:
        expansion = (minimum_duration - (end - start)) / 2
        start -= expansion
        end += expansion
    return AlignedCue(
        source_index=cue.source_index,
        source_start=cue.start,
        source_end=cue.end,
        start=max(0.0, start),
        end=end,
        text=cue.text,
        status="matched",
        matched_tokens=len(matches),
        total_tokens=len(cue.tokens),
        strong_matches=strong_count,
    )


def _rescue_weak_cues(
    cues: list[SubtitleCue],
    output_by_position: dict[int, AlignedCue],
    weak_positions: set[int],
    config: AlignmentConfig,
) -> None:
    for cue_position in sorted(weak_positions):
        previous_positions = [position for position in output_by_position if position < cue_position]
        next_positions = [position for position in output_by_position if position > cue_position]
        if not previous_positions or not next_positions:
            continue
        previous_position = max(previous_positions)
        next_position = min(next_positions)
        if (
            cue_position - previous_position > config.maximum_neighbor_distance
            or next_position - cue_position > config.maximum_neighbor_distance
        ):
            continue
        previous = output_by_position[previous_position]
        following = output_by_position[next_position]
        if following.start - previous.end > config.maximum_rescue_gap:
            continue
        cue = cues[cue_position]
        source_span = following.source_start - previous.source_end
        target_span = following.start - previous.end
        if source_span <= 0 or target_span <= 0.2:
            continue
        relative_start = (cue.start - previous.source_end) / source_span
        relative_end = (cue.end - previous.source_end) / source_span
        output_by_position[cue_position] = AlignedCue(
            source_index=cue.source_index,
            source_start=cue.start,
            source_end=cue.end,
            start=previous.end + max(0.0, relative_start) * target_span,
            end=previous.end + min(1.0, relative_end) * target_span,
            text=cue.text,
            status="rescued",
            matched_tokens=0,
            total_tokens=len(cue.tokens),
            strong_matches=0,
        )


def _remove_overlaps(cues: list[AlignedCue], minimum_duration: float) -> None:
    for index, cue in enumerate(cues):
        cue.start = max(0.0, cue.start)
        cue.end = max(cue.start + minimum_duration, cue.end)
        if index == 0:
            continue
        previous = cues[index - 1]
        if previous.end + OVERLAP_GAP <= cue.start:
            continue
        boundary = (previous.end + cue.start) / 2
        previous.end = max(previous.start + 0.2, boundary - OVERLAP_GAP / 2)
        cue.start = max(previous.end + OVERLAP_GAP, boundary + OVERLAP_GAP / 2)


def _infer_unmatched_cues(
    cues: list[SubtitleCue],
    output_by_position: dict[int, AlignedCue],
    config: AlignmentConfig,
) -> None:
    missing_positions = [position for position in range(len(cues)) if position not in output_by_position]
    groups: list[list[int]] = []
    for position in missing_positions:
        if groups and position == groups[-1][-1] + 1:
            groups[-1].append(position)
        else:
            groups.append([position])

    for group in groups:
        if len(group) > config.maximum_inference_cues:
            continue
        previous_positions = [position for position in output_by_position if position < group[0]]
        next_positions = [position for position in output_by_position if position > group[-1]]
        if not previous_positions or not next_positions:
            continue
        previous_position = max(previous_positions)
        next_position = min(next_positions)
        previous = output_by_position[previous_position]
        following = output_by_position[next_position]
        source_span = following.source_start - previous.source_end
        target_span = following.start - previous.end
        if (
            source_span <= 0
            or source_span > config.maximum_inference_source_span
            or target_span <= 0
        ):
            continue
        scale = target_span / source_span
        if not config.minimum_inference_scale <= scale <= config.maximum_inference_scale:
            continue
        for position in group:
            cue = cues[position]
            relative_start = (cue.start - previous.source_end) / source_span
            relative_end = (cue.end - previous.source_end) / source_span
            output_by_position[position] = AlignedCue(
                source_index=cue.source_index,
                source_start=cue.start,
                source_end=cue.end,
                start=previous.end + max(0.0, relative_start) * target_span,
                end=previous.end + min(1.0, relative_end) * target_span,
                text=cue.text,
                status="inferred",
                matched_tokens=0,
                total_tokens=len(cue.tokens),
                strong_matches=0,
            )


def _build_result(
    cues: list[SubtitleCue],
    output_by_position: dict[int, AlignedCue],
    reference_tokens: int,
    whisper_tokens: int,
    matched_reference_tokens: int,
    minimum_duration: float,
) -> AlignmentResult:
    output = [output_by_position[position] for position in sorted(output_by_position)]
    _remove_overlaps(output, minimum_duration)
    kept_positions = set(output_by_position)
    dropped = [cue for position, cue in enumerate(cues) if position not in kept_positions]
    summary = {
        "source_cues": len(cues),
        "output_cues": len(output),
        "dropped_cues": len(dropped),
        "rescued_cues": sum(cue.status == "rescued" for cue in output),
        "inferred_cues": sum(cue.status == "inferred" for cue in output),
        "supplemented_cues": sum(cue.status == "supplemented" for cue in output),
        "reference_tokens": reference_tokens,
        "whisper_tokens": whisper_tokens,
        "matched_reference_tokens": matched_reference_tokens,
        "token_coverage": round(matched_reference_tokens / max(1, reference_tokens), 4),
        "first_output_time": round(output[0].start, 3) if output else None,
        "last_output_time": round(output[-1].end, 3) if output else None,
        "dropped": [
            {
                "source_index": cue.source_index,
                "source_start": format_timestamp(cue.start),
                "text": cue.text.replace("\n", " "),
            }
            for cue in dropped
        ],
    }
    return AlignmentResult(cues=output, dropped=dropped, summary=summary)


def align_cues(
    cues: list[SubtitleCue],
    timed_words: list[TimedWord],
    config: AlignmentConfig | None = None,
) -> AlignmentResult:
    if not cues:
        raise ValueError("The subtitle contains no usable cues")
    if not timed_words:
        raise ValueError("The transcript contains no timed words")
    config = config or AlignmentConfig()

    reference_tokens: list[str] = []
    cue_reference_offsets: list[int] = []
    for cue in cues:
        cue_reference_offsets.append(len(reference_tokens))
        reference_tokens.extend(cue.tokens)
    hypothesis_tokens = [word.token for word in timed_words]
    # Long transcripts contain hundreds of repeated glue words. Treating every
    # occurrence as an anchor can pull a cue toward a similar sentence in a
    # different scene, so SequenceMatcher's popular-token suppression stays on.
    matcher = difflib.SequenceMatcher(None, reference_tokens, hypothesis_tokens, autojunk=True)

    token_mapping: dict[int, tuple[int, int]] = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            token_mapping[block.a + offset] = (block.b + offset, block.size)

    output_by_position: dict[int, AlignedCue] = {}
    weak_positions: set[int] = set()
    for cue_position, cue in enumerate(cues):
        reference_offset = cue_reference_offsets[cue_position]
        matches: list[Match] = []
        for token_position in range(len(cue.tokens)):
            mapped = token_mapping.get(reference_offset + token_position)
            if mapped is not None:
                hypothesis_position, block_size = mapped
                matches.append((token_position, hypothesis_position, block_size))
        matches = _select_coherent_cluster(cue, matches, timed_words)
        matched_count = len(matches)
        strong_count = sum(
            1 for _, _, block_size in matches if block_size >= MINIMUM_STRONG_BLOCK_SIZE
        )
        if not _is_accepted(cue, matched_count, strong_count, config.minimum_coverage):
            if matched_count:
                weak_positions.add(cue_position)
            continue
        aligned = _create_matched_cue(cue, matches, timed_words, strong_count)
        if aligned is not None:
            output_by_position[cue_position] = aligned

    _rescue_weak_cues(cues, output_by_position, weak_positions, config)
    if config.infer_unmatched:
        _infer_unmatched_cues(cues, output_by_position, config)
    matched_reference_tokens = len(token_mapping)
    return _build_result(
        cues=cues,
        output_by_position=output_by_position,
        reference_tokens=len(reference_tokens),
        whisper_tokens=len(hypothesis_tokens),
        matched_reference_tokens=matched_reference_tokens,
        minimum_duration=config.minimum_duration,
    )


def merge_alignment_results(
    cues: list[SubtitleCue],
    primary: AlignmentResult,
    supplemental: AlignmentResult,
    config: AlignmentConfig | None = None,
) -> AlignmentResult:
    config = config or AlignmentConfig(infer_unmatched=True)
    position_by_source_index = {cue.source_index: position for position, cue in enumerate(cues)}
    output_by_position: dict[int, AlignedCue] = {}
    for cue in primary.cues:
        position = position_by_source_index.get(cue.source_index)
        if position is not None:
            output_by_position[position] = replace(cue)
    for cue in supplemental.cues:
        position = position_by_source_index.get(cue.source_index)
        primary_cue = output_by_position.get(position) if position is not None else None
        if position is not None and (
            primary_cue is None
            or (primary_cue.status == "rescued" and cue.status == "matched")
        ):
            output_by_position[position] = replace(cue, status="supplemented")
    if config.infer_unmatched:
        _infer_unmatched_cues(cues, output_by_position, config)
    primary_summary = primary.summary
    supplemental_summary = supplemental.summary
    return _build_result(
        cues=cues,
        output_by_position=output_by_position,
        reference_tokens=int(primary_summary["reference_tokens"]),
        whisper_tokens=int(primary_summary["whisper_tokens"]),
        matched_reference_tokens=max(
            int(primary_summary["matched_reference_tokens"]),
            int(supplemental_summary["matched_reference_tokens"]),
        ),
        minimum_duration=config.minimum_duration,
    )
