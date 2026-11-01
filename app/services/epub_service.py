from pathlib import Path


def convert_epub_to_txt(epub_path: str | Path, output_path: str | Path) -> Path:
    try:
        import epub2txt as epub2txt_module
        epub2txt = epub2txt_module.epub2txt
    except ImportError as exc:
        raise RuntimeError("Chưa cài epub2txt. Hãy chạy install.bat hoặc pip install -r requirements.txt.") from exc

    source = Path(epub_path)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        chapters = epub2txt(str(source), outputlist=True)
    except Exception as exc:
        raise RuntimeError(f"Không đọc được EPUB: {exc}") from exc

    if isinstance(chapters, (list, tuple)):
        pieces = []
        titles = getattr(epub2txt_module, "content_titles", []) or []
        for index, item in enumerate(chapters):
            if isinstance(item, dict):
                title = str(item.get("title") or "")
                content = str(item.get("content") or item.get("text") or "")
            else:
                title = str(titles[index]) if index < len(titles) else ""
                content = str(item)
            if title:
                pieces.append(f"\n\n{title}\n\n{content}")
            else:
                pieces.append(content)
        text = "\n\n".join(piece.strip() for piece in pieces if piece.strip())
    else:
        text = str(chapters or "")
    if not text.strip():
        # Compatibility fallback for package versions returning a flat string.
        text = str(epub2txt(str(source)))
    if not text.strip():
        raise RuntimeError("EPUB không chứa văn bản có thể trích xuất.")
    target.write_text(text, encoding="utf-8-sig")
    return target
