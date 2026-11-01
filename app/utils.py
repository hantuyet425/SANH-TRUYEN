from pathlib import Path
import re


def read_text_file(path: str | Path) -> str:
    p = Path(path)
    raw = p.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "gb18030", "big5", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def split_text(text: str, max_chars: int = 3800) -> list[str]:
    """Split on paragraph boundaries where possible; preserve all source text."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        pieces = [para[i:i + max_chars] for i in range(0, len(para), max_chars)] if len(para) > max_chars else [para]
        for piece in pieces:
            candidate = f"{current}\n\n{piece}" if current else piece
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = piece
    if current:
        chunks.append(current)
    return chunks


def split_for_tts(text: str, max_chars: int = 2600) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    result: list[str] = []
    while len(text) > max_chars:
        cut = max(text.rfind(mark, 0, max_chars) for mark in ("。", "！", "？", "!", "?", ".", "；", ";", ",", "，", " "))
        if cut < max_chars // 2:
            cut = max_chars
        else:
            cut += 1
        result.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        result.append(text)
    return result


def parse_drop_files(data: str) -> list[str]:
    """Parse TkDND's Tcl list representation, including paths with spaces/braces."""
    try:
        # Tkinter's splitlist handles escaped paths and braces correctly.
        import tkinter
        return list(tkinter.Tcl().splitlist(data))
    except Exception:
        cleaned = data.strip().strip("{}")
        return [cleaned] if cleaned else []
