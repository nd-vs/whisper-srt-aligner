from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .models import AlignmentResult
from .subtitles import format_timestamp


REPORT_STYLE = """
body { font: 15px/1.45 system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #1f2328; }
h1, h2 { line-height: 1.2; }
.summary { display: flex; flex-wrap: wrap; gap: .75rem; }
.metric { background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 8px; padding: .7rem 1rem; }
.metric strong { display: block; font-size: 1.35rem; }
table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
th, td { border: 1px solid #d0d7de; padding: .45rem .6rem; text-align: left; vertical-align: top; }
th { background: #f6f8fa; }
.dropped { color: #9a6700; }
.rescued { color: #8250df; }
.supplemented { color: #0969da; }
.inferred { color: #bf3989; }
code { word-break: break-all; }
"""


def build_report_payload(
    result: AlignmentResult,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "metadata": metadata or {},
        "summary": result.summary,
        "cues": [
            {
                "source_index": cue.source_index,
                "source_start": round(cue.source_start, 3),
                "source_end": round(cue.source_end, 3),
                "start": round(cue.start, 3),
                "end": round(cue.end, 3),
                "status": cue.status,
                "matched_tokens": cue.matched_tokens,
                "total_tokens": cue.total_tokens,
                "coverage": round(cue.coverage, 3),
                "text": cue.text,
            }
            for cue in result.cues
        ],
        "dropped": result.summary["dropped"],
    }


def write_json_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    metadata = payload.get("metadata") or {}
    dropped_rows = "".join(
        "<tr>"
        f"<td>{item['source_index']}</td>"
        f"<td>{html.escape(item['source_start'])}</td>"
        f"<td>{html.escape(item['text'])}</td>"
        "</tr>"
        for item in payload.get("dropped", [])
    ) or '<tr><td colspan="3">None</td></tr>'
    adjusted = [
        cue
        for cue in payload.get("cues", [])
        if cue["status"] in {"rescued", "supplemented", "inferred"}
    ]
    adjusted_rows = "".join(
        "<tr>"
        f"<td>{cue['source_index']}</td>"
        f"<td>{format_timestamp(cue['start'])}</td>"
        f"<td class=\"{html.escape(cue['status'])}\">{html.escape(cue['status'])}</td>"
        f"<td>{html.escape(cue['text'])}</td>"
        "</tr>"
        for cue in adjusted
    ) or '<tr><td colspan="4">None</td></tr>'
    source = html.escape(str(metadata.get("subtitle", "")))
    transcript = html.escape(str(metadata.get("transcript", "")))
    document = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Whisper SRT alignment report</title>
<style>{REPORT_STYLE}</style>
<body>
<h1>Whisper SRT alignment report</h1>
<p>Subtitle: <code>{source}</code><br>Transcript: <code>{transcript}</code></p>
<div class="summary">
  <div class="metric"><strong>{summary['output_cues']}</strong>kept cues</div>
  <div class="metric"><strong>{summary['dropped_cues']}</strong>dropped cues</div>
  <div class="metric"><strong>{summary['rescued_cues']}</strong>rescued cues</div>
  <div class="metric"><strong>{summary['supplemented_cues']}</strong>supplemented cues</div>
  <div class="metric"><strong>{summary['inferred_cues']}</strong>inferred cues</div>
  <div class="metric"><strong>{summary['token_coverage']:.1%}</strong>token coverage</div>
</div>
<h2 class="dropped">Dropped cues</h2>
<table><thead><tr><th>#</th><th>Original time</th><th>Text</th></tr></thead><tbody>{dropped_rows}</tbody></table>
<h2>Adjusted cues</h2>
<table><thead><tr><th>#</th><th>New time</th><th>Status</th><th>Text</th></tr></thead><tbody>{adjusted_rows}</tbody></table>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
