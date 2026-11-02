from __future__ import annotations

import base64
import io
import json
import re
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

AUDIO_REPOSITORY = "hantuyet425/SANH-TRUYEN-AUDIO"
AUDIO_WORKFLOW = "generate-audio-mp3.yml"
API_ROOT = "https://api.github.com"
KEYRING_SERVICE = "SANH-TRUYEN-AUDIO"
KEYRING_TOKEN_NAME = "github_pat"
VOICE_IDS = {
    "Nam Minh": "vi-VN-NamMinhNeural",
    "Hoài My": "vi-VN-HoaiMyNeural",
}


class AudioGitHubError(RuntimeError):
    """A safe, user-readable GitHub Audio connection or job error."""


def _move_to_next_numbered_audiobook(source: Path, audio_dir: Path) -> Path:
    """Move one completed audiobook to au1.mp3, au2.mp3, ... without overwriting."""
    highest = 0
    for existing in audio_dir.rglob("au*.mp3"):
        suffix = existing.stem[2:] if existing.stem.lower().startswith("au") else ""
        if suffix.isdigit():
            highest = max(highest, int(suffix))

    index = highest + 1
    while True:
        target = audio_dir / f"au{index}.mp3"
        try:
            # Exclusive creation also protects against two app instances finishing together.
            with target.open("xb"):
                pass
        except FileExistsError:
            index += 1
            continue

        try:
            source.replace(target)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target


def save_audio_credentials(token: str) -> None:
    """Store the GitHub token in Windows Credential Manager."""
    token = token.strip()
    if not token:
        raise AudioGitHubError("Chưa nhập GitHub Personal Access Token.")
    try:
        import keyring
        backend = keyring.get_keyring()
        if getattr(backend, "priority", 0) <= 0:
            raise RuntimeError("No secure credential backend is available.")
        keyring.set_password(KEYRING_SERVICE, KEYRING_TOKEN_NAME, token)
        if keyring.get_password(KEYRING_SERVICE, KEYRING_TOKEN_NAME) != token:
            raise RuntimeError("Credential verification failed.")
        # Remove the obsolete key saved by an older version.
        try:
            keyring.delete_password(KEYRING_SERVICE, "audio_shared_key")
        except Exception:
            pass
    except Exception as exc:
        raise AudioGitHubError(
            "Không lưu được GitHub token vào Windows Credential Manager. "
            "Hãy kiểm tra Windows Credential Manager rồi thử lại."
        ) from exc


def load_audio_credentials() -> str | None:
    try:
        import keyring
        token = keyring.get_password(KEYRING_SERVICE, KEYRING_TOKEN_NAME)
        # Clean up the obsolete AES key left by older desktop versions.
        try:
            keyring.delete_password(KEYRING_SERVICE, "audio_shared_key")
        except Exception:
            pass
        return token
    except Exception as exc:
        raise AudioGitHubError(
            "Không đọc được GitHub token từ Windows Credential Manager."
        ) from exc


class AudioGitHubClient:
    def __init__(self, token: str, repository: str = AUDIO_REPOSITORY):
        self.repository = repository
        self.token = token.strip()
        if not self.token:
            raise AudioGitHubError("Chưa cấu hình GitHub token.")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SANH-TRUYEN-Desktop",
        })

    def _url(self, path: str) -> str:
        return f"{API_ROOT}/repos/{self.repository}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs):
        try:
            response = self.session.request(
                method, self._url(path), timeout=(20, 60), **kwargs
            )
        except requests.RequestException as exc:
            raise AudioGitHubError(
                "Không kết nối được GitHub. Hãy kiểm tra Internet rồi thử lại."
            ) from exc

        if not response.ok:
            try:
                detail = response.json().get("message", "")
            except Exception:
                detail = ""
            if response.status_code in (401, 403):
                raise AudioGitHubError(
                    "GitHub từ chối quyền truy cập. Kiểm tra PAT và hai quyền "
                    "Contents: Read and write, Actions: Read and write."
                )
            if response.status_code == 404:
                endpoint = f"{method.upper()} /repos/{self.repository}/{path.lstrip('/')}".rstrip("/")
                suffix = f" ({detail})" if detail else ""
                raise AudioGitHubError(
                    f"GitHub trả về HTTP 404 tại {endpoint}{suffix}. "
                    "Thông báo này giúp xác định chính xác endpoint không tìm thấy."
                )
            suffix = f" ({detail})" if detail else ""
            raise AudioGitHubError(
                f"GitHub API trả về HTTP {response.status_code}{suffix}"
            )
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise AudioGitHubError("GitHub trả về dữ liệu không đúng định dạng.") from exc

    def test_connection(self) -> None:
        try:
            repo = self._request("GET", "")
        except AudioGitHubError as exc:
            raise AudioGitHubError(
                f"Không đọc được repository {self.repository}. "
                f"Kiểm tra owner/repository và quyền token. Chi tiết: {exc}"
            ) from exc

        if repo.get("full_name", "").lower() != self.repository.lower():
            raise AudioGitHubError(
                "GitHub trả về repository không đúng tên SANH-TRUYEN-AUDIO."
            )

        try:
            workflow = self._request("GET", f"actions/workflows/{AUDIO_WORKFLOW}")
        except AudioGitHubError as exc:
            raise AudioGitHubError(
                f"Đã đọc được repository {self.repository}, nhưng không đọc được "
                f"workflow {AUDIO_WORKFLOW}. Hãy kiểm tra GitHub Actions có được bật "
                "và file workflow có nằm trên nhánh mặc định main hay không. "
                f"Chi tiết: {exc}"
            ) from exc

        expected_path = f".github/workflows/{AUDIO_WORKFLOW}"
        actual_path = str(workflow.get("path") or "").lstrip("/")
        if actual_path and actual_path != expected_path:
            raise AudioGitHubError(
                f"GitHub tìm thấy workflow nhưng đường dẫn trả về là {actual_path}, "
                f"trong khi ứng dụng cần {expected_path}."
            )
        state = workflow.get("state")
        if state and state != "active":
            raise AudioGitHubError(
                f"Workflow {AUDIO_WORKFLOW} hiện có trạng thái {state}, không phải active. "
                "Hãy bật workflow trong tab Actions của repository."
            )

    def _delete_branch(self, branch: str) -> None:
        try:
            self._request("DELETE", f"git/refs/heads/{branch}")
        except AudioGitHubError:
            # The workflow may already have deleted the temporary branch.
            pass

    def _find_run(self, job_id: str, main_sha: str, started_at: datetime):
        data = self._request(
            "GET",
            f"actions/workflows/{AUDIO_WORKFLOW}/runs",
            params={"event": "workflow_dispatch", "branch": "main", "per_page": 50},
        )
        exact_title = f"Audio job {job_id}".casefold()
        for run in data.get("workflow_runs", []):
            title = str(run.get("display_title") or run.get("name") or "").casefold()
            if exact_title in title:
                return run

        # Fallback for GitHub API responses that omit run-name from display_title.
        candidates = []
        for run in data.get("workflow_runs", []):
            created = run.get("created_at")
            if not created or run.get("head_sha") != main_sha:
                continue
            try:
                created_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                continue
            if created_at >= started_at:
                candidates.append(run)
        return candidates[0] if len(candidates) == 1 else None

    def _find_artifact(self, run_id: int, artifact_name: str):
        # GitHub paginates this endpoint (30 items by default). A run with
        # hundreds of TTS segment artifacts can place the final audiobook
        # beyond the first page, so explicitly walk every page.
        per_page = 100
        page = 1
        while True:
            data = self._request(
                "GET",
                f"actions/runs/{run_id}/artifacts",
                params={"per_page": per_page, "page": page},
            )
            artifacts = data.get("artifacts", [])
            for artifact in artifacts:
                if artifact.get("name") == artifact_name and not artifact.get("expired"):
                    return artifact

            total_count = int(data.get("total_count") or 0)
            if not artifacts or len(artifacts) < per_page:
                return None
            if total_count and page * per_page >= total_count:
                return None
            page += 1

    def _wait_for_artifact(self, run_id: int, artifact_name: str, deadline: float):
        while time.monotonic() < deadline:
            artifact = self._find_artifact(run_id, artifact_name)
            if artifact:
                return artifact
            time.sleep(5)
        raise AudioGitHubError(
            "Workflow đã hoàn tất nhưng chưa tìm thấy artifact MP3. "
            "Mở trang Actions của repo để kiểm tra lần chạy."
        )

    def _download_and_extract(self, artifact: dict, job_id: str, audio_dir: Path) -> list[Path]:
        """Download the artifact ZIP and save its ordinary audiobook MP3."""
        artifact_id = artifact.get("id")
        if not artifact_id:
            raise AudioGitHubError("GitHub artifact không có ID hợp lệ.")
        url = self._url(f"actions/artifacts/{artifact_id}/zip")
        try:
            response = self.session.get(url, timeout=(30, 600))
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AudioGitHubError("Không tải được artifact audio từ GitHub.") from exc

        job_dir = audio_dir / f"audio_{job_id[:8]}"
        job_dir.mkdir(parents=True, exist_ok=True)
        audio_member = None
        legacy_member = None
        manifest_member = None
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                for name in archive.namelist():
                    filename = Path(name).name
                    if re.fullmatch(r"au[1-9][0-9]*\.mp3", filename):
                        audio_member = name
                    elif filename == "audiobook.mp3":
                        legacy_member = name
                    elif filename == "manifest.json":
                        manifest_member = name

                # Prefer the new auN.mp3 naming, but keep old artifacts downloadable.
                audio_member = audio_member or legacy_member
                if not audio_member:
                    raise AudioGitHubError(
                        "Artifact không chứa file auN.mp3. Hãy kiểm tra lần chạy GitHub Actions."
                    )
                local_audio_name = Path(audio_member).name
                audiobook_path = job_dir / local_audio_name
                audiobook_path.write_bytes(archive.read(audio_member))
                if manifest_member:
                    (job_dir / "manifest.json").write_bytes(archive.read(manifest_member))
        except zipfile.BadZipFile as exc:
            raise AudioGitHubError("Artifact GitHub tải về không phải ZIP hợp lệ.") from exc

        if not audiobook_path.is_file() or audiobook_path.stat().st_size == 0:
            raise AudioGitHubError("File MP3 tải về đang trống hoặc không hợp lệ.")
        numbered_audiobook = _move_to_next_numbered_audiobook(audiobook_path, audio_dir)
        return [numbered_audiobook]

    def download_latest_completed_audio(
        self,
        audio_dir: str | Path,
        progress: Callable[[str], None] | None = None,
    ) -> list[Path]:
        """Download the newest successful audiobook without running TTS again."""
        data = self._request(
            "GET",
            f"actions/workflows/{AUDIO_WORKFLOW}/runs",
            params={"event": "workflow_dispatch", "branch": "main", "per_page": 20},
        )
        for run in data.get("workflow_runs", []):
            if run.get("status") != "completed" or run.get("conclusion") != "success":
                continue

            title = str(run.get("display_title") or run.get("name") or "")
            prefix = "Audio job "
            if not title.startswith(prefix):
                continue
            raw_job_id = title[len(prefix):].strip()
            try:
                job_id = uuid.UUID(raw_job_id).hex
            except (ValueError, AttributeError):
                continue

            run_id = run.get("id")
            if not run_id:
                continue
            artifact = self._find_artifact(int(run_id), f"audio-{job_id}")
            if not artifact:
                continue

            if progress:
                progress("Đã tìm thấy audiobook đã tạo. Đang tải file MP3...")
            return self._download_and_extract(artifact, job_id, Path(audio_dir))

        raise AudioGitHubError(
            "Không tìm thấy audiobook đã tạo còn hạn tải trên GitHub. "
            "Artifact audio được lưu tối đa 1 ngày; hãy kiểm tra tab Actions của repo."
        )

    def generate_audio(
        self,
        text: str,
        voice_name: str,
        rate: float,
        audio_dir: str | Path,
        progress: Callable[[str], None] | None = None,
        poll_interval: int = 10,
        timeout_seconds: int = 6 * 60 * 60,
    ) -> list[Path]:
        if not text or not text.strip():
            raise AudioGitHubError("Nội dung truyện đang trống.")
        voice = VOICE_IDS.get(voice_name)
        if voice is None:
            raise AudioGitHubError("Giọng đọc không được hỗ trợ.")
        if not 0.5 <= float(rate) <= 2.0:
            raise AudioGitHubError("Tốc độ đọc phải nằm trong khoảng 0.5x đến 2.0x.")

        job_id = uuid.uuid4().hex
        branch = f"audio-job-{job_id}"
        payload = {
            "job_id": job_id,
            "text": text,
            "voice": voice,
            "rate": float(rate),
        }
        payload_bytes = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        payload_b64 = base64.b64encode(payload_bytes).decode("ascii")
        audio_dir = Path(audio_dir)
        audio_dir.mkdir(parents=True, exist_ok=True)

        if progress:
            progress("Đang chuẩn bị nội dung và nhánh tác vụ tạm...")
        ref = self._request("GET", "git/ref/heads/main")
        main_sha = ref["object"]["sha"]
        self._request(
            "POST",
            "git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": main_sha},
        )
        dispatch_sent = False
        try:
            payload_path = f"contents/audio_jobs/{job_id}/payload.json"
            self._request(
                "PUT",
                payload_path,
                json={
                    "message": "Upload plain audio job payload",
                    "content": payload_b64,
                    "branch": branch,
                },
            )
            started_at = datetime.now(timezone.utc)
            self._request(
                "POST",
                f"actions/workflows/{AUDIO_WORKFLOW}/dispatches",
                json={
                    "ref": "main",
                    "inputs": {"job_id": job_id, "payload_branch": branch},
                },
            )
            dispatch_sent = True
        except Exception:
            if not dispatch_sent:
                self._delete_branch(branch)
            raise

        if progress:
            progress("Đã gửi tác vụ. Đang chờ GitHub Actions khởi chạy...")
        deadline = time.monotonic() + timeout_seconds
        run = None
        no_run_deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            run = self._find_run(job_id, main_sha, started_at)
            if run:
                status = run.get("status", "unknown")
                conclusion = run.get("conclusion")
                if progress:
                    progress(f"GitHub Actions: {status}" + (f" · {conclusion}" if conclusion else ""))
                if status == "completed":
                    if conclusion != "success":
                        run_url = run.get("html_url", "")
                        raise AudioGitHubError(
                            f"Tác vụ audio thất bại ({conclusion or 'unknown'}). "
                            f"Kiểm tra log tại: {run_url}"
                        )
                    break
            elif time.monotonic() > no_run_deadline:
                self._delete_branch(branch)
                raise AudioGitHubError(
                    "Đã gửi lệnh nhưng không tìm thấy phiên chạy trên GitHub Actions. "
                    "Nhánh tải lên tạm đã được dọn; kiểm tra quyền Actions và trạng thái workflow."
                )
            time.sleep(max(3, poll_interval))
        else:
            raise AudioGitHubError(
                "Đã hết thời gian chờ 6 giờ. Tác vụ có thể vẫn đang chạy trên GitHub Actions."
            )

        if not run or run.get("status") != "completed" or run.get("conclusion") != "success":
            raise AudioGitHubError("Không xác nhận được trạng thái hoàn tất của tác vụ audio.")

        if progress:
            progress("Tác vụ hoàn tất. Đang tải MP3 về máy...")
        artifact = self._wait_for_artifact(
            int(run["id"]),
            f"audio-{job_id}",
            time.monotonic() + 90,
        )
        outputs = self._download_and_extract(artifact, job_id, audio_dir)
        if progress:
            progress("Đã nhận audiobook MP3 hoàn chỉnh.")
        return outputs
