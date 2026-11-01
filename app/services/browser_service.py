from pathlib import Path
import os
import shutil
import subprocess
import sys
import webbrowser

from app.config import CHROME_PROFILE_DIR, DOWNLOAD_DIR, WEBTOEPUB_URL


def find_chrome() -> str | None:
    candidates: list[Path] = []
    if sys.platform == "win32":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                candidates.extend([
                    Path(base) / "Google/Chrome/Application/chrome.exe",
                    Path(base) / "Google/Chrome Beta/Application/chrome.exe",
                ])
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ])
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            found = shutil.which(name)
            if found:
                return found
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("chrome") or shutil.which("google-chrome")


def _prepare_profile() -> None:
    default_dir = CHROME_PROFILE_DIR / "Default"
    default_dir.mkdir(parents=True, exist_ok=True)
    prefs_path = default_dir / "Preferences"
    if not prefs_path.exists():
        import json
        prefs = {
            "download": {
                "default_directory": str(DOWNLOAD_DIR.resolve()),
                "prompt_for_download": False,
                "directory_upgrade": True,
            },
            "profile": {"exit_type": "Normal", "exited_cleanly": True},
        }
        prefs_path.write_text(json.dumps(prefs, ensure_ascii=False), encoding="utf-8")


def open_chrome(url: str = "https://www.google.com") -> tuple[bool, str]:
    chrome = find_chrome()
    if not chrome:
        return False, "Không tìm thấy Google Chrome. Hãy cài Chrome chính thức rồi thử lại."
    _prepare_profile()
    args = [
        chrome,
        f"--user-data-dir={CHROME_PROFILE_DIR.resolve()}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        url,
    ]
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "Đã mở Google Chrome bằng hồ sơ riêng của SẢNH TRUYỆN."
    except Exception as exc:
        return False, f"Không mở được Chrome: {exc}"


def open_webtoepub_page() -> None:
    webbrowser.open(WEBTOEPUB_URL)
