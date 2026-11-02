from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.audio_github_client import (
    AUDIO_REPOSITORY,
    AUDIO_WORKFLOW,
    AudioGitHubClient,
    AudioGitHubError,
)


class AudioGitHubClientTests(unittest.TestCase):
    def setUp(self):
        self.client = AudioGitHubClient("test-token-not-used")
        self.job_id = "1234567890abcdef"

    def make_artifact(self, members: dict[str, bytes]) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        return buffer.getvalue()

    def test_download_extracts_plain_full_audiobook(self):
        artifact_data = self.make_artifact({
            "au7.mp3": b"the-whole-novel",
            "manifest.json": b'{"audio_file":"au7.mp3"}',
        })
        response = Mock()
        response.content = artifact_data
        response.raise_for_status = Mock()

        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(self.client.session, "get", return_value=response):
                outputs = self.client._download_and_extract(
                    {"id": 9876}, self.job_id, Path(temporary)
                )
            self.assertEqual(len(outputs), 1)
            self.assertEqual(outputs[0].name, "au1.mp3")
            self.assertEqual(outputs[0].parent, Path(temporary))
            self.assertEqual(outputs[0].read_bytes(), b"the-whole-novel")
            self.assertTrue(
                (Path(temporary) / f"audio_{self.job_id[:8]}" / "manifest.json").is_file()
            )

    def test_each_new_audiobook_gets_the_next_au_number(self):
        artifact_data = self.make_artifact({
            "au12.mp3": b"one-complete-book",
            "manifest.json": b'{"audio_file":"au12.mp3"}',
        })
        response = Mock()
        response.content = artifact_data
        response.raise_for_status = Mock()

        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(self.client.session, "get", return_value=response):
                first = self.client._download_and_extract(
                    {"id": 9876}, self.job_id, Path(temporary)
                )
                second = self.client._download_and_extract(
                    {"id": 9877}, "abcdef0123456789", Path(temporary)
                )
            self.assertEqual(first[0].name, "au1.mp3")
            self.assertEqual(second[0].name, "au2.mp3")
            self.assertEqual(first[0].read_bytes(), b"one-complete-book")
            self.assertEqual(second[0].read_bytes(), b"one-complete-book")

    def test_rejects_legacy_chapter_tracks_without_full_audiobook(self):
        artifact_data = self.make_artifact({
            "001_chapter.mp3": b"only-one-chapter",
            "manifest.json": b'{"chapters":1}',
        })
        response = Mock()
        response.content = artifact_data
        response.raise_for_status = Mock()
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(self.client.session, "get", return_value=response):
                with self.assertRaises(AudioGitHubError):
                    self.client._download_and_extract(
                        {"id": 9876}, self.job_id, Path(temporary)
                    )

    def test_wait_for_artifact_searches_past_first_github_page(self):
        first_page = {
            "total_count": 150,
            "artifacts": [
                {"id": index, "name": f"audio-segment-{index}", "expired": False}
                for index in range(100)
            ],
        }
        second_page = {
            "total_count": 150,
            "artifacts": [
                {"id": 98765, "name": "audio-final", "expired": False}
            ],
        }
        with patch.object(
            self.client, "_request", side_effect=[first_page, second_page]
        ) as request:
            artifact = self.client._wait_for_artifact(
                12345, "audio-final", deadline=float("inf")
            )
        self.assertEqual(artifact["id"], 98765)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[0].kwargs["params"],
                         {"per_page": 100, "page": 1})
        self.assertEqual(request.call_args_list[1].kwargs["params"],
                         {"per_page": 100, "page": 2})

    def test_download_latest_completed_audio_reuses_existing_successful_run(self):
        job_id = "abcdef0123456789abcdef0123456789"
        run = {
            "id": 24680,
            "run_number": 12,
            "status": "completed",
            "conclusion": "success",
            "display_title": f"Audio job {job_id}",
        }
        expected = [Path("audio/au1.mp3")]
        with patch.object(
            self.client, "_request", return_value={"workflow_runs": [run]}
        ) as request, patch.object(
            self.client, "_find_artifact",
            return_value={"id": 13579, "name": "au12", "expired": False},
        ) as find_artifact, patch.object(
            self.client, "_download_and_extract", return_value=expected
        ) as download:
            outputs = self.client.download_latest_completed_audio(Path("audio"))
        self.assertEqual(outputs, expected)
        request.assert_called_once()
        find_artifact.assert_called_once_with(24680, "au12")
        download.assert_called_once_with(
            {"id": 13579, "name": "au12", "expired": False},
            job_id,
            Path("audio"),
        )

    def test_client_targets_audio_worker_repository_and_m3_workflow(self):
        self.assertEqual(self.client.repository, AUDIO_REPOSITORY)
        self.assertEqual(AUDIO_WORKFLOW, "generate-audio-mp3.yml")

    def test_connection_distinguishes_missing_workflow_from_repository_access(self):
        with patch.object(
            self.client, "_request",
            side_effect=[
                {"full_name": AUDIO_REPOSITORY},
                AudioGitHubError(
                    "GitHub trả về HTTP 404 tại "
                    "GET /repos/hantuyet425/SANH-TRUYEN-AUDIO/actions/workflows/generate-audio.yml"
                ),
            ],
        ):
            with self.assertRaisesRegex(
                AudioGitHubError, "Đã đọc được repository.*không đọc được workflow"
            ):
                self.client.test_connection()

    def test_connection_reports_repository_lookup_failure_separately(self):
        with patch.object(
            self.client, "_request",
            side_effect=AudioGitHubError(
                "GitHub trả về HTTP 404 tại GET /repos/hantuyet425/SANH-TRUYEN-AUDIO"
            ),
        ):
            with self.assertRaisesRegex(AudioGitHubError, "Không đọc được repository"):
                self.client.test_connection()

    def test_connection_rejects_non_active_workflow(self):
        with patch.object(
            self.client, "_request",
            side_effect=[
                {"full_name": AUDIO_REPOSITORY},
                {
                    "path": ".github/workflows/generate-audio-mp3.yml",
                    "state": "disabled_manually",
                },
            ],
        ):
            with self.assertRaisesRegex(AudioGitHubError, "disabled_manually"):
                self.client.test_connection()


if __name__ == "__main__":
    unittest.main()
