import unittest

from app.utils import split_text, split_for_tts
from app.services.tts_service import split_chapters


class CoreTests(unittest.TestCase):
    def test_split_text_keeps_all_content(self):
        source = "第一段。" * 1000 + "\n\n第二段。" * 1000
        chunks = split_text(source, max_chars=300)
        self.assertTrue(chunks)
        self.assertEqual("\n\n".join(chunks).replace("\n\n", ""), source.replace("\n\n", ""))
        self.assertTrue(all(len(chunk) <= 300 for chunk in chunks))

    def test_split_for_tts_respects_limit(self):
        chunks = split_for_tts("Xin chào. " * 500, max_chars=100)
        self.assertTrue(chunks)
        self.assertTrue(all(len(chunk) <= 100 for chunk in chunks))

    def test_split_chapters(self):
        source = "Chương 1: Mở đầu\nNội dung một.\n\nChương 2: Tiếp tục\nNội dung hai."
        chapters = split_chapters(source)
        self.assertEqual(len(chapters), 2)
        self.assertIn("Nội dung một", chapters[0][1])
        self.assertIn("Nội dung hai", chapters[1][1])


if __name__ == "__main__":
    unittest.main()
