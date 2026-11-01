import re

CHAPTER_RE = re.compile(
    r"(?im)^\s*((?:chương|chapter)\s+[^\n]{1,100}|第[0-9零〇一二三四五六七八九十百千两]+[章节回卷部篇集][^\n]{0,100})\s*$"
)


def split_chapters(text: str) -> list[tuple[str, str]]:
    """Keep chapter boundaries so the remote TTS service returns one AU per chapter."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    matches = list(CHAPTER_RE.finditer(text))
    if not matches:
        return [("Toàn bộ truyện", text)] if text else []
    chapters: list[tuple[str, str]] = []
    if matches[0].start() > 0 and text[:matches[0].start()].strip():
        chapters.append(("Phần mở đầu", text[:matches[0].start()].strip()))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(1).strip()
        body = text[match.end():end].strip()
        if body:
            chapters.append((title, body))
    return chapters
