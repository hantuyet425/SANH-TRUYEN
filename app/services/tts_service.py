from pathlib import Path
import asyncio
import re
import tempfile

from app.utils import split_for_tts

CHAPTER_RE = re.compile(
    r"(?im)^\s*((?:chương|chapter)\s+[^\n]{1,100}|第[0-9零〇一二三四五六七八九十百千两]+[章节回卷部篇集][^\n]{0,100})\s*$"
)


def split_chapters(text: str) -> list[tuple[str, str]]:
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


async def _save_audio(text: str, voice: str, rate: str, destination: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicate.save(str(destination))


def create_mp3(text: str, voice: str, rate: str, destination: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    pieces = split_for_tts(text, max_chars=2500)
    if not pieces:
        raise RuntimeError("Chương này không có nội dung để đọc.")
    with tempfile.TemporaryDirectory(prefix="sanhtts_") as temp_dir:
        temp = Path(temp_dir)
        part_files: list[Path] = []
        for index, piece in enumerate(pieces, start=1):
            part = temp / f"part_{index:04d}.mp3"
            asyncio.run(_save_audio(piece, voice, rate, part))
            part_files.append(part)
        with target.open("wb") as output:
            for part in part_files:
                output.write(part.read_bytes())
    return target
