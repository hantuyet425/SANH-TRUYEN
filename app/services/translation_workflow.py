from __future__ import annotations

import re

from app.services.chapter_numbering import renumber_chapters


_CHAPTER_LINE_RE = re.compile(
    r"^\s*(?:第[0-9０-９零〇○一二两兩三四五六七八九十百千万萬亿億]+\s*[章节回节節集话話].*"
    r"|(?:Chương|Chapter|Chap\.?|Hồi)\s+[0-9０-９]+.*)$",
    re.IGNORECASE,
)


def split_story_chapters(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Normalize chapter numbers, split at chapter headings, and preserve any preface."""
    normalized, _report = renumber_chapters(text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return normalized, []

    lines = normalized.splitlines(keepends=True)
    starts: list[tuple[int, str]] = []
    offset = 0
    for line in lines:
        title = line.rstrip("\r\n").strip()
        if _CHAPTER_LINE_RE.match(title):
            starts.append((offset, title))
        offset += len(line)

    if not starts:
        return normalized, [("Toàn bộ RAW (không nhận diện tiêu đề chương)", normalized)]

    preface = normalized[:starts[0][0]].strip()
    segments: list[tuple[str, str]] = []
    for index, (start, title) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(normalized)
        content = normalized[start:end].strip()
        if index == 0 and preface:
            content = f"{preface}\n\n{content}"
        if content:
            segments.append((title, content))
    return normalized, segments
