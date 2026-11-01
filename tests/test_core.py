import unittest

from app.utils import split_text, split_for_tts
from app.services.tts_service import split_chapters
from app.services.chapter_numbering import renumber_chapters, count_chapters


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

    def test_continuous_numbering_across_volumes(self):
        source = (
            "第一卷\n第一章 开始\n内容一。\n第二章 继续\n内容二。\n"
            "第二卷\n第一章 再开始\n内容三。\n第二章 结束\n内容四。"
        )
        normalized, report = renumber_chapters(source)
        self.assertIn("第一卷", normalized)
        self.assertIn("第二卷", normalized)
        self.assertIn("第一章 开始", normalized)
        self.assertIn("第二章 继续", normalized)
        self.assertIn("第三章 再开始", normalized)
        self.assertIn("第四章 结束", normalized)
        self.assertEqual(report["chapter_count"], 4)
        self.assertEqual(report["changed_count"], 2)
        self.assertEqual(report["reset_count"], 1)

    def test_continuous_numbering_for_vietnamese_and_start_offset(self):
        source = "Quyển 1\nChương 1: Mở đầu\nA\nChương 2: Tiếp\nB\nQuyển 2\nChương 1: Tiếp tục"
        normalized, report = renumber_chapters(source, start_number=10)
        self.assertIn("Quyển 1", normalized)
        self.assertIn("Quyển 2", normalized)
        self.assertIn("Chương 10: Mở đầu", normalized)
        self.assertIn("Chương 11: Tiếp", normalized)
        self.assertIn("Chương 12: Tiếp tục", normalized)
        self.assertEqual(count_chapters(normalized), 3)
        self.assertEqual(report["reset_count"], 1)

    def test_chinese_numeral_conversion(self):
        normalized, report = renumber_chapters("第十二章\nA\n第一章\nB", start_number=12)
        self.assertIn("第十二章", normalized)
        self.assertIn("第十三章", normalized)
        self.assertEqual(report["chapter_count"], 2)


if __name__ == "__main__":
    unittest.main()
