from __future__ import annotations

import base64
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.services.audio_github_client import (
    AUDIO_REPOSITORY,
    MAGIC,
    AudioGitHubClient,
    AudioGitHubError,
)


class AudioGitHubClientTests(unittest.TestCase):
    def setUp(self):
        self.key = bytes(range(32))
        self.key_b64 = base64.b64encode(self.key).decode("ascii")
        self.client = AudioGitHubClient("test-token-not-used", self.key_b64)
        self.job_id = "1234567890abcdef"

    def make_artifact(self, members: dict[str, bytes]) -> bytes:
        clear_buffer = io.BytesIO()
        with zipfile.ZipFile(clear_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in members.items():
                archive.writestr(name, data)

        nonce = bytes(range(12))
        ciphertext = AESGCM(self.key).encrypt(nonce, clear_buffer.getvalue(), MAGIC)
        envelope = json.dumps({
            "version": 1,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }).encode("utf-8")

        artifact_buffer = io.BytesIO()
        with zipfile.ZipFile(artifact_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("audio-result.enc", envelope)
        return artifact_buffer.getvalue()

    def test_download_extracts_exactly_one_full_audiobook(self):
        artifact_data = self.make_artifact({
            "audiobook.mp3": b"the-whole-novel",
            "manifest.json": b'{"audio_file":"audiobook.mp3"}',
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
            "audiobook.mp3": b"one-complete-book",
            "manifest.json": b'{"audio_file":"audiobook.mp3"}',
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
            self.assertEqual(
                sorted(path.name for path in Path(temporary).glob("au*.mp3")),
                ["au1.mp3", "au2.mp3"],
            )

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

    def test_client_targets_audio_worker_repository(self):
        self.assertEqual(self.client.repository, AUDIO_REPOSITORY)

    def test_connection_distinguishes_missing_workflow_from_repository_access(self):
        with patch.object(
            self.client,
            "_request",
            side_effect=[
                {"full_name": AUDIO_REPOSITORY},
                AudioGitHubError(
                    "GitHub trả về HTTP 404 tại "
                    "GET /repos/hantuyet425/SANH-TRUYEN-AUDIO/actions/workflows/generate-audio.yml"
                ),
            ],
        ):
            with self.assertRaisesRegex(
                AudioGitHubError,
                "Đã đọc được repository.*không đọc được workflow",
            ):
                self.client.test_connection()

    def test_connection_reports_repository_lookup_failure_separately(self):
        with patch.object(
            self.client,
            "_request",
            side_effect=AudioGitHubError(
                "GitHub trả về HTTP 404 tại GET /repos/hantuyet425/SANH-TRUYEN-AUDIO"
            ),
        ):
            with self.assertRaisesRegex(
                AudioGitHubError,
                "Không đọc được repository",
            ):
                self.client.test_connection()

    def test_connection_rejects_non_active_workflow(self):
        with patch.object(
            self.client,
            "_request",
            side_effect=[
                {"full_name": AUDIO_REPOSITORY},
                {
                    "path": ".github/workflows/generate-audio.yml",
                    "state": "disabled_manually",
                },
            ],
        ):
            with self.assertRaisesRegex(
                AudioGitHubError,
                "disabled_manually",
            ):
                self.client.test_connection()


if __name__ == "__main__":
    unittest.main()
