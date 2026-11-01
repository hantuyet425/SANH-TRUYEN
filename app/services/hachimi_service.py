from pathlib import Path
from typing import Callable

from app.config import MODELS_DIR
from app.utils import split_text


class HachimiTranslator:
    def __init__(self, model_id: str, progress: Callable[[str], None] | None = None):
        self.model_id = model_id
        self.progress = progress or (lambda _message: None)
        self.tokenizer = None
        self.translator = None

    def load(self) -> None:
        try:
            from huggingface_hub import snapshot_download
            from transformers import AutoTokenizer
            import ctranslate2
        except ImportError as exc:
            raise RuntimeError(
                "Thiếu thư viện dịch cục bộ. Hãy chạy install-local-ai.bat trước."
            ) from exc

        self.progress("Đang tải/kiểm tra mô hình Hachimi (lần đầu có thể mất vài phút)...")
        model_path = Path(snapshot_download(
            repo_id=self.model_id,
            cache_dir=str(MODELS_DIR / "huggingface"),
            allow_patterns=[
                "config.json", "source.spm", "target.spm", "vocab.json",
                "tokenizer_config.json", "special_tokens_map.json", "ct2-int8_float32/*",
            ],
        ))
        ct2_path = model_path / "ct2-int8_float32"
        if not ct2_path.exists():
            raise RuntimeError("Repo mô hình không có thư mục ct2-int8_float32; không thể chạy bản CPU INT8 theo cấu hình này.")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.translator = ctranslate2.Translator(str(ct2_path), device="cpu", compute_type="int8_float32")
        self.progress("Đã nạp HachimiMT-60 vào CPU.")

    def translate(self, text: str) -> str:
        if self.translator is None or self.tokenizer is None:
            self.load()
        # Hachimi's encoder has a finite context window. Split long chapter chunks
        # before tokenization so no tail of the source text is silently truncated.
        pieces = split_text(text, max_chars=380) or [text]
        translated_pieces: list[str] = []
        for piece in pieces:
            source_ids = self.tokenizer(piece, truncation=False).input_ids
            if len(source_ids) > 500:
                # A very token-dense paragraph gets one more conservative split.
                smaller = split_text(piece, max_chars=220)
                for part in smaller:
                    ids = self.tokenizer(part, truncation=False).input_ids
                    tokens = self.tokenizer.convert_ids_to_tokens(ids)
                    result = self.translator.translate_batch([tokens], beam_size=2, max_decoding_length=256)
                    out_ids = self.tokenizer.convert_tokens_to_ids(result[0].hypotheses[0])
                    translated_pieces.append(self.tokenizer.decode(out_ids, skip_special_tokens=True).strip())
                continue
            source_tokens = self.tokenizer.convert_ids_to_tokens(source_ids)
            result = self.translator.translate_batch(
                [source_tokens], beam_size=2, max_decoding_length=256
            )
            output_tokens = result[0].hypotheses[0]
            output_ids = self.tokenizer.convert_tokens_to_ids(output_tokens)
            translated_pieces.append(self.tokenizer.decode(output_ids, skip_special_tokens=True).strip())
        return "\n\n".join(part for part in translated_pieces if part)
