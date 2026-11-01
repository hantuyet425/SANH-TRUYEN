from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.config import HACHIMI_MODELS, PROJECTS_DIR, project_dir_for
from app.services.audio_github_client import (
    AudioGitHubClient,
    AudioGitHubError,
    load_audio_credentials,
)
from app.services.chapter_numbering import renumber_chapters
from app.services.hachimi_service import HachimiTranslator
from app.ui.pages import AudioConnectionDialog, BasePage
from app.ui.widgets import (
    BG, COPPER, INPUT, LINE, MUTED, PANEL, PANEL_2, RED, TEXT,
    button, eyebrow, field_label, heading, panel, text_box, try_enable_drop,
)
from app.utils import parse_drop_files, read_text_file


_CHAPTER_LINE_RE = re.compile(
    r"^\s*(?:第[0-9０-９零〇○一二两兩三四五六七八九十百千万萬亿億]+\s*[章节回节節集话話].*"
    r"|(?:Chương|Chapter|Chap\.?|Hồi)\s+[0-9０-９０-９]+.*)$",
    re.IGNORECASE,
)


def split_story_chapters(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Normalize chapter numbers, then split RAW without treating volume headings as chapters."""
    normalized, _report = renumber_chapters(text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return normalized, []

    lines = normalized.splitlines(keepends=True)
    starts: list[tuple[int, str]] = []
    offset = 0
    for line in lines:
        title = line.rstrip("\r\n").strip()
        if _CHAPTER_LINE_RE.match(title):
            starts.append((offset, title))
        offset += len(line)

    if not starts:
        return normalized, [("Toàn bộ RAW (không nhận diện tiêu đề chương)", normalized)]

    # Keep any preface before the first chapter attached to the first segment.
    segments: list[tuple[str, str]] = []
    for index, (start, title) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(normalized)
        content = normalized[start:end].strip()
        if index == 0 and start > 0:
            content = normalized[:end].strip()
        if content:
            segments.append((title, content))
    return normalized, segments


class _BatchSettingsDialog(tk.Toplevel):
    def __init__(self, parent, batch_default: int = 20, turn_default: int = 5):
        super().__init__(parent.winfo_toplevel())
        self.title("Thiết lập chia lô dịch")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.result = None
        self.geometry("430x285")

        tk.Label(self, text="THIẾT LẬP PHIÊN DỊCH", bg=BG, fg=COPPER,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(20, 6))
        tk.Label(
            self,
            text="Chia RAW thành các lô theo số chương. Với ChatGPT, mỗi lô tiếp tục được chia thành các lượt nhỏ.",
            bg=BG, fg=MUTED, wraplength=380, justify="left",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=22, pady=(0, 14))

        body = tk.Frame(self, bg=PANEL, padx=16, pady=14,
                        highlightthickness=1, highlightbackground=LINE)
        body.pack(fill="x", padx=20)
        self.batch_var = tk.StringVar(value=str(batch_default))
        self.turn_var = tk.StringVar(value=str(turn_default))
        for label, variable, hint in (
            ("SỐ CHƯƠNG MỖI LÔ", self.batch_var, "Ví dụ: 20 chương/lô"),
            ("SỐ CHƯƠNG MỖI LƯỢT", self.turn_var, "Ví dụ: 5 chương/lượt"),
        ):
            row = tk.Frame(body, bg=PANEL)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, bg=PANEL, fg=COPPER,
                     font=("Segoe UI", 8, "bold"), width=23, anchor="w").pack(side="left")
            tk.Entry(row, textvariable=variable, width=8, bg=INPUT, fg=TEXT,
                     insertbackground=TEXT, relief="flat").pack(side="left", ipady=5)
            tk.Label(row, text=hint, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 8)).pack(side="left", padx=8)

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=20, pady=16)
        button(footer, "HỦY", self.destroy).pack(side="right", padx=(8, 0))
        button(footer, "TIẾP TỤC", self._accept, accent=True).pack(side="right")
        self.bind("<Return>", lambda _event: self._accept())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.grab_set()
        self.focus_force()

    def _accept(self):
        try:
            batch_size = int(self.batch_var.get().strip())
            turn_size = int(self.turn_var.get().strip())
        except ValueError:
            messagebox.showwarning("Thông số không hợp lệ", "Hãy nhập số nguyên cho cả hai thông số.", parent=self)
            return
        if not 1 <= batch_size <= 500 or not 1 <= turn_size <= 100:
            messagebox.showwarning(
                "Thông số ngoài giới hạn",
                "Số chương mỗi lô phải từ 1 đến 500; số chương mỗi lượt từ 1 đến 100.",
                parent=self,
            )
            return
        self.result = (batch_size, turn_size)
        self.destroy()


class _BatchSelectionDialog(tk.Toplevel):
    def __init__(self, parent, segments, batch_size, completed):
        super().__init__(parent.winfo_toplevel())
        self.title("Chọn lô cần dịch")
        self.configure(bg=BG)
        self.geometry("540x500")
        self.minsize(460, 380)
        self.transient(parent.winfo_toplevel())
        self.result = None

        count = max(1, math.ceil(len(segments) / batch_size))
        tk.Label(self, text="CHỌN LÔ TRUYỆN", bg=BG, fg=COPPER,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(18, 5))
        tk.Label(
            self, text=f"{len(segments)} phần/chương · {count} lô · chọn lô muốn xử lý",
            bg=BG, fg=MUTED, font=("Segoe UI", 9),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        frame = tk.Frame(self, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
        frame.pack(fill="both", expand=True, padx=20)
        self.listbox = tk.Listbox(
            frame, bg=INPUT, fg=TEXT, selectbackground="#5B1A25",
            relief="flat", bd=0, font=("Segoe UI", 10), activestyle="none",
        )
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        scroll.pack(side="right", fill="y", pady=8)
        for batch_index in range(count):
            start = batch_index * batch_size
            end = min(len(segments), start + batch_size)
            if len(segments) == 1 and "không nhận diện" in segments[0][0]:
                range_label = "Toàn bộ RAW"
            else:
                range_label = f"Chương/phần {start + 1}–{end}"
            state = "✓ Hoàn thành" if batch_index in completed else "○ Chưa hoàn thành"
            self.listbox.insert("end", f"Lô {batch_index + 1:02d}  ·  {range_label}  ·  {state}")
        if count:
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        self.listbox.bind("<Double-Button-1>", lambda _event: self._accept())

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=20, pady=16)
        button(footer, "HỦY", self.destroy).pack(side="right", padx=(8, 0))
        button(footer, "CHỌN LÔ NÀY", self._accept, accent=True).pack(side="right")
        self.bind("<Return>", lambda _event: self._accept())
        self.grab_set()
        self.focus_force()

    def _accept(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showinfo("Chưa chọn lô", "Hãy chọn một lô truyện.", parent=self)
            return
        self.result = int(selection[0])
        self.destroy()


class _ProfileDialog(tk.Toplevel):
    def __init__(self, parent, prompt: str, on_accept):
        super().__init__(parent.winfo_toplevel())
        self.title("Lập hồ sơ dịch xuyên suốt")
        self.configure(bg=BG)
        self.geometry("1040x650")
        self.minsize(800, 520)
        self.transient(parent.winfo_toplevel())
        self.on_accept = on_accept

        tk.Label(self, text="BƯỚC 1 / LẬP HỒ SƠ TRUYỆN", bg=BG, fg=COPPER,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(16, 5))
        tk.Label(
            self,
            text="Sao chép prompt bên trái, gửi ChatGPT. Dán hồ sơ ChatGPT trả về vào khung bên phải.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        panes = tk.Frame(self, bg=BG)
        panes.pack(fill="both", expand=True, padx=20)
        panes.grid_columnconfigure(0, weight=1)
        panes.grid_columnconfigure(1, weight=1)
        panes.grid_rowconfigure(0, weight=1)

        left = panel(panes)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(left, text="PROMPT TẠO HỒ SƠ", bg=PANEL, fg=COPPER,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 7))
        self.prompt_box = tk.Text(
            left, wrap="word", bg=INPUT, fg=TEXT, relief="flat",
            insertbackground=COPPER, font=("Segoe UI", 9), padx=9, pady=9,
        )
        self.prompt_box.pack(fill="both", expand=True)
        self.prompt_box.insert("1.0", prompt)
        self.prompt_box.configure(state="disabled")

        right = panel(panes)
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Label(right, text="HỒ SƠ CHATGPT TRẢ VỀ", bg=PANEL, fg=COPPER,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 7))
        self.profile_box = tk.Text(
            right, wrap="word", bg=INPUT, fg=TEXT, relief="flat",
            insertbackground=COPPER, font=("Segoe UI", 9), padx=9, pady=9,
        )
        self.profile_box.pack(fill="both", expand=True)
        self.profile_box.focus_set()

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=20, pady=15)
        button(footer, "HỦY PHIÊN DỊCH", self.destroy).pack(side="right", padx=(8, 0))
        button(footer, "ĐÃ DÁN – VÀO DỊCH", self._accept, accent=True).pack(side="right")
        button(footer, "SAO CHÉP PROMPT", self._copy).pack(side="left")
        self.grab_set()

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.prompt_box.get("1.0", "end-1c"))
        self.update()
        messagebox.showinfo("Đã sao chép", "Prompt tạo hồ sơ đã được sao chép.", parent=self)

    def _accept(self):
        profile = self.profile_box.get("1.0", "end-1c").strip()
        if not profile:
            messagebox.showwarning("Chưa có hồ sơ", "Hãy dán hồ sơ ChatGPT trả về trước.", parent=self)
            return
        self.destroy()
        self.on_accept(profile)


class _TurnPromptDialog(tk.Toplevel):
    """Non-modal by design: the user must be able to paste ChatGPT's answer into the main editor."""
    def __init__(self, parent, on_continue, on_cancel):
        super().__init__(parent.winfo_toplevel())
        self.title("Lượt dịch")
        self.configure(bg=BG)
        self.geometry("760x560")
        self.minsize(620, 430)
        self.transient(parent.winfo_toplevel())
        self.on_continue = on_continue
        self.on_cancel = on_cancel
        self.prompt = ""

        self.title_label = tk.Label(self, text="LƯỢT DỊCH", bg=BG, fg=COPPER,
                                    font=("Segoe UI", 12, "bold"))
        self.title_label.pack(anchor="w", padx=18, pady=(16, 8))
        tk.Label(
            self,
            text="Sao chép prompt sang ChatGPT. Dán phần trả lời vào khung BẢN DỊCH của cửa sổ chính, rồi bấm TIẾP TỤC.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=720, justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 10))
        frame = panel(self)
        frame.pack(fill="both", expand=True, padx=18)
        tk.Label(frame, text="PROMPT CHO LƯỢT NÀY", bg=PANEL, fg=COPPER,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 7))
        self.prompt_box = tk.Text(
            frame, wrap="word", bg=INPUT, fg=TEXT, relief="flat",
            font=("Segoe UI", 9), padx=9, pady=9,
        )
        self.prompt_box.pack(fill="both", expand=True)
        self.prompt_box.configure(state="disabled")

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=18, pady=14)
        button(footer, "HỦY PHIÊN", self._cancel).pack(side="right", padx=(8, 0))
        button(footer, "TIẾP TỤC", self.on_continue, accent=True).pack(side="right")
        button(footer, "SAO CHÉP PROMPT", self._copy).pack(side="left")
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def show_prompt(self, title: str, prompt: str):
        self.title_label.configure(text=title.upper())
        self.prompt = prompt
        self.prompt_box.configure(state="normal")
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", prompt)
        self.prompt_box.configure(state="disabled")
        self.lift()

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.prompt)
        self.update()

    def _cancel(self):
        self.on_cancel()
        self.destroy()


class TranslatePage(BasePage):
    """Chapter-based translation workflow with resumable, per-project session state."""

    def __init__(self, parent, app):
        super().__init__(parent, app)
        eyebrow(self, "02 / TRANSLATE").pack(anchor="w", pady=(0, 6))
        heading(self, "Dịch truyện", "Chia theo chương, lập hồ sơ nhất quán và xử lý lần lượt từng lượt.")

        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill="x", pady=(0, 9))
        button(toolbar, "MỞ RAW TXT", self.load_file, accent=True).pack(side="left", padx=(0, 7))
        button(toolbar, "TỪ ĐIỂN DỊCH", self.load_dictionary).pack(side="left", padx=(0, 10))
        field_label(toolbar, "Chế độ dịch", bg=BG).pack(side="left", padx=(0, 6))
        self.engine_choice = tk.StringVar(value="ChatGPT của tôi")
        self.engine_combo = ttk.Combobox(
            toolbar, textvariable=self.engine_choice,
            values=["ChatGPT của tôi", "Hachimi"],
            state="readonly", width=18,
        )
        self.engine_combo.pack(side="left")
        self.story_label = tk.StringVar(value="Chưa mở RAW")
        tk.Label(toolbar, textvariable=self.story_label, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="right", padx=(8, 0))
        self.dictionary_label = tk.StringVar(value="Chưa nạp từ điển")
        tk.Label(self, textvariable=self.dictionary_label, bg=BG, fg=COPPER,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 7))

        panes = tk.Frame(self, bg=BG)
        panes.pack(fill="both", expand=True)
        panes.grid_columnconfigure(0, weight=1, uniform="translation")
        panes.grid_columnconfigure(1, weight=1, uniform="translation")
        panes.grid_rowconfigure(0, weight=1)

        left = panel(panes)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(left, text="RAW / VĂN BẢN NGUỒN", bg=PANEL, fg=COPPER,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 7))
        self.raw_frame, self.raw_box = text_box(left, 18)
        self.raw_frame.pack(fill="both", expand=True)

        right = panel(panes)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(right, text="BẢN DỊCH TIẾNG VIỆT", bg=PANEL, fg=COPPER,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 7))
        self.vi_frame, self.vi_box = text_box(right, 18)
        self.vi_frame.pack(fill="both", expand=True)
        try_enable_drop(self.raw_box, self.drop_raw)

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", pady=(9, 0))
        self.status = tk.StringVar(value="Mở RAW TXT để bắt đầu.")
        tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8), anchor="w").pack(side="left", fill="x", expand=True)
        self.save_button = button(footer, "LƯU BẢN DỊCH", self.save_translation)
        self.save_button.pack(side="right", padx=(8, 0))
        self.save_button.configure(state="disabled")
        self.start_button = button(footer, "BẮT ĐẦU DỊCH", self.start_translation, accent=True)
        self.start_button.pack(side="right")

        self.source: Path | None = None
        self.normalized_raw = ""
        self.chapter_segments: list[tuple[str, str]] = []
        self.dictionary_text = ""
        self.dictionary_path: Path | None = None
        self.session: dict = {}
        self.session_path: Path | None = None
        self.active_batch: int | None = None
        self.turn_dialog: _TurnPromptDialog | None = None
        self.local_busy = False

    def _new_session(self, path: Path, raw: str, batch_size: int = 20, turn_size: int = 5) -> dict:
        return {
            "version": 1,
            "source_path": str(path.resolve()),
            "source_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "chapters_per_batch": batch_size,
            "chapters_per_turn": turn_size,
            "profiles": {},
            "batch_translations": {},
            "completed_batches": [],
            "active_batch": None,
            "turn_index": 0,
            "engine": "ChatGPT của tôi",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _persist_session(self):
        if not self.session_path or not self.session:
            return
        self.session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.session_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.session, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.session_path)

    def load_file(self):
        selected = filedialog.askopenfilename(filetypes=[("Văn bản RAW", "*.txt"), ("Tất cả tệp", "*.*")])
        if selected:
            self.load_path(Path(selected))

    def drop_raw(self, data):
        paths = parse_drop_files(data)
        if paths:
            path = Path(paths[0].strip("{}"))
            if path.suffix.lower() == ".txt":
                self.load_path(path)

    def load_path(self, path: Path):
        path = Path(path)
        try:
            raw = read_text_file(path)
            normalized, segments = split_story_chapters(raw)
        except Exception as exc:
            messagebox.showerror("Không mở được RAW", str(exc))
            return
        if not segments:
            messagebox.showwarning("RAW trống", "File không có nội dung để dịch.")
            return

        self.source = path
        self.normalized_raw = normalized
        self.chapter_segments = segments
        project_dir = project_dir_for(path)
        self.session_path = project_dir / "translation_session.json"
        fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        restored = False
        if self.session_path.is_file():
            try:
                previous = json.loads(self.session_path.read_text(encoding="utf-8"))
                same_source = (
                    previous.get("source_path") == str(path.resolve())
                    and previous.get("source_sha256") == fingerprint
                    and previous.get("version") == 1
                )
                if same_source:
                    restore = messagebox.askyesno(
                        "Khôi phục phiên dịch",
                        "Tìm thấy tiến độ dịch đã lưu cho RAW này.\n\n"
                        "Khôi phục lô đang làm, hồ sơ và các lượt đã hoàn thành?",
                    )
                    if restore:
                        self.session = previous
                        restored = True
            except (OSError, ValueError, TypeError):
                pass
        if not restored:
            self.session = self._new_session(path, raw)
            self._persist_session()

        self.raw_box.delete("1.0", "end")
        self.raw_box.insert("1.0", self.normalized_raw)
        self.vi_box.delete("1.0", "end")
        self.story_label.set(f"{path.name} · {len(segments)} chương/phần")
        self.status.set(
            f"Đã nạp {len(segments)} chương/phần. RAW gốc không bị chỉnh sửa."
        )
        self.active_batch = self.session.get("active_batch")
        self._update_save_state()
        if restored:
            self.status.set("Đã khôi phục tiến độ. Bấm BẮT ĐẦU DỊCH để tiếp tục lô đang làm.")

    def load_dictionary(self):
        selected = filedialog.askopenfilename(
            filetypes=[("Từ điển văn bản", "*.txt *.md"), ("Tất cả tệp", "*.*")]
        )
        if not selected:
            return
        path = Path(selected)
        try:
            content = read_text_file(path).strip()
        except Exception as exc:
            messagebox.showerror("Không đọc được từ điển", str(exc))
            return
        self.dictionary_path = path
        self.dictionary_text = content
        self.dictionary_label.set(f"Từ điển: {path.name}")
        self.status.set(f"Đã nạp từ điển {path.name}.")

    def _batch_count(self) -> int:
        size = max(1, int(self.session.get("chapters_per_batch", 20)))
        return math.ceil(len(self.chapter_segments) / size)

    def _batch_slice(self, batch_index: int) -> list[tuple[str, str]]:
        size = int(self.session.get("chapters_per_batch", 20))
        start = batch_index * size
        return self.chapter_segments[start:start + size]

    def _turns_for_batch(self, batch_index: int) -> list[list[tuple[str, str]]]:
        chapters = self._batch_slice(batch_index)
        size = max(1, int(self.session.get("chapters_per_turn", 5)))
        return [chapters[index:index + size] for index in range(0, len(chapters), size)]

    def _range_label(self, batch_index: int) -> str:
        batch = self._batch_slice(batch_index)
        if not batch:
            return ""
        if len(self.chapter_segments) == 1 and "không nhận diện" in batch[0][0]:
            return "Toàn bộ RAW"
        start = batch_index * int(self.session.get("chapters_per_batch", 20)) + 1
        end = start + len(batch) - 1
        return f"chương {start}–{end}"

    def start_translation(self):
        if not self.source or not self.chapter_segments:
            messagebox.showinfo("Chưa có RAW", "Hãy mở file RAW TXT trước.")
            return
        current_batch = int(self.session.get("chapters_per_batch", 20))
        current_turn = int(self.session.get("chapters_per_turn", 5))
        dialog = _BatchSettingsDialog(self, current_batch, current_turn)
        self.wait_window(dialog)
        if not dialog.result:
            return
        batch_size, turn_size = dialog.result
        changed = (
            batch_size != current_batch or turn_size != current_turn
        )
        if changed and (self.session.get("completed_batches") or self.session.get("profiles")):
            reset = messagebox.askyesno(
                "Thay đổi cách chia lô",
                "Đổi số chương mỗi lô/lượt sẽ làm tiến độ hiện tại không còn khớp.\n"
                "Xóa tiến độ dịch của RAW này và chia lại từ đầu?",
            )
            if not reset:
                return
            self.session = self._new_session(self.source, self.normalized_raw, batch_size, turn_size)
        else:
            self.session["chapters_per_batch"] = batch_size
            self.session["chapters_per_turn"] = turn_size
        self._persist_session()

        if len(self.chapter_segments) == 1 and "không nhận diện" in self.chapter_segments[0][0]:
            messagebox.showwarning(
                "Không nhận diện tiêu đề chương",
                "RAW không có tiêu đề chương theo định dạng nhận diện được. "
                "Ứng dụng sẽ coi toàn bộ file là một phần duy nhất; hãy kiểm tra kết quả chia lô.",
            )
        completed = {int(value) for value in self.session.get("completed_batches", [])}
        selector = _BatchSelectionDialog(self, self.chapter_segments, batch_size, completed)
        self.wait_window(selector)
        if selector.result is None:
            return
        self.active_batch = selector.result
        self.session["active_batch"] = self.active_batch
        self.session["engine"] = self.engine_choice.get()
        self._persist_session()
        self._update_save_state()

        if self.active_batch in completed:
            answers = self.session.get("batch_translations", {}).get(str(self.active_batch), [])
            self._display_batch(self.active_batch, answers)
            self.status.set(f"Lô {self.active_batch + 1} đã hoàn thành. Có thể lưu bản dịch.")
            return

        if self.engine_choice.get() == "Hachimi":
            self._run_hachimi_batch(self.active_batch)
            return

        profile = self.session.get("profiles", {}).get(str(self.active_batch), "")
        if profile:
            self._open_turn_prompt(self.active_batch)
        else:
            self._open_profile_dialog(self.active_batch)

    def _profile_prompt(self, batch_index: int) -> str:
        chapters = self._batch_slice(batch_index)
        content = "\n\n".join(text for _title, text in chapters)
        name = self.source.stem if self.source else "Tiểu thuyết"
        return (
            "Bạn là biên dịch viên/biên tập viên tiểu thuyết Trung–Việt chuyên nghiệp. "
            "Đây là bước lập HỒ SƠ THAM CHIẾU XUYÊN SUỐT, KHÔNG PHẢI BƯỚC DỊCH.\n"
            "Đọc phần RAW bên dưới và tạo hồ sơ ngắn gọn nhưng đủ dùng cho các lượt dịch sau: "
            "thể loại/bối cảnh; nhân vật và quan hệ; cách xưng hô đã xác nhận; địa danh, tổ chức, "
            "công pháp, chức danh và thuật ngữ; quy tắc phiên âm/tên riêng; giọng văn; các điểm "
            "chưa rõ cần giữ trung tính. Phân biệt dữ kiện chắc chắn với suy luận, không tự bịa canon. "
            "Ưu tiên RAW, không dùng kiến thức ngoài để ghi đè nội dung nguồn. Giữ thuật ngữ nhất quán. "
            "Chỉ trả hồ sơ tham chiếu, tuyệt đối không dịch hoặc viết lại RAW ở bước này.\n\n"
            f"TÊN TRUYỆN: {name}\n"
            f"LÔ: {batch_index + 1}/{self._batch_count()} · {self._range_label(batch_index)}\n\n"
            f"RAW:\n{content}"
        )

    def _open_profile_dialog(self, batch_index: int):
        prompt = self._profile_prompt(batch_index)

        def accepted(profile: str):
            self.session.setdefault("profiles", {})[str(batch_index)] = profile
            self.session["turn_index"] = 0
            self.session["engine"] = "ChatGPT của tôi"
            self._persist_session()
            self._open_turn_prompt(batch_index)

        _ProfileDialog(self, prompt, accepted)

    def _turn_prompt(self, batch_index: int, turn_index: int) -> str:
        turns = self._turns_for_batch(batch_index)
        current = turns[turn_index]
        first_chapter = batch_index * int(self.session["chapters_per_batch"]) + turn_index * int(self.session["chapters_per_turn"]) + 1
        last_chapter = first_chapter + len(current) - 1
        profile = self.session.get("profiles", {}).get(str(batch_index), "")
        dictionary = self.dictionary_text
        parts = [
            "Bạn là biên dịch viên/biên tập viên tiểu thuyết chuyên nghiệp. "
            "Hãy tạo văn xuôi tiếng Việt tự nhiên, mạch lạc, trau chuốt; không bám máy móc vào trật tự câu tiếng Trung. "
            "Không thêm, lược, bịa tình tiết, thông tin, cảm xúc hoặc diễn biến. "
            "Giữ nguyên đầy đủ tiêu đề chương, thứ tự, tên riêng và thuật ngữ. "
            "Không gộp, tách, bỏ hoặc tự tạo chương. Duy trì xưng hô và thuật ngữ theo hồ sơ. "
            "Chỉ trả nội dung đã dịch, không giải thích, không mở đầu hay kết luận ngoài truyện.",
            f"TÊN TRUYỆN: {self.source.stem if self.source else 'Tiểu thuyết'}",
            f"LÔ {batch_index + 1}/{self._batch_count()} · LƯỢT {turn_index + 1}/{len(turns)} · CHƯƠNG {first_chapter}–{last_chapter}",
            "HỒ SƠ THAM CHIẾU XUYÊN SUỐT:\n" + profile,
        ]
        if dictionary:
            parts.append("TỪ ĐIỂN/THUẬT NGỮ ƯU TIÊN:\n" + dictionary)
        parts.append("RAW CẦN DỊCH:\n" + "\n\n".join(text for _title, text in current))
        return "\n\n".join(parts)

    def _open_turn_prompt(self, batch_index: int):
        turns = self._turns_for_batch(batch_index)
        if not turns:
            messagebox.showerror("Lỗi chia lượt", "Lô này không có nội dung để dịch.")
            return
        turn_index = int(self.session.get("turn_index", 0))
        turn_index = max(0, min(turn_index, len(turns) - 1))
        self.session["turn_index"] = turn_index
        self._show_turn_source(batch_index, turn_index)
        prompt = self._turn_prompt(batch_index, turn_index)
        title = (
            f"Lượt dịch {turn_index + 1}/{len(turns)} · "
            f"Lô {batch_index + 1} · {self._range_label(batch_index)}"
        )
        if self.turn_dialog and self.turn_dialog.winfo_exists():
            self.turn_dialog.show_prompt(title, prompt)
            return
        self.turn_dialog = _TurnPromptDialog(
            self,
            on_continue=self._accept_current_turn,
            on_cancel=self._cancel_turn_dialog,
        )
        self.turn_dialog.show_prompt(title, prompt)
        self.turn_dialog.lift()

    def _show_turn_source(self, batch_index: int, turn_index: int):
        turns = self._turns_for_batch(batch_index)
        if not turns:
            return
        current = turns[turn_index]
        self.raw_box.delete("1.0", "end")
        self.raw_box.insert("1.0", "\n\n".join(text for _title, text in current))
        previous_answers = self.session.get("batch_translations", {}).get(str(batch_index), [])
        answer = previous_answers[turn_index] if turn_index < len(previous_answers) else ""
        self.vi_box.delete("1.0", "end")
        if answer:
            self.vi_box.insert("1.0", answer)

    def _accept_current_turn(self):
        if self.active_batch is None:
            return
        answer = self.vi_box.get("1.0", "end-1c").strip()
        if not answer:
            messagebox.showwarning(
                "Chưa có bản dịch",
                "Hãy dán kết quả ChatGPT vào khung BẢN DỊCH của cửa sổ chính trước khi tiếp tục.",
            )
            return
        batch_index = self.active_batch
        turn_index = int(self.session.get("turn_index", 0))
        turns = self._turns_for_batch(batch_index)
        translations = self.session.setdefault("batch_translations", {}).setdefault(
            str(batch_index), [""] * len(turns)
        )
        while len(translations) < len(turns):
            translations.append("")
        translations[turn_index] = answer
        self.session["batch_translations"][str(batch_index)] = translations
        self.session["turn_index"] = turn_index + 1
        self._persist_session()

        if turn_index + 1 < len(turns):
            self._open_turn_prompt(batch_index)
            return

        completed = set(int(value) for value in self.session.get("completed_batches", []))
        completed.add(batch_index)
        self.session["completed_batches"] = sorted(completed)
        self.session["turn_index"] = 0
        self._persist_session()
        if self.turn_dialog and self.turn_dialog.winfo_exists():
            self.turn_dialog.destroy()
        self.turn_dialog = None
        self._display_batch(batch_index, translations)
        self._update_save_state()
        self.status.set(f"Đã hoàn thành lô {batch_index + 1}. Có thể lưu bản dịch.")

    def _cancel_turn_dialog(self):
        self._persist_session()
        self.turn_dialog = None
        self.status.set("Đã tạm dừng phiên. Tiến độ các lượt đã lưu vẫn được giữ.")

    def _display_batch(self, batch_index: int, translations: list[str]):
        self.raw_box.delete("1.0", "end")
        self.raw_box.insert(
            "1.0",
            "\n\n".join(text for _title, text in self._batch_slice(batch_index)),
        )
        self.vi_box.delete("1.0", "end")
        self.vi_box.insert("1.0", "\n\n".join(item for item in translations if item))

    def _update_save_state(self):
        enabled = (
            self.active_batch is not None
            and self.active_batch in {
                int(value) for value in self.session.get("completed_batches", [])
            }
        )
        self.save_button.configure(state="normal" if enabled else "disabled")

    def _run_hachimi_batch(self, batch_index: int):
        if self.local_busy:
            return
        chapters = self._batch_slice(batch_index)
        model_id = HACHIMI_MODELS.get(self.session.get("hachimi_model", list(HACHIMI_MODELS)[0]))
        if not model_id:
            model_id = list(HACHIMI_MODELS.values())[0]
        self.local_busy = True
        self.start_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status.set(f"Đang dịch lô {batch_index + 1} bằng Hachimi trên CPU...")

        def report(message: str):
            try:
                self.after(0, lambda value=message: self.status.set(value))
            except tk.TclError:
                pass

        def work():
            try:
                translator = HachimiTranslator(model_id, progress=report)
                results = []
                for index, (title, text) in enumerate(chapters, start=1):
                    report(f"Hachimi · lô {batch_index + 1} · chương {index}/{len(chapters)}: {title}")
                    results.append(translator.translate(text))
                self.after(0, lambda values=results: self._hachimi_done(batch_index, values))
            except Exception as exc:
                self.after(0, lambda error=str(exc): self._hachimi_failed(error))

        threading.Thread(target=work, daemon=True).start()

    def _hachimi_done(self, batch_index: int, results: list[str]):
        self.local_busy = False
        self.start_button.configure(state="normal")
        self.session.setdefault("batch_translations", {})[str(batch_index)] = results
        completed = set(int(value) for value in self.session.get("completed_batches", []))
        completed.add(batch_index)
        self.session["completed_batches"] = sorted(completed)
        self.session["engine"] = "Hachimi"
        self._persist_session()
        self._display_batch(batch_index, results)
        self._update_save_state()
        self.status.set(f"Hachimi đã dịch xong lô {batch_index + 1}. Có thể lưu bản dịch.")

    def _hachimi_failed(self, error: str):
        self.local_busy = False
        self.start_button.configure(state="normal")
        self.status.set("Dịch Hachimi thất bại. Tiến độ lô chưa được đánh dấu hoàn thành.")
        messagebox.showerror("Lỗi Hachimi", error)

    def save_translation(self):
        if self.active_batch is None or self.active_batch not in {
            int(value) for value in self.session.get("completed_batches", [])
        }:
            messagebox.showinfo("Lô chưa hoàn thành", "Chỉ có thể lưu sau khi hoàn thành tất cả lượt của lô đang chọn.")
            return
        translated_dir = project_dir_for(self.source) / "translated"
        translated_dir.mkdir(parents=True, exist_ok=True)
        completed = sorted(int(value) for value in self.session.get("completed_batches", []))
        batch_size = int(self.session.get("chapters_per_batch", 20))
        batch_outputs = self.session.get("batch_translations", {})
        current_answers = batch_outputs.get(str(self.active_batch), [])
        batch_text = "\n\n".join(value for value in current_answers if value).strip()
        batch_path = translated_dir / f"translated_batch_{self.active_batch + 1:02d}.txt"
        batch_path.write_text(batch_text, encoding="utf-8-sig")

        all_parts = []
        for batch_index in completed:
            values = batch_outputs.get(str(batch_index), [])
            part = "\n\n".join(value for value in values if value).strip()
            if part:
                all_parts.append(part)
        partial_path = translated_dir / "translated_partial.txt"
        partial_path.write_text("\n\n".join(all_parts), encoding="utf-8-sig")

        total_batches = self._batch_count()
        final_path = translated_dir / "translated.txt"
        is_all_complete = len(completed) == total_batches and all(
            index in completed for index in range(total_batches)
        )
        if is_all_complete:
            final_path.write_text("\n\n".join(all_parts), encoding="utf-8-sig")
            saved_path = final_path
            message = "Đã hoàn thành tất cả các lô. Bản dịch đầy đủ đã được lưu."
        else:
            saved_path = batch_path
            message = (
                f"Đã lưu lô {self.active_batch + 1}/{total_batches}.\n"
                "Bản tổng hợp tạm thời cũng đã được cập nhật. "
                "Khi hoàn thành tất cả lô, ứng dụng sẽ tạo translated.txt."
            )
        self.status.set(f"Đã lưu: {saved_path.name}")
        messagebox.showinfo("Lưu bản dịch", f"{message}\n\n{saved_path}")

