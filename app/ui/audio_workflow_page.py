from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.config import PROJECTS_DIR, project_dir_for
from app.services.audio_github_client import (
    AudioGitHubClient,
    AudioGitHubError,
    load_audio_credentials,
)
from app.ui.pages import AudioConnectionDialog, BasePage
from app.ui.widgets import (
    BG, COPPER, INPUT, LINE, MUTED, PANEL, RED, TEXT,
    button, eyebrow, field_label, heading, panel, text_box, try_enable_drop,
)
from app.utils import parse_drop_files, read_text_file


class AudioPage(BasePage):
    """Two-pane audiobook workspace with persistent history and elapsed-job timer."""

    def __init__(self, parent, app):
        super().__init__(parent, app)
        eyebrow(self, "03 / AUDIO").pack(anchor="w", pady=(0, 6))
        heading(self, "Tạo Audio", "Tạo một audiobook MP3 hoàn chỉnh từ bản dịch đã lưu.")

        file_bar = tk.Frame(self, bg=BG)
        file_bar.pack(fill="x", pady=(0, 9))
        self.open_button = button(file_bar, "MỞ FILE TXT ĐÃ DỊCH", self.load_file, accent=True)
        self.open_button.pack(side="left", padx=(0, 10))
        self.file_label = tk.StringVar(value="Chưa chọn nội dung")
        tk.Label(file_bar, textvariable=self.file_label, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="left")

        columns = tk.Frame(self, bg=BG)
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=6, uniform="audio")
        columns.grid_columnconfigure(1, weight=4, uniform="audio")
        columns.grid_rowconfigure(0, weight=1)

        left = panel(columns)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(left, text="NỘI DUNG TẠO", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 7))
        self.content_frame, self.content = text_box(left, 18)
        self.content_frame.pack(fill="both", expand=True)
        try_enable_drop(self.content, self.drop_audio)

        controls = tk.Frame(left, bg="#1D1412", padx=10, pady=9,
                            highlightthickness=1, highlightbackground=LINE)
        controls.pack(fill="x", pady=(9, 0))
        field_label(controls, "Giọng đọc", bg="#1D1412").pack(side="left")
        self.voice = tk.StringVar(value="Nam Minh")
        self.voice_combo = ttk.Combobox(
            controls, textvariable=self.voice,
            values=["Hoài My", "Nam Minh"], state="readonly", width=13,
        )
        self.voice_combo.pack(side="left", padx=(7, 14))
        field_label(controls, "Tốc độ", bg="#1D1412").pack(side="left")
        self.rate = tk.StringVar(value="1.25")
        self.rate_combo = ttk.Combobox(
            controls, textvariable=self.rate,
            values=["1", "1.25", "1.5", "1.75", "2"],
            state="readonly", width=7,
        )
        self.rate_combo.pack(side="left", padx=7)

        self.start_button = button(left, "BẮT ĐẦU TẠO AUDIO", self.start_audio, accent=True)
        self.start_button.pack(anchor="e", pady=(9, 0))

        right = panel(columns)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(right, text="LỊCH SỬ TẠO", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 7))
        list_frame = tk.Frame(right, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
        list_frame.pack(fill="both", expand=True)
        self.history = tk.Listbox(
            list_frame, bg=INPUT, fg=TEXT, selectbackground="#5B1A25",
            relief="flat", bd=0, font=("Segoe UI", 9), activestyle="none",
            selectmode="browse",
        )
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.history.yview)
        self.history.configure(yscrollcommand=scroll.set)
        self.history.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scroll.pack(side="right", fill="y", pady=5)
        self.history.bind("<<ListboxSelect>>", self.on_history_select)

        timer_panel = tk.Frame(right, bg="#1D1412", padx=12, pady=10,
                               highlightthickness=1, highlightbackground=LINE)
        timer_panel.pack(fill="x", pady=(9, 8))
        tk.Label(timer_panel, text="THỜI GIAN TẠO", bg="#1D1412", fg=COPPER,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.timer_value = tk.StringVar(value="00:00:00")
        tk.Label(timer_panel, textvariable=self.timer_value, bg="#1D1412", fg=TEXT,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(3, 0))
        self.job_status = tk.StringVar(value="Chưa có tác vụ")
        tk.Label(right, textvariable=self.job_status, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8), wraplength=300, justify="left").pack(anchor="w", pady=(0, 8))

        result_buttons = tk.Frame(right, bg=PANEL)
        result_buttons.pack(fill="x")
        self.listen_button = button(result_buttons, "NGHE AUDIO", self.listen_selected, accent=True)
        self.listen_button.pack(side="left", padx=(0, 7))
        self.open_file_button = button(result_buttons, "MỞ FILE", self.open_selected_file)
        self.open_file_button.pack(side="left")
        self.listen_button.configure(state="disabled")
        self.open_file_button.configure(state="disabled")

        self.source: Path | None = None
        self.audio_dir: Path | None = None
        self.history_path: Path | None = None
        self.history_records: list[dict] = []
        self.busy = False
        self._started_monotonic: float | None = None
        self._timer_after_id = None
        self._active_record_id: str | None = None
        self._selected_record: dict | None = None

    def load_file(self):
        selected = filedialog.askopenfilename(
            filetypes=[("Bản dịch TXT", "*.txt"), ("Tất cả tệp", "*.*")]
        )
        if selected:
            self.load_path(Path(selected))

    def drop_audio(self, data):
        paths = parse_drop_files(data)
        if paths:
            path = Path(paths[0].strip("{}"))
            if path.suffix.lower() == ".txt":
                self.load_path(path)

    def load_path(self, path: Path):
        path = Path(path)
        try:
            content = read_text_file(path)
        except Exception as exc:
            messagebox.showerror("Không đọc được TXT", str(exc))
            return
        if not content.strip():
            messagebox.showwarning("File trống", "TXT không có nội dung.")
            return
        self.source = path
        self.content.delete("1.0", "end")
        self.content.insert("1.0", content)
        self.audio_dir = project_dir_for(path) / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.audio_dir / "audio_history.json"
        self.file_label.set(path.name)
        self.job_status.set("Đã nạp nội dung · sẵn sàng tạo audio")
        self._refresh_history()
        self.app.set_status(f"Đã nạp bản dịch {path.name}.")

    def _load_history_records(self) -> list[dict]:
        if not self.history_path or not self.history_path.is_file():
            return []
        try:
            payload = json.loads(self.history_path.read_text(encoding="utf-8"))
            records = payload.get("items", [])
            return records if isinstance(records, list) else []
        except (OSError, ValueError, TypeError):
            return []

    def _save_history_records(self):
        if not self.history_path:
            return
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.history_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"version": 1, "items": self.history_records},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.history_path)

    def _refresh_history(self):
        self.history.delete(0, "end")
        self.history_records = self._load_history_records()
        known_paths = {
            str(Path(item.get("file_path", "")).resolve())
            for item in self.history_records if item.get("file_path")
        }
        if self.audio_dir and self.audio_dir.exists():
            for path in self.audio_dir.rglob("audiobook.mp3"):
                key = str(path.resolve())
                if key not in known_paths:
                    self.history_records.append({
                        "id": uuid.uuid4().hex,
                        "file_path": str(path),
                        "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                        "voice": "Không rõ",
                        "rate": None,
                        "elapsed_seconds": None,
                        "status": "completed",
                    })
                    known_paths.add(key)
            self.history_records.sort(
                key=lambda item: str(item.get("created_at", "")), reverse=True
            )
            self._save_history_records()

        for item in self.history_records:
            created = str(item.get("created_at", ""))[:16].replace("T", " ")
            voice = item.get("voice") or "Không rõ"
            rate = item.get("rate")
            rate_label = f"{rate}x" if rate is not None else ""
            status = item.get("status", "completed")
            if status == "completed":
                name = Path(item.get("file_path", "audiobook.mp3")).name
                label = f"✓ {created} · {voice} {rate_label} · {name}"
            elif status == "running":
                label = f"◌ {created} · {voice} {rate_label} · Đang tạo"
            else:
                label = f"× {created} · {voice} {rate_label} · Thất bại"
            self.history.insert("end", label)

        self._selected_record = None
        if self.history_records:
            self.history.selection_set(0)
            self.history.activate(0)
            self._selected_record = self.history_records[0]
        self._update_history_buttons()

    def on_history_select(self, _event=None):
        selection = self.history.curselection()
        self._selected_record = (
            self.history_records[selection[0]]
            if selection and selection[0] < len(self.history_records)
            else None
        )
        self._update_history_buttons()

    def _update_history_buttons(self):
        record = self._selected_record or {}
        path = Path(record.get("file_path", "")) if record.get("file_path") else None
        ready = bool(
            record.get("status") == "completed"
            and path and path.is_file()
        )
        state = "normal" if ready else "disabled"
        self.listen_button.configure(state=state)
        self.open_file_button.configure(state=state)

    def listen_selected(self):
        record = self._selected_record or {}
        path = Path(record.get("file_path", "")) if record.get("file_path") else None
        if not path or not path.is_file():
            messagebox.showinfo("Chưa có audiobook", "Hãy chọn một tác vụ đã hoàn thành.")
            return
        try:
            if os.name == "nt":
                os.startfile(str(path))
            else:
                import webbrowser
                webbrowser.open(path.as_uri())
        except Exception as exc:
            messagebox.showerror("Không mở được audio", str(exc))

    def open_selected_file(self):
        record = self._selected_record or {}
        path = Path(record.get("file_path", "")) if record.get("file_path") else None
        if not path or not path.is_file():
            messagebox.showinfo("Chưa có file", "Hãy chọn một audiobook đã hoàn thành.")
            return
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", f"/select,{path}"])
            else:
                import webbrowser
                webbrowser.open(path.parent.as_uri())
        except Exception as exc:
            messagebox.showerror("Không mở được vị trí file", str(exc))

    def _format_elapsed(self, seconds: float) -> str:
        total = max(0, int(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _start_timer(self):
        self._started_monotonic = time.monotonic()
        self.timer_value.set("00:00:00")
        self._tick_timer()

    def _tick_timer(self):
        if self._started_monotonic is None:
            return
        elapsed = time.monotonic() - self._started_monotonic
        self.timer_value.set(self._format_elapsed(elapsed))
        self._timer_after_id = self.after(1000, self._tick_timer)

    def _stop_timer(self) -> float:
        elapsed = 0.0
        if self._started_monotonic is not None:
            elapsed = time.monotonic() - self._started_monotonic
        self._started_monotonic = None
        if self._timer_after_id is not None:
            try:
                self.after_cancel(self._timer_after_id)
            except tk.TclError:
                pass
            self._timer_after_id = None
        self.timer_value.set(self._format_elapsed(elapsed))
        return elapsed

    def _update_record(self, **values):
        if not self._active_record_id:
            return
        for record in self.history_records:
            if record.get("id") == self._active_record_id:
                record.update(values)
                break
        self._save_history_records()
        self._refresh_history()

    def start_audio(self):
        if self.busy:
            return
        if self.source is None and not self.content.get("1.0", "end-1c").strip():
            messagebox.showinfo("Chưa có nội dung", "Hãy mở file TXT đã dịch hoặc dán nội dung trước.")
            return
        source_text = self.content.get("1.0", "end-1c").strip()
        if not source_text:
            messagebox.showinfo("Nội dung trống", "Không có văn bản để tạo audio.")
            return
        try:
            token, shared_key = load_audio_credentials()
        except AudioGitHubError as exc:
            messagebox.showerror("Lỗi Credential Manager", str(exc))
            return
        if not token or not shared_key:
            messagebox.showinfo(
                "Cần cấu hình GitHub Audio",
                "Ứng dụng cần GitHub PAT và khóa AES để gửi tác vụ đã mã hóa. "
                "Hãy cấu hình một lần, sau đó bấm BẮT ĐẦU TẠO AUDIO lần nữa.",
            )
            AudioConnectionDialog(self, self._credentials_updated)
            return

        if self.audio_dir is None:
            self.audio_dir = PROJECTS_DIR / "Audio-moi" / "audio"
            self.audio_dir.mkdir(parents=True, exist_ok=True)
            self.history_path = self.audio_dir / "audio_history.json"
            self._refresh_history()

        voice = self.voice.get().strip()
        rate = float(self.rate.get())
        record_id = uuid.uuid4().hex
        created_at = datetime.now().isoformat(timespec="seconds")
        record = {
            "id": record_id,
            "file_path": "",
            "created_at": created_at,
            "voice": voice,
            "rate": rate,
            "elapsed_seconds": None,
            "status": "running",
            "error": "",
            "source_file": str(self.source) if self.source else "",
        }
        self.history_records.insert(0, record)
        self._active_record_id = record_id
        self._save_history_records()
        self._refresh_history()
        self.busy = True
        self.start_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.voice_combo.configure(state="disabled")
        self.rate_combo.configure(state="disabled")
        self.job_status.set("Đang gửi và tạo audiobook trên GitHub Actions...")
        self.app.set_status("Đang tạo audiobook. Đồng hồ đã bắt đầu.")
        self._start_timer()

        audio_dir = self.audio_dir

        def report(status: str):
            try:
                self.after(0, lambda value=status: self.job_status.set(value))
            except tk.TclError:
                pass

        def work():
            try:
                client = AudioGitHubClient(token, shared_key)
                outputs = client.generate_audio(
                    source_text, voice, rate, audio_dir, progress=report
                )
                output_path = outputs[0] if outputs else None
                self.after(0, lambda path=output_path: self._audio_done(path))
            except Exception as exc:
                self.after(0, lambda error=str(exc): self._audio_failed(error))

        threading.Thread(target=work, daemon=True).start()

    def _credentials_updated(self):
        self.job_status.set("Đã lưu cấu hình GitHub Audio. Bấm BẮT ĐẦU TẠO AUDIO để chạy.")

    def _finish_job_controls(self):
        self.busy = False
        self.start_button.configure(state="normal")
        self.open_button.configure(state="normal")
        self.voice_combo.configure(state="readonly")
        self.rate_combo.configure(state="readonly")

    def _audio_done(self, output_path: Path | None):
        elapsed = self._stop_timer()
        self._finish_job_controls()
        if output_path is None or not Path(output_path).is_file():
            self._audio_failed("Worker không trả về audiobook.mp3 hợp lệ.")
            return
        self._update_record(
            file_path=str(output_path),
            elapsed_seconds=round(elapsed, 2),
            status="completed",
            error="",
        )
        self.job_status.set(f"Hoàn tất · {Path(output_path).name}")
        self.app.set_status("Đã tạo xong audiobook.mp3.")
        self._active_record_id = None
        self._refresh_history()
        messagebox.showinfo(
            "Tạo audio hoàn tất",
            f"Đã tạo audiobook.mp3.\n\nLưu tại:\n{output_path}\n\n"
            f"Thời gian: {self._format_elapsed(elapsed)}",
        )

    def _audio_failed(self, error: str):
        elapsed = self._stop_timer()
        self._finish_job_controls()
        self._update_record(
            elapsed_seconds=round(elapsed, 2),
            status="failed",
            error=error,
        )
        self.job_status.set("Tạo audio thất bại · " + error)
        self.app.set_status("Tác vụ audio thất bại.")
        self._active_record_id = None
        self._refresh_history()
        messagebox.showerror("Không tạo được audio", error)
