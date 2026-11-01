from __future__ import annotations

import base64
import io
import json
import secrets
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AUDIO_REPOSITORY = "hantuyet425/SANH-TRUYEN-AUDIO"
AUDIO_WORKFLOW = "generate-audio.yml"
API_ROOT = "https://api.github.com"
KEYRING_SERVICE = "SANH-TRUYEN-AUDIO"
KEYRING_TOKEN_NAME = "github_pat"
KEYRING_KEY_NAME = "audio_shared_key"
MAGIC = b"SANHAUDIO1"
VOICE_IDS = {
    "Nam Minh": "vi-VN-NamMinhNeural",
    "Hoài My": "vi-VN-HoaiMyNeural",
}


class AudioGitHubError(RuntimeError):
    """A safe, user-readable GitHub Audio connection or job error."""


def generate_shared_key() -> str:
    """Create a new AES-256 key encoded as Base64 for the GitHub secret."""
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


def _validate_shared_key(shared_key_b64: str) -> bytes:
    try:
        key = base64.b64decode(shared_key_b64.strip(), validate=True)
    except Exception as exc:
        raise AudioGitHubError("Khóa AUDIO_SHARED_KEY không phải Base64 hợp lệ.") from exc
    if len(key) != 32:
        raise AudioGitHubError("Khóa AUDIO_SHARED_KEY phải giải mã thành đúng 32 byte.")
    return key


def save_audio_credentials(token: str, shared_key_b64: str) -> None:
    """Store credentials in the operating system credential vault via keyring."""
    token = token.strip()
    if not token:
        raise AudioGitHubError("Chưa nhập GitHub Personal Access Token.")
    _validate_shared_key(shared_key_b64)
    try:
        import keyring
        backend = keyring.get_keyring()
        if getattr(backend, "priority", 0) <= 0:
            raise RuntimeError("No secure credential backend is available.")
        keyring.set_password(KEYRING_SERVICE, KEYRING_TOKEN_NAME, token)
        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY_NAME, shared_key_b64.strip())
        if keyring.get_password(KEYRING_SERVICE, KEYRING_TOKEN_NAME) != token:
            raise RuntimeError("Credential verification failed.")
        if keyring.get_password(KEYRING_SERVICE, KEYRING_KEY_NAME) != shared_key_b64.strip():
            raise RuntimeError("Key verification failed.")
    except Exception as exc:
        raise AudioGitHubError(
            "Không lưu được thông tin vào Windows Credential Manager. "
            "Hãy kiểm tra keyring/Windows Credential Manager rồi thử lại."
        ) from exc


def load_audio_credentials() -> tuple[str | None, str | None]:
    try:
        import keyring
        token = keyring.get_password(KEYRING_SERVICE, KEYRING_TOKEN_NAME)
        shared_key = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY_NAME)
        return token, shared_key
    except Exception as exc:
        raise AudioGitHubError(
            "Không đọc được thông tin từ Windows Credential Manager."
        ) from exc


def _encrypt_payload(payload: dict, key: bytes) -> bytes:
    nonce = secrets.token_bytes(12)
    plaintext = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, MAGIC)
    envelope = {
        "version": 1,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope, separators=(",", ":")).encode("utf-8")


def _decrypt_result(encrypted_data: bytes, key: bytes) -> bytes:
    try:
        envelope = json.loads(encrypted_data.decode("utf-8"))
        if envelope.get("version") != 1:
            raise ValueError("unsupported envelope version")
        nonce = base64.b64decode(envelope["nonce"], validate=True)
        ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
        return AESGCM(key).decrypt(nonce, ciphertext, MAGIC)
    except Exception as exc:
        raise AudioGitHubError(
            "Không giải mã được kết quả audio. Hãy kiểm tra khóa AUDIO_SHARED_KEY "
            "trong ứng dụng có trùng với GitHub Actions secret hay không."
        ) from exc


class AudioGitHubClient:
    def __init__(self, token: str, shared_key_b64: str, repository: str = AUDIO_REPOSITORY):
        self.repository = repository
        self.token = token.strip()
        if not self.token:
            raise AudioGitHubError("Chưa cấu hình GitHub token.")
        self.key = _validate_shared_key(shared_key_b64)
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

    def _wait_for_artifact(self, run_id: int, artifact_name: str, deadline: float):
        while time.monotonic() < deadline:
            data = self._request("GET", f"actions/runs/{run_id}/artifacts")
            for artifact in data.get("artifacts", []):
                if artifact.get("name") == artifact_name and not artifact.get("expired"):
                    return artifact
            time.sleep(5)
        raise AudioGitHubError(
            "Workflow đã hoàn tất nhưng chưa tìm thấy artifact MP3. "
            "Mở trang Actions của repo để kiểm tra lần chạy."
        )

    def _download_and_extract(self, artifact: dict, job_id: str, audio_dir: Path) -> list[Path]:
        artifact_id = artifact.get("id")
        if not artifact_id:
            raise AudioGitHubError("GitHub artifact không có ID hợp lệ.")
        url = self._url(f"actions/artifacts/{artifact_id}/zip")
        try:
            response = self.session.get(url, timeout=(30, 600))
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AudioGitHubError("Không tải được artifact audio từ GitHub.") from exc

        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as outer:
                encrypted_member = next(
                    (name for name in outer.namelist() if Path(name).name == "audio-result.enc"),
                    None,
                )
                if not encrypted_member:
                    raise AudioGitHubError("Artifact không chứa audio-result.enc.")
                encrypted_audio = outer.read(encrypted_member)
        except zipfile.BadZipFile as exc:
            raise AudioGitHubError("Artifact GitHub tải về không phải ZIP hợp lệ.") from exc

        clear_zip = _decrypt_result(encrypted_audio, self.key)
        job_dir = audio_dir / f"audio_{job_id[:8]}"
        job_dir.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        try:
            with zipfile.ZipFile(io.BytesIO(clear_zip)) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename
                    # The worker currently writes only flat MP3 files and manifest.json.
                    if Path(name).name != name:
                        continue
                    suffix = Path(name).suffix.lower()
                    if suffix != ".mp3" and name != "manifest.json":
                        continue
                    target = job_dir / name
                    target.write_bytes(archive.read(info))
                    if suffix == ".mp3":
                        outputs.append(target)
        except zipfile.BadZipFile as exc:
            raise AudioGitHubError("Gói audio sau giải mã không phải ZIP hợp lệ.") from exc

        audiobook = job_dir / "audiobook.mp3"
        if not audiobook.is_file() or audiobook not in outputs:
            raise AudioGitHubError(
                "Gói kết quả không có audiobook.mp3 hoàn chỉnh. "
                "Hãy cập nhật worker SANH-TRUYEN-AUDIO lên phiên bản mới nhất."
            )
        # The current protocol returns one complete MP3 for the whole novel.
        return [audiobook]

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
        encrypted_payload = _encrypt_payload(payload, self.key)
        audio_dir = Path(audio_dir)
        audio_dir.mkdir(parents=True, exist_ok=True)

        if progress:
            progress("Đang chuẩn bị bản mã hóa và nhánh tác vụ tạm...")
        ref = self._request("GET", "git/ref/heads/main")
        main_sha = ref["object"]["sha"]
        self._request(
            "POST",
            "git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": main_sha},
        )
        dispatch_sent = False
        try:
            payload_path = f"contents/audio_jobs/{job_id}/payload.json.enc"
            self._request(
                "PUT",
                payload_path,
                json={
                    "message": "Upload encrypted audio job",
                    "content": base64.b64encode(encrypted_payload).decode("ascii"),
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
            progress("Tác vụ hoàn tất. Đang tải và giải mã MP3 về máy...")
        artifact = self._wait_for_artifact(
            int(run["id"]),
            f"audio-{job_id}",
            time.monotonic() + 90,
        )
        outputs = self._download_and_extract(artifact, job_id, audio_dir)
        if progress:
            progress("Đã nhận audiobook.mp3 hoàn chỉnh.")
        return outputs
