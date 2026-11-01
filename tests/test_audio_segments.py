import unittest

from app.services.audio_segments import split_audio_segments


class AudioSegmentPreviewTests(unittest.TestCase):
    def test_splits_long_text_into_chunks_no_larger_than_5000(self):
        segments = split_audio_segments("A" * 12000)

        self.assertEqual([item["characters"] for item in segments], [5000, 5000, 2000])
        self.assertTrue(all(item["characters"] <= 5000 for item in segments))
        self.assertEqual([item["index"] for item in segments], [1, 2, 3])

    def test_prefers_a_sentence_boundary_when_it_is_not_too_early(self):
        source = ("A" * 3000) + "。" + ("B" * 3000)
        segments = split_audio_segments(source)

        self.assertEqual(segments[0]["characters"], 3001)
        self.assertEqual(segments[1]["characters"], 3000)
        self.assertEqual(segments[0]["text"][-1], "。")

    def test_keeps_chapter_titles_as_metadata_and_splits_each_chapter(self):
        source = (
            "Chương 1: Khởi đầu\n" + ("A" * 5100)
            + "\n\nChương 2: Tiếp nối\n" + ("B" * 1200)
        )
        segments = split_audio_segments(source)

        self.assertEqual(
            [item["chapter"] for item in segments],
            ["Chương 1: Khởi đầu", "Chương 1: Khởi đầu", "Chương 2: Tiếp nối"],
        )
        self.assertEqual([item["characters"] for item in segments], [5000, 100, 1200])

    def test_empty_input_returns_no_segments(self):
        self.assertEqual(split_audio_segments("  \n\t "), [])

    def test_rejects_invalid_segment_limit(self):
        with self.assertRaises(ValueError):
            split_audio_segments("some text", 0)


if __name__ == "__main__":
    unittest.main()
