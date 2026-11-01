from pathlib import Path
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from app.config import (
    DOWNLOAD_DIR, WEBTOEPUB_URL, TTS_VOICES, TTS_RATES, HACHIMI_MODELS,
    project_dir_for,
)
from app.utils import read_text_file, split_text, parse_drop_files
from app.services.browser_service import open_chrome
from app.services.epub_service import convert_epub_to_txt
from app.services.hachimi_service import HachimiTranslator
from app.services.tts_service import split_chapters, create_mp3
from app.ui.widgets import heading, panel, button, text_box, try_enable_drop, BG, PANEL, PANEL_2, COPPER, TEXT, MUTED


class BasePage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app

    def on_show(self):
        pass


class DashboardPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        heading(self, "Thư viện bí mật", "Nơi thu thập, chuyển ngữ và thổi hồn vào những câu chuyện")
        intro = tk.Frame(self, bg=BG)
        intro.pack(fill="x", pady=(0, 22))
        tk.Label(intro, text="Một hành trình khép kín từ bản raw đến audiobook.", bg=BG, fg=MUTED, font=("Segoe UI", 11)).pack(anchor="w")
        cards = tk.Frame(self, bg=BG)
        cards.pack(fill="both", expand=True)
        entries = [
            ("01", "CÀO TRUYỆN", "Chrome thật · WebToEpub · EPUB → TXT", "crawl", "◈"),
            ("02", "DỊCH TRUYỆN", "ChatGPT clipboard · HachimiMT CPU", "translate", "文"),
            ("03", "TẠO AUDIO", "NamMinh · HoaiMy · MP3 theo chương", "audio", "♫"),
        ]
        for col, (number, title, desc, page, symbol) in enumerate(entries):
            cards.grid_columnconfigure(col, weight=1, uniform="cards")
            card = tk.Frame(cards, bg=PANEL, padx=22, pady=24, highlightthickness=1, highlightbackground="#543727")
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 10, 0 if col == 2 else 10), pady=4)
            tk.Label(card, text=number, bg=PANEL, fg=COPPER, font=("Georgia", 10)).pack(anchor="w")
            tk.Label(card, text=symbol, bg=PANEL, fg=COPPER, font=("Georgia", 37)).pack(anchor="w", pady=(16, 18))
            tk.Label(card, text=title, bg=PANEL, fg=TEXT, font=("Georgia", 16, "bold")).pack(anchor="w")
            tk.Label(card, text=desc, bg=PANEL, fg=MUTED, font=("Segoe UI", 9), wraplength=220, justify="left").pack(anchor="w", pady=(9, 22))
            button(card, "MỞ KHU VỰC  →", lambda p=page: app.show_page(p), accent=True).pack(anchor="w")
        note = panel(self, "Ghi chú vận hành")
        note.pack(fill="x", pady=(22, 0))
        tk.Label(note, text="Chrome và Edge TTS cần Internet. HachimiMT chạy cục bộ trên CPU; mô hình chỉ tải khi người dùng chọn dịch máy lần đầu.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9), wraplength=1000, justify="left").pack(anchor="w")


class CrawlPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        heading(self, "Cào truyện", "Mở Google Chrome thật, dùng WebToEpub để đóng gói truyện thành EPUB")
        controls = tk.Frame(self, bg=BG)
        controls.pack(fill="x", pady=(0, 14))
        button(controls, "MỞ CHROME THẬT", self.launch_chrome, accent=True).pack(side="left")
        button(controls, "CÀI / MỞ WEBTOEPUB", lambda: webbrowser.open(WEBTOEPUB_URL)).pack(side="left", padx=8)
        button(controls, "MỞ THƯ MỤC TẢI", lambda: self.open_folder(DOWNLOAD_DIR)).pack(side="left")
        info = panel(self, "Quy trình")
        info.pack(fill="x", pady=(0, 14))
        tk.Label(info, text="1. Trong Chrome, vào website truyện và mở mục lục/chương đầu.  2. Nhấn biểu tượng WebToEpub trên thanh công cụ.  3. Kiểm tra truyện rồi Pack EPUB.  4. File EPUB sẽ xuất hiện trong danh sách bên dưới.", bg=PANEL, fg=MUTED, justify="left", wraplength=1050, font=("Segoe UI", 9)).pack(anchor="w")
        list_panel = panel(self, "EPUB đã tải")
        list_panel.pack(fill="both", expand=True)
        top = tk.Frame(list_panel, bg=PANEL)
        top.pack(fill="x")
        tk.Label(top, text="Danh sách file trong thư mục downloads", bg=PANEL, fg=TEXT).pack(side="left")
        button(top, "LÀM MỚI", self.refresh_files).pack(side="right")
        self.files = tk.Listbox(list_panel, bg="#100B0A", fg=TEXT, selectbackground="#63402F", relief="flat", height=12, font=("Segoe UI", 10))
        self.files.pack(fill="both", expand=True, pady=10)
        try_enable_drop(self.files, self._on_drop)
        bottom = tk.Frame(list_panel, bg=PANEL)
        bottom.pack(fill="x")
        button(bottom, "CHUYỂN EPUB → TXT", self.convert_selected, accent=True).pack(side="left")
        button(bottom, "CHỌN EPUB KHÁC", self.choose_epub).pack(side="left", padx=8)
        self.note = tk.Label(bottom, text="Tự kiểm tra thư mục mỗi vài giây khi trang này đang mở.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
        self.note.pack(side="left", padx=12)
        self._poll_id = None

    def on_show(self):
        self.refresh_files()
        self._schedule_poll()

    def _schedule_poll(self):
        if self._poll_id:
            self.after_cancel(self._poll_id)
        self._poll_id = self.after(3500, self._poll)

    def _poll(self):
        if self.winfo_ismapped():
            self.refresh_files()
            self._poll_id = self.after(3500, self._poll)

    def _on_drop(self, data):
        paths = parse_drop_files(data)
        for item in paths:
            path = Path(item.strip("{}"))
            if path.suffix.lower() == ".epub" and path.exists():
                self._selected_external = path
                self.note.config(text=f"Đã nhận: {path.name}")
                self.convert_path(path)
                return

    def launch_chrome(self):
        ok, text = open_chrome()
        self.note.config(text=text)
        self.app.set_status(text)
        if not ok:
            messagebox.showwarning("Không mở được Chrome", text)

    def open_folder(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def refresh_files(self):
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        selected = None
        try:
            selected = self.files.get(self.files.curselection()[0])
        except Exception:
            pass
        self.files.delete(0, "end")
        for path in sorted(DOWNLOAD_DIR.glob("*.epub"), key=lambda p: p.stat().st_mtime, reverse=True):
            self.files.insert("end", path.name)
        if selected:
            try:
                idx = list(self.files.get(0, "end")).index(selected)
                self.files.selection_set(idx)
            except ValueError:
                pass
        self.note.config(text=f"Tìm thấy {self.files.size()} file EPUB trong {DOWNLOAD_DIR}")

    def choose_epub(self):
        path = filedialog.askopenfilename(title="Chọn EPUB", filetypes=[("EPUB", "*.epub")])
        if path:
            self.convert_path(Path(path))

    def convert_selected(self):
        try:
            name = self.files.get(self.files.curselection()[0])
        except Exception:
            messagebox.showinfo("Chưa chọn EPUB", "Hãy chọn một file EPUB trong danh sách.")
            return
        self.convert_path(DOWNLOAD_DIR / name)

    def convert_path(self, source: Path):
        self.note.config(text=f"Đang chuyển {source.name}...")
        self.app.set_status(f"Đang chuyển EPUB: {source.name}")
        def worker():
            try:
                project = project_dir_for(source)
                output = project / "raw" / f"{source.stem}.txt"
                result = convert_epub_to_txt(source, output)
                self.after(0, lambda: self._convert_done(result))
            except Exception as exc:
                self.after(0, lambda e=str(exc): self._convert_error(e))
        threading.Thread(target=worker, daemon=True).start()

    def _convert_done(self, result: Path):
        self.note.config(text=f"Đã tạo TXT: {result}")
        self.app.set_status("Chuyển EPUB → TXT hoàn tất")
        if messagebox.askyesno("Chuyển đổi hoàn tất", f"Đã lưu file:\n{result}\n\nMở thư mục chứa TXT?"):
            self.open_folder(result.parent)

    def _convert_error(self, error: str):
        self.note.config(text="Chuyển đổi thất bại")
        self.app.set_status("Lỗi chuyển EPUB")
        messagebox.showerror("Không chuyển được EPUB", error)


class TranslatePage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        heading(self, "Dịch truyện", "Hai khung RAW / BẢN DỊCH · ChatGPT qua clipboard hoặc HachimiMT chạy cục bộ")
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", pady=(0, 12))
        button(bar, "MỞ FILE RAW", self.load_file, accent=True).pack(side="left")
        button(bar, "MỞ CHATGPT", lambda: webbrowser.open("https://chatgpt.com/")).pack(side="left", padx=8)
        button(bar, "LƯU BẢN DỊCH", self.save_translation).pack(side="left")
        button(bar, "XUẤT TXT", self.export_translation).pack(side="left", padx=8)
        self.file_label = tk.Label(bar, text="Chưa chọn file", bg=BG, fg=MUTED, font=("Segoe UI", 8))
        self.file_label.pack(side="left", padx=12)
        columns = tk.Frame(self, bg=BG)
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=1, uniform="translate")
        columns.grid_columnconfigure(1, weight=1, uniform="translate")
        columns.grid_rowconfigure(0, weight=1)
        left = panel(columns, "Bản RAW")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        right = panel(columns, "Bản dịch")
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.raw_frame, self.raw_text = text_box(left, 20)
        self.raw_frame.pack(fill="both", expand=True)
        self.trans_frame, self.trans_text = text_box(right, 20)
        self.trans_frame.pack(fill="both", expand=True)
        try_enable_drop(self.raw_text, self._on_drop)
        nav = tk.Frame(self, bg=BG)
        nav.pack(fill="x", pady=(12, 0))
        self.chunk_var = tk.StringVar(value="Chưa có nội dung")
        tk.Label(nav, textvariable=self.chunk_var, bg=BG, fg=COPPER, font=("Segoe UI", 9, "bold")).pack(side="left")
        button(nav, "← ĐOẠN TRƯỚC", self.previous_chunk).pack(side="right", padx=5)
        button(nav, "ĐOẠN TIẾP →", self.next_chunk, accent=True).pack(side="right")
        actions = tk.Frame(self, bg=BG)
        actions.pack(fill="x", pady=(10, 0))
        button(actions, "SAO CHÉP PROMPT", self.copy_prompt, accent=True).pack(side="left")
        button(actions, "NHẬN TỪ CLIPBOARD", self.paste_translation).pack(side="left", padx=8)
        ttk.Label(actions, text="Mô hình cục bộ:").pack(side="left", padx=(18, 5))
        self.model_var = tk.StringVar(value=list(HACHIMI_MODELS.keys())[0])
        ttk.Combobox(actions, textvariable=self.model_var, values=list(HACHIMI_MODELS.keys()), state="readonly", width=28).pack(side="left")
        button(actions, "DỊCH BẰNG HACHIMI", self.translate_local).pack(side="left", padx=8)
        self.progress_var = tk.StringVar(value="Sẵn sàng")
        tk.Label(actions, textvariable=self.progress_var, bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=8)
        self.source_path: Path | None = None
        self.chunks: list[str] = []
        self.translations: list[str] = []
        self.index = 0
        self.local_queue = queue.Queue()

    def _on_drop(self, data):
        paths = parse_drop_files(data)
        if paths:
            path = Path(paths[0].strip("{}"))
            if path.is_file() and path.suffix.lower() == ".txt":
                self.load_path(path)

    def load_file(self):
        path = filedialog.askopenfilename(title="Chọn bản RAW", filetypes=[("Text", "*.txt"), ("Tất cả", "*.*")])
        if path:
            self.load_path(Path(path))

    def load_path(self, path: Path):
        try:
            text = read_text_file(path)
        except Exception as exc:
            messagebox.showerror("Lỗi đọc file", str(exc)); return
        self.source_path = path
        self.chunks = split_text(text, 3600)
        self.translations = [""] * len(self.chunks)
        self.index = 0
        project = project_dir_for(path)
        self.file_label.config(text=path.name)
        self._show_chunk()
        self.app.set_status(f"Đã nạp {len(self.chunks)} đoạn RAW")

    def _capture_current_translation(self):
        if self.chunks:
            self.translations[self.index] = self.trans_text.get("1.0", "end-1c").strip()

    def _show_chunk(self):
        self.raw_text.delete("1.0", "end")
        self.trans_text.delete("1.0", "end")
        if not self.chunks:
            self.chunk_var.set("Chưa có nội dung")
            return
        self.raw_text.insert("1.0", self.chunks[self.index])
        self.trans_text.insert("1.0", self.translations[self.index])
        self.chunk_var.set(f"ĐOẠN {self.index + 1}/{len(self.chunks)}")

    def previous_chunk(self):
        if not self.chunks or self.index == 0: return
        self._capture_current_translation(); self._write_project_translation()
        self.index -= 1; self._show_chunk()

    def next_chunk(self):
        if not self.chunks or self.index >= len(self.chunks) - 1: return
        self._capture_current_translation(); self._write_project_translation()
        self.index += 1; self._show_chunk()

    def _prompt_text(self):
        self._capture_current_translation()
        title = self.source_path.stem if self.source_path else "Tiểu thuyết"
        return (
            "Bạn là biên dịch viên/biên tập viên tiểu thuyết Trung→Việt chuyên nghiệp.\n"
            "Dịch tự nhiên, mạch lạc như văn xuôi Việt; không bám máy móc trật tự câu Hán ngữ. "
            "Giữ nguyên tên riêng, thuật ngữ và quan hệ xưng hô; không tự ý thêm/bớt tình tiết. "
            "Chỉ trả về bản dịch, không giải thích, không mở đầu.\n\n"
            f"Tên truyện: {title}\nĐoạn: {self.index + 1}/{len(self.chunks)}\n\n"
            "NỘI DUNG RAW:\n" + self.chunks[self.index]
        )

    def copy_prompt(self):
        if not self.chunks:
            messagebox.showinfo("Chưa có RAW", "Hãy mở file TXT trước."); return
        prompt = self._prompt_text()
        self.clipboard_clear(); self.clipboard_append(prompt); self.update()
        self.progress_var.set("Đã sao chép prompt. Dán vào ChatGPT, rồi copy kết quả trở lại đây.")
        self.app.set_status("Prompt đã được sao chép vào clipboard")

    def paste_translation(self):
        try:
            content = self.clipboard_get().strip()
        except tk.TclError:
            content = ""
        if not content:
            messagebox.showwarning("Clipboard trống", "Hãy copy phần trả lời từ ChatGPT trước."); return
        self.trans_text.delete("1.0", "end"); self.trans_text.insert("1.0", content)
        self._capture_current_translation()
        self._write_project_translation()
        self.progress_var.set("Đã nhận bản dịch từ clipboard và lưu tạm.")

    def save_translation(self):
        self._capture_current_translation()
        if not any(self.translations):
            messagebox.showinfo("Chưa có bản dịch", "Chưa có đoạn dịch nào để lưu."); return
        self._write_project_translation()
        messagebox.showinfo("Đã lưu", "Đã lưu tiến độ bản dịch trong thư mục dự án.")

    def _write_project_translation(self):
        if not self.source_path: return
        project = project_dir_for(self.source_path)
        target = project / "translated" / "translated_partial.txt"
        joined = "\n\n".join(self.translations)
        target.write_text(joined, encoding="utf-8-sig")

    def export_translation(self):
        self._capture_current_translation()
        if not any(self.translations):
            messagebox.showinfo("Chưa có bản dịch", "Hãy dịch ít nhất một đoạn trước."); return
        default = (self.source_path.stem + "_vi.txt") if self.source_path else "ban_dich.txt"
        path = filedialog.asksaveasfilename(title="Xuất bản dịch", defaultextension=".txt", initialfile=default, filetypes=[("Text", "*.txt")])
        if path:
            Path(path).write_text("\n\n".join(self.translations), encoding="utf-8-sig")
            messagebox.showinfo("Xuất thành công", f"Đã lưu: {path}")

    def translate_local(self):
        if not self.chunks:
            messagebox.showinfo("Chưa có RAW", "Hãy mở file TXT trước."); return
        model_id = HACHIMI_MODELS[self.model_var.get()]
        self._capture_current_translation()
        self.progress_var.set("Đang khởi tạo Hachimi...")
        self.app.set_status("Dịch bằng HachimiMT trên CPU")
        threading.Thread(target=self._local_worker, args=(model_id,), daemon=True).start()
        self.after(400, self._poll_local_queue)

    def _local_worker(self, model_id):
        try:
            engine = HachimiTranslator(model_id, progress=lambda msg: self.local_queue.put(("message", msg)))
            for idx, chunk in enumerate(self.chunks):
                if self.translations[idx].strip():
                    self.local_queue.put(("skip", idx))
                    continue
                translated = engine.translate(chunk)
                self.local_queue.put(("result", idx, translated))
            self.local_queue.put(("done",))
        except Exception as exc:
            self.local_queue.put(("error", str(exc)))

    def _poll_local_queue(self):
        try:
            while True:
                item = self.local_queue.get_nowait()
                kind = item[0]
                if kind == "message":
                    self.progress_var.set(item[1])
                elif kind == "result":
                    idx, text = item[1], item[2]
                    self.translations[idx] = text
                    self.index = idx
                    self._show_chunk()
                    self._write_project_translation()
                    self.progress_var.set(f"Đã dịch đoạn {idx + 1}/{len(self.chunks)}")
                elif kind == "skip":
                    pass
                elif kind == "done":
                    self.progress_var.set("Hachimi đã dịch xong các đoạn còn trống.")
                    self.app.set_status("HachimiMT hoàn tất")
                elif kind == "error":
                    self.progress_var.set("Dịch thất bại")
                    messagebox.showerror("Lỗi Hachimi", item[1])
        except queue.Empty:
            pass
        if self.progress_var.get() not in ("Hachimi đã dịch xong các đoạn còn trống.", "Dịch thất bại"):
            self.after(400, self._poll_local_queue)


class AudioPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        heading(self, "Tạo Audio", "Chuyển bản dịch tiếng Việt thành audiobook MP3 theo từng chương")
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", pady=(0, 12))
        button(top, "MỞ FILE TXT ĐÃ DỊCH", self.load_file, accent=True).pack(side="left")
        self.file_label = tk.Label(top, text="Chưa chọn file", bg=BG, fg=MUTED, font=("Segoe UI", 8))
        self.file_label.pack(side="left", padx=12)
        columns = tk.Frame(self, bg=BG)
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=1, uniform="audio")
        columns.grid_columnconfigure(1, weight=1, uniform="audio")
        columns.grid_rowconfigure(0, weight=1)
        content_panel = panel(columns, "Nội dung tạo")
        content_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        result_panel = panel(columns, "Kết quả")
        result_panel.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.content_frame, self.content_text = text_box(content_panel, 20)
        self.content_frame.pack(fill="both", expand=True)
        try_enable_drop(self.content_text, self._on_drop)
        self.results = ttk.Treeview(result_panel, columns=("chapter", "state", "file"), show="headings", height=18)
        self.results.heading("chapter", text="TÁC VỤ")
        self.results.heading("state", text="TRẠNG THÁI")
        self.results.heading("file", text="FILE")
        self.results.column("chapter", width=150)
        self.results.column("state", width=110)
        self.results.column("file", width=180)
        self.results.pack(fill="both", expand=True)
        settings = tk.Frame(self, bg=BG)
        settings.pack(fill="x", pady=(12, 0))
        tk.Label(settings, text="Tốc độ", bg=BG, fg=MUTED).pack(side="left", padx=(12, 0))
        self.rate_var = tk.StringVar(value="1.0x")
        ttk.Combobox(settings, textvariable=self.rate_var, values=list(TTS_RATES.keys()), state="readonly", width=9).pack(side="left", padx=7)
        button(settings, "TẠO AUDIO", self.generate, accent=True).pack(side="left", padx=8)
        button(settings, "NGHE THỬ / MỞ MP3", self.play_selected).pack(side="left")
        button(settings, "MỞ THƯ MỤC AUDIO", self.open_audio_folder).pack(side="left", padx=8)
        self.progress_var = tk.StringVar(value="Sẵn sàng")
        tk.Label(settings, textvariable=self.progress_var, bg=BG, fg=COPPER, font=("Segoe UI", 8)).pack(side="left", padx=10)
        self.source_path: Path | None = None
        self.audio_dir: Path | None = None
        self.task_queue = queue.Queue()
        self.is_generating = False

    def _on_drop(self, data):
        paths = parse_drop_files(data)
        if paths:
            path = Path(paths[0].strip("{}"))
            if path.is_file() and path.suffix.lower() == ".txt":
                self.load_path(path)

    def load_file(self):
        path = filedialog.askopenfilename(title="Chọn bản dịch", filetypes=[("Text", "*.txt"), ("Tất cả", "*.*")])
        if path:
            self.load_path(Path(path))

    def load_path(self, path: Path):
        try:
            text = read_text_file(path)
        except Exception as exc:
            messagebox.showerror("Lỗi đọc file", str(exc)); return
        if not text.strip():
            messagebox.showwarning("File trống", "File TXT không có nội dung."); return
        self.source_path = path
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", text)
        project = project_dir_for(path)
        self.audio_dir = project / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.file_label.config(text=path.name)
        self.app.set_status(f"Đã nạp nội dung audio: {path.name}")

    def generate(self):
        if self.is_generating:
            messagebox.showinfo("Đang tạo", "Tác vụ tạo audio hiện đang chạy."); return
        text = self.content_text.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo("Chưa có nội dung", "Hãy mở hoặc kéo thả file TXT đã dịch vào khung bên trái."); return
        if not self.source_path:
            self.source_path = Path("truyen.txt")
            self.audio_dir = Path.cwd() / "data" / "audio"
        chapters = split_chapters(text)
        if not chapters:
            messagebox.showwarning("Không có chương", "Không tìm thấy nội dung phù hợp để đọc."); return
        self.results.delete(*self.results.get_children())
        for index, (title, _body) in enumerate(chapters, start=1):
            self.results.insert("", "end", iid=str(index), values=(f"AU ({index}) · {title[:28]}", "Đang chờ", f"AU_{index:03d}.mp3"))
        voice = TTS_VOICES[self.voice_var.get()]
        rate = TTS_RATES[self.rate_var.get()]
        self.is_generating = True
        self.progress_var.set("Đang tạo...")
        self.app.set_status("Edge TTS đang xử lý; cần Internet")
        threading.Thread(target=self._audio_worker, args=(chapters, voice, rate), daemon=True).start()
        self.after(350, self._poll_audio)

    def _audio_worker(self, chapters, voice, rate):
        try:
            self.audio_dir.mkdir(parents=True, exist_ok=True)
            for index, (title, body) in enumerate(chapters, start=1):
                self.task_queue.put(("state", index, "Đang tạo"))
                destination = self.audio_dir / f"AU_{index:03d}.mp3"
                create_mp3(body, voice, rate, destination)
                self.task_queue.put(("done_one", index, str(destination)))
            self.task_queue.put(("done",))
        except Exception as exc:
            self.task_queue.put(("error", str(exc)))

    def _poll_audio(self):
        try:
            while True:
                item = self.task_queue.get_nowait()
                if item[0] == "state":
                    idx, state = item[1], item[2]
                    vals = list(self.results.item(str(idx), "values")); vals[1] = state
                    self.results.item(str(idx), values=vals)
                    self.progress_var.set(f"Đang tạo AU ({idx})...")
                elif item[0] == "done_one":
                    idx, path = item[1], item[2]
                    vals = list(self.results.item(str(idx), "values")); vals[1] = "Hoàn thành"; vals[2] = Path(path).name
                    self.results.item(str(idx), values=vals)
                elif item[0] == "done":
                    self.is_generating = False
                    self.progress_var.set("Đã tạo xong toàn bộ audio.")
                    self.app.set_status("Tạo audio hoàn tất")
                    messagebox.showinfo("Hoàn thành", f"Đã tạo audio trong:\n{self.audio_dir}")
                elif item[0] == "error":
                    self.is_generating = False
                    self.progress_var.set("Có lỗi khi tạo audio")
                    self.app.set_status("Tạo audio thất bại")
                    messagebox.showerror("Lỗi Edge TTS", item[1])
        except queue.Empty:
            pass
        if self.is_generating:
            self.after(350, self._poll_audio)

    def play_selected(self):
        selection = self.results.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn AU", "Chọn một AU đã hoàn thành trong danh sách trước."); return
        values = self.results.item(selection[0], "values")
        path = self.audio_dir / values[2]
        if not path.exists():
            messagebox.showwarning("Chưa có file", "AU này chưa tạo xong."); return
        if sys.platform == "win32": os.startfile(path)
        elif sys.platform == "darwin": subprocess.Popen(["open", str(path)])
        else: subprocess.Popen(["xdg-open", str(path)])

    def open_audio_folder(self):
        if not self.audio_dir:
            messagebox.showinfo("Chưa có thư mục", "Hãy nạp file TXT trước."); return
        if sys.platform == "win32": os.startfile(self.audio_dir)
        elif sys.platform == "darwin": subprocess.Popen(["open", str(self.audio_dir)])
        else: subprocess.Popen(["xdg-open", str(self.audio_dir)])
