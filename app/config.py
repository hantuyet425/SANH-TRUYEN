from pathlib import Path
import os

APP_NAME = "SẢNH TRUYỆN"
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DOWNLOAD_DIR = DATA_DIR / "downloads"
CHROME_PROFILE_DIR = DATA_DIR / "chrome_profile"
PROJECTS_DIR = DATA_DIR / "projects"
MODELS_DIR = DATA_DIR / "models"
TEMP_DIR = DATA_DIR / "temp"
LOG_DIR = DATA_DIR / "logs"

for directory in (DATA_DIR, DOWNLOAD_DIR, CHROME_PROFILE_DIR, PROJECTS_DIR, MODELS_DIR, TEMP_DIR, LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)

WEBTOEPUB_URL = "https://chromewebstore.google.com/detail/webtoepub/akiljllkbielkidmammnifcnibaigelm"
HACHIMI_MODELS = {
    "HachimiMT-60 (tự nhiên)": "ngocdang83/HachimiMT-60-zh-vi",
    "HachimiMT-60-QT (convert)": "ngocdang83/HachimiMT-60-QT",
}
TTS_VOICES = {
    "NamMinh (nam)": "vi-VN-NamMinhNeural",
    "HoaiMy (nữ)": "vi-VN-HoaiMyNeural",
}
TTS_RATES = {"0.75x": "-25%", "1.0x": "+0%", "1.25x": "+25%", "1.5x": "+50%", "2.0x": "+100%"}


def project_dir_for(source: Path) -> Path:
    source = Path(source).resolve()
    # Files already stored in a project's raw/translated/audio folder belong
    # to that same project (important when converting a translated TXT to audio).
    if source.parent.name.lower() in {"raw", "translated", "audio"} and source.parent.parent.parent.resolve() == PROJECTS_DIR.resolve():
        target = source.parent.parent
    else:
        safe_name = "".join(ch for ch in source.stem if ch.isalnum() or ch in " ._-()[]")
        safe_name = safe_name.strip(" .")[:80] or "Truyen-moi"
        target = PROJECTS_DIR / safe_name
    (target / "raw").mkdir(parents=True, exist_ok=True)
    (target / "translated").mkdir(parents=True, exist_ok=True)
    (target / "audio").mkdir(parents=True, exist_ok=True)
    return target
