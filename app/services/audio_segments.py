from __future__ import annotations

import re
from typing import Any

MAX_SEGMENT_CHARACTERS = 5000

CHAPTER_RE = re.compile(
    r"(?im)^\s*((?:chương|chapter|chap\.?|hồi)\s+[^\n]{1,100}|"
    r"第[0-9０-９零〇○一二两兩三四五六七八九十百千万萬亿億]+[章节回节節集话話篇卷部][^\n]{0,100})\s*$"
)


def _split_text(text: str, max_chars: int = MAX_SEGMENT_CHARACTERS) -> list[str]:
    """Mirror the worker's 5,000-character, punctuation-aware chunking."""
    if max_chars < 1:
        raise ValueError("max_chars must be a positive integer.")

    text = re.sub(r"\s+", " ", text).strip()
    parts: list[str] = []
    while len(text) > max_chars:
        window = text[:max_chars]
        cut = max(
            window.rfind(mark)
            for mark in ("。", "！", "？", "!", "?", ".", "；", ";", "，", ",", " ")
        )
        if cut < max_chars // 2:
            cut = max_chars
        else:
            cut += 1
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        parts.append(text)
    return [part for part in parts if part]


def split_audio_segments(
    text: str,
    max_chars: int = MAX_SEGMENT_CHARACTERS,
) -> list[dict[str, Any]]:
    """
    Preview the same chapter-aware segments that the audio worker will synthesize.

    Chapter headings are retained as metadata, as in worker/run_job.py; only
    chapter body text is sent to TTS.
    """
    if max_chars < 1:
        raise ValueError("max_chars must be a positive integer.")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    matches = list(CHAPTER_RE.finditer(normalized))
    chapters: list[tuple[str, str]] = []
    if not matches:
        chapters.append(("Toàn bộ truyện", normalized))
    else:
        if normalized[:matches[0].start()].strip():
            chapters.append(("Phần mở đầu", normalized[:matches[0].start()].strip()))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
            body = normalized[match.end():end].strip()
            if body:
                chapters.append((match.group(1).strip(), body))

    result: list[dict[str, Any]] = []
    for chapter_title, body in chapters:
        for chunk in _split_text(body, max_chars):
            result.append({
                "index": len(result) + 1,
                "chapter": chapter_title,
                "text": chunk,
                "characters": len(chunk),
            })
    return result
