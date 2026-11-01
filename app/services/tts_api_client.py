from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from app.config import DATA_DIR

SETTINGS_PATH = DATA_DIR / "settings.json"
DEFAULT_API_URL = "http://127.0.0.1:8000"


class StoryTTSAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def load_audio_api_settings() -> dict[str, str]:
    defaults = {"url": DEFAULT_API_URL, "api_key": ""}
    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            defaults["url"] = str(payload.get("story_tts_url") or defaults["url"])
            defaults["api_key"] = str(payload.get("story_tts_api_key") or "")
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return defaults


def save_audio_api_settings(url: str, api_key: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    current: dict[str, Any] = {}
    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            current = payload
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    current["story_tts_url"] = url.strip().rstrip("/")
    current["story_tts_api_key"] = api_key.strip()
    temporary = SETTINGS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, SETTINGS_PATH)


class StoryTTSClient:
    """HTTP client for the separate Story-TTS-API repository."""

    def __init__(self, base_url: str, api_key: str, timeout: tuple[int, int] = (15, 90)):
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.timeout = timeout
        if not self.base_url.startswith(("http://", "https://")):
            raise StoryTTSAPIError("URL dịch vụ phải bắt đầu bằng http:// hoặc https://.")
        if not self.api_key:
            raise StoryTTSAPIError("Chưa nhập API key của Story TTS API.")

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _json_request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        try:
            response = requests.request(
                method,
                self.base_url + path,
                headers={**self.headers, **kwargs.pop("headers", {})},
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise StoryTTSAPIError(f"Không kết nối được Story TTS API: {exc}") from exc
        try:
            data = response.json()
        except ValueError:
            data = {}
        if not response.ok:
            detail = data.get("detail") or data.get("error") or response.text[:500]
            raise StoryTTSAPIError(
                f"Story TTS API trả lỗi HTTP {response.status_code}: {detail}",
                response.status_code,
            )
        return data

    def check_connection(self) -> dict[str, Any]:
        return self._json_request("GET", "/v1/voices")

    def create_job(
        self,
        text: str,
        voice: str,
        rate: float,
        chapter_id: str,
    ) -> dict[str, Any]:
        data = self._json_request(
            "POST",
            "/v1/tts",
            json={
                "text": text,
                "voice": voice,
                "rate": rate,
                "chapter_id": chapter_id[:300],
            },
            headers={"Content-Type": "application/json"},
        )
        # The API returns the public job record as the root object.
        if "job_id" not in data:
            raise StoryTTSAPIError("API không trả về job_id hợp lệ.")
        return data

    def get_job(self, job_id: int) -> dict[str, Any]:
        return self._json_request("GET", f"/v1/jobs/{int(job_id)}")

    def download_audio(self, job: dict[str, Any], destination: str | Path) -> Path:
        url = job.get("download_url") or job.get("audio_url")
        if not url:
            # Refresh status once to obtain a fresh signed download URL.
            job = self.get_job(int(job["job_id"]))
            url = job.get("download_url") or job.get("audio_url")
        if not url:
            raise StoryTTSAPIError("AU đã hoàn tất nhưng API chưa cấp đường dẫn tải MP3.")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.stem + ".download" + target.suffix)
        try:
            with requests.get(url, stream=True, timeout=(15, 300)) as response:
                if not response.ok:
                    raise StoryTTSAPIError(
                        f"Không tải được MP3 (HTTP {response.status_code}).",
                        response.status_code,
                    )
                with temporary.open("wb") as output:
                    for block in response.iter_content(chunk_size=1024 * 1024):
                        if block:
                            output.write(block)
            if not temporary.is_file() or temporary.stat().st_size < 128:
                raise StoryTTSAPIError("File MP3 tải về rỗng hoặc không hợp lệ.")
            os.replace(temporary, target)
            return target
        except requests.RequestException as exc:
            raise StoryTTSAPIError(f"Lỗi tải MP3: {exc}") from exc
        finally:
            temporary.unlink(missing_ok=True)

    def wait_for_job(
        self,
        job_id: int,
        on_update=None,
        poll_seconds: float = 3.0,
        timeout_seconds: int = 12 * 60 * 60,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            job = self.get_job(job_id)
            if on_update:
                on_update(job)
            status = job.get("status")
            if status == "completed":
                return job
            if status == "failed":
                raise StoryTTSAPIError(job.get("error") or f"AU {job_id} tạo thất bại.")
            time.sleep(poll_seconds)
        raise StoryTTSAPIError(
            f"Đã chờ AU {job_id} quá {timeout_seconds // 3600} giờ. Tác vụ có thể vẫn chạy trên API; hãy kiểm tra lại lịch sử."
        )
