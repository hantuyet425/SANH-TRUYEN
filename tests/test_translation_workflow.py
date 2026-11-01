import unittest

from app.services.translation_workflow import split_story_chapters


class TranslationWorkflowTests(unittest.TestCase):
    def test_preserves_preface_and_splits_chapters_across_volumes(self):
        raw = (
            "Lời dẫn của truyện.\n\n"
            "第一卷\n"
            "第一章 Mở đầu\nNội dung chương một.\n"
            "第二章 Tiếp tục\nNội dung chương hai.\n"
            "第二卷\n"
            "第一章 Quyển mới\nNội dung chương ba."
        )

        normalized, chapters = split_story_chapters(raw)

        self.assertIn("Lời dẫn của truyện.", chapters[0][1])
        self.assertEqual(len(chapters), 3)
        self.assertIn("第一章 Mở đầu", chapters[0][1])
        self.assertIn("第二章 Tiếp tục", chapters[1][1])
        self.assertIn("第三章 Quyển mới", chapters[2][1])
        self.assertIn("第一卷", normalized)
        self.assertIn("第二卷", normalized)

    def test_volume_headings_are_not_counted_as_chapters(self):
        raw = "第一卷\nNgoại truyện chưa đánh số chương.\n第二卷\nPhần tiếp theo."

        normalized, chapters = split_story_chapters(raw)

        self.assertEqual(normalized, raw)
        self.assertEqual(len(chapters), 1)
        self.assertIn("第一卷", chapters[0][1])
        self.assertIn("第二卷", chapters[0][1])

    def test_vietnamese_chapter_headings_are_split(self):
        raw = "Chương 1: Mở đầu\nA\n\nChương 2: Tiếp tục\nB"

        _normalized, chapters = split_story_chapters(raw)

        self.assertEqual(len(chapters), 2)
        self.assertIn("Chương 1", chapters[0][1])
        self.assertIn("Chương 2", chapters[1][1])

    def test_empty_text_returns_no_chapters(self):
        normalized, chapters = split_story_chapters(" \n ")

        self.assertEqual(normalized, "")
        self.assertEqual(chapters, [])

    def test_unrecognized_text_is_preserved_as_one_segment(self):
        raw = "Đoạn văn chưa có tiêu đề chương.\nVẫn phải giữ đầy đủ nội dung."

        normalized, chapters = split_story_chapters(raw)

        self.assertEqual(normalized, raw)
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0][1], raw)


if __name__ == "__main__":
    unittest.main()
