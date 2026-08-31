from __future__ import annotations

import html
import re
import unicodedata


TAG_PATTERN = re.compile(r"<[^>]+>|\{[^}]+\}")
WORD_PATTERN = re.compile(r"[^\W_]+(?:['’][^\W_]+)*|\d+", re.UNICODE)
TOKEN_ALIASES = {
    "ok": "okay",
    "alright": "allright",
    "allright": "allright",
    "cos": "because",
    "cause": "because",
}


def normalize_token(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().replace("’", "'")
    normalized = normalized.replace("'", "")
    return TOKEN_ALIASES.get(normalized, normalized)


def tokenize(value: str) -> list[str]:
    cleaned = html.unescape(TAG_PATTERN.sub(" ", value))
    return [normalize_token(match.group(0)) for match in WORD_PATTERN.finditer(cleaned)]


def visible_text(value: str) -> str:
    return html.unescape(TAG_PATTERN.sub("", value)).strip()
