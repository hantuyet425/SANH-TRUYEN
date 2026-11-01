import base64
import unittest
from unittest.mock import patch

from app.services.audio_github_client import (
    AudioGitHubError,
    ensure_audio_credentials,
)


class EnsureAudioCredentialsTests(unittest.TestCase):
    def test_uses_gh_login_and_creates_actions_secret_when_key_is_missing(self):
        token = "gh-test-token"
        key = base64.b64encode(b"x" * 32).decode("ascii")

        with (
            patch(
                "app.services.audio_github_client.load_audio_credentials",
                return_value=(None, None),
            ),
            patch(
                "app.services.audio_github_client._run_github_cli",
                side_effect=[token, ""],
            ) as run_cli,
            patch(
                "app.services.audio_github_client.generate_shared_key",
                return_value=key,
            ),
            patch("app.services.audio_github_client.save_audio_credentials") as save,
        ):
            actual_token, actual_key = ensure_audio_credentials()

        self.assertEqual(actual_token, token)
        self.assertEqual(actual_key, key)
        self.assertEqual(run_cli.call_args_list[0].args[0], [
            "auth", "token", "--hostname", "github.com"
        ])
        self.assertEqual(
            run_cli.call_args_list[1].args[0],
            ["secret", "set", "AUDIO_SHARED_KEY", "--repo",
             "hantuyet425/SANH-TRUYEN-AUDIO", "--app", "actions"],
        )
        self.assertEqual(run_cli.call_args_list[1].kwargs["input_text"], key)
        save.assert_called_once_with(token, key)

    def test_reuses_saved_credentials_when_gh_cli_is_unavailable(self):
        token = "saved-token"
        key = base64.b64encode(b"y" * 32).decode("ascii")

        with (
            patch(
                "app.services.audio_github_client.load_audio_credentials",
                return_value=(token, key),
            ),
            patch(
                "app.services.audio_github_client._run_github_cli",
                side_effect=AudioGitHubError("gh missing"),
            ),
            patch("app.services.audio_github_client.save_audio_credentials") as save,
        ):
            actual = ensure_audio_credentials()

        self.assertEqual(actual, (token, key))
        save.assert_called_once_with(token, key)

    def test_explains_that_gh_login_is_needed_when_no_credentials_exist(self):
        with (
            patch(
                "app.services.audio_github_client.load_audio_credentials",
                return_value=(None, None),
            ),
            patch(
                "app.services.audio_github_client._run_github_cli",
                side_effect=AudioGitHubError("gh missing"),
            ),
            patch("app.services.audio_github_client.save_audio_credentials") as save,
        ):
            with self.assertRaisesRegex(AudioGitHubError, "gh auth login"):
                ensure_audio_credentials()

        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
