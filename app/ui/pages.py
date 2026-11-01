from pathlib import Path
import os
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from app.config import DOWNLOAD_DIR, WEBTOEPUB_URL, TTS_VOICES, TTS_RATES, HACHIMI_MODELS, project_dir_for
from app.utils import read_text_file, split_text, parse_drop_files
from app.services.browser_service import open_chrome
from app.services.epub_service import convert_epub_to_txt
from app.services.hachimi_service import HachimiTranslator
from app.services.tts_service import split_chapters
from app.services.tts_api_client import StoryTTSClient, StoryTTSAPIError, load_audio_api_settings, save_audio_api_settings
from app.ui.widgets import heading, panel, button, text_box, try_enable_drop, BG, PANEL, COPPER, TEXT, MUTED


class BasePage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app


class DashboardPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        heading(self, "Thư viện bí mật", "Quy trình khép kín từ bản raw đến audiobook")
        for number, title, detail, page in [
            ("01", "CÀO TRUYỆN", "Chrome thật · WebToEpub · EPUB → TXT", "crawl"),
            ("02", "DỊCH TRUYỆN", "ChatGPT clipboard · HachimiMT CPU", "translate"),
            ("03", "TẠO AUDIO", "NamMinh · HoaiMy · MP3 theo chương", "audio"),
        ]:
            card = panel(self, f"{number} · {title}")
            card.pack(fill="x", pady=7)
            tk.Label(card, text=detail, bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(side="left", padx=(0, 18))
            button(card, "MỞ KHU VỰC →", lambda p=page: app.show_page(p), accent=True).pack(side="right")


class CrawlPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        heading(self, "Cào truyện", "Chrome thật kết hợp WebToEpub; sau đó chuyển EPUB thành TXT")
        bar = tk.Frame(self, bg=BG); bar.pack(fill="x", pady=(0, 12))
        button(bar, "MỞ CHROME THẬT", self.launch_chrome, accent=True).pack(side="left")
        button(bar, "MỞ WEBTOEPUB", lambda: webbrowser.open(WEBTOEPUB_URL)).pack(side="left", padx=7)
        button(bar, "MỞ THƯ MỤC TẢI", lambda: self.open_folder(DOWNLOAD_DIR)).pack(side="left")
        info = panel(self, "Cách dùng")
        info.pack(fill="x", pady=(0, 12))
        tk.Label(info, text="Trong Chrome, mở mục lục truyện → nhấn biểu tượng WebToEpub trên thanh công cụ → Pack EPUB. File tải về sẽ hiện trong danh sách bên dưới.", bg=PANEL, fg=MUTED, wraplength=1000, justify="left").pack(anchor="w")
        area = panel(self, "EPUB đã tải")
        area.pack(fill="both", expand=True)
        self.files = tk.Listbox(area, bg="#100B0A", fg=TEXT, selectbackground="#63402F", relief="flat", height=14)
        self.files.pack(fill="both", expand=True, pady=(0, 10))
        try_enable_drop(self.files, self.drop_epub)
        row = tk.Frame(area, bg=PANEL); row.pack(fill="x")
        button(row, "LÀM MỚI", self.refresh).pack(side="left")
        button(row, "CHỌN EPUB", self.choose_epub).pack(side="left", padx=7)
        button(row, "CHUYỂN EPUB → TXT", self.convert_selected, accent=True).pack(side="left")
        self.note = tk.Label(row, text="Sẵn sàng", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)); self.note.pack(side="left", padx=12)

    def launch_chrome(self):
        ok, msg = open_chrome()
        self.note.config(text=msg); self.app.set_status(msg)
        if not ok: messagebox.showwarning("Chrome", msg)

    def refresh(self):
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.files.delete(0, "end")
        for path in sorted(DOWNLOAD_DIR.glob("*.epub"), key=lambda p: p.stat().st_mtime, reverse=True):
            self.files.insert("end", path.name)
        self.note.config(text=f"Có {self.files.size()} file EPUB")

    def drop_epub(self, data):
        for item in parse_drop_files(data):
            p = Path(item.strip("{}"))
            if p.suffix.lower() == ".epub" and p.exists():
                self.convert_path(p); return

    def choose_epub(self):
        p = filedialog.askopenfilename(filetypes=[("EPUB", "*.epub")])
        if p: self.convert_path(Path(p))

    def convert_selected(self):
        try: name = self.files.get(self.files.curselection()[0])
        except Exception:
            messagebox.showinfo("Chưa chọn file", "Hãy chọn EPUB trước."); return
        self.convert_path(DOWNLOAD_DIR / name)

    def convert_path(self, source: Path):
        self.note.config(text=f"Đang chuyển {source.name}...")
        self.app.set_status("Đang chuyển EPUB → TXT")
        def work():
            try:
                target = project_dir_for(source) / "raw" / f"{source.stem}.txt"
                result = convert_epub_to_txt(source, target)
                self.after(0, lambda: self.convert_done(result))
            except Exception as exc:
                self.after(0, lambda e=str(exc): messagebox.showerror("Lỗi EPUB", e))
        threading.Thread(target=work, daemon=True).start()

    def convert_done(self, path):
        self.note.config(text=f"Đã tạo {path.name}")
        self.app.set_status("Chuyển EPUB → TXT hoàn tất")
        if messagebox.askyesno("Hoàn tất", f"Đã lưu:\n{path}\nMở thư mục?"):
            self.open_folder(path.parent)

    @staticmethod
    def open_folder(path):
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt": os.startfile(path)
        else: webbrowser.open(path.as_uri())


class TranslatePage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        heading(self, "Dịch truyện", "Hai khung RAW / BẢN DỊCH · ChatGPT clipboard hoặc HachimiMT cục bộ")
        bar = tk.Frame(self, bg=BG); bar.pack(fill="x", pady=(0, 10))
        button(bar, "MỞ FILE RAW", self.load_file, accent=True).pack(side="left")
        button(bar, "MỞ CHATGPT", lambda: webbrowser.open("https://chatgpt.com/")).pack(side="left", padx=6)
        button(bar, "SAO CHÉP PROMPT", self.copy_prompt).pack(side="left")
        button(bar, "NHẬN CLIPBOARD", self.paste_clipboard).pack(side="left", padx=6)
        button(bar, "LƯU BẢN DỊCH", self.save_translation).pack(side="left")
        panes = tk.Frame(self, bg=BG); panes.pack(fill="both", expand=True)
        panes.grid_columnconfigure(0, weight=1); panes.grid_columnconfigure(1, weight=1); panes.grid_rowconfigure(0, weight=1)
        left = panel(panes, "Bản RAW"); left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right = panel(panes, "Bản dịch"); right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.raw_frame, self.raw_box = text_box(left, 18); self.raw_frame.pack(fill="both", expand=True)
        self.vi_frame, self.vi_box = text_box(right, 18); self.vi_frame.pack(fill="both", expand=True)
        try_enable_drop(self.raw_box, self.drop_raw)
        nav = tk.Frame(self, bg=BG); nav.pack(fill="x", pady=8)
        self.counter = tk.StringVar(value="Chưa có nội dung")
        tk.Label(nav, textvariable=self.counter, bg=BG, fg=COPPER).pack(side="left")
        button(nav, "← ĐOẠN TRƯỚC", self.prev_chunk).pack(side="right", padx=5)
        button(nav, "ĐOẠN TIẾP →", self.next_chunk).pack(side="right")
        opts = tk.Frame(self, bg=BG); opts.pack(fill="x")
        tk.Label(opts, text="Mô hình:", bg=BG, fg=MUTED).pack(side="left")
        self.model = tk.StringVar(value=list(HACHIMI_MODELS)[0])
        ttk.Combobox(opts, textvariable=self.model, values=list(HACHIMI_MODELS), state="readonly", width=28).pack(side="left", padx=6)
        button(opts, "DỊCH ĐOẠN HIỆN TẠI BẰNG HACHIMI", self.translate_local, accent=True).pack(side="left")
        self.status = tk.StringVar(value="Sẵn sàng")
        tk.Label(opts, textvariable=self.status, bg=BG, fg=MUTED).pack(side="left", padx=10)
        self.source = None; self.chunks = []; self.translations = []; self.index = 0

    def drop_raw(self, data):
        paths = parse_drop_files(data)
        if paths and Path(paths[0].strip("{}")).suffix.lower() == ".txt":
            self.load_path(Path(paths[0].strip("{}")))

    def load_file(self):
        p = filedialog.askopenfilename(filetypes=[("Text", "*.txt")])
        if p: self.load_path(Path(p))

    def load_path(self, path):
        try: raw = read_text_file(path)
        except Exception as exc: messagebox.showerror("Lỗi đọc file", str(exc)); return
        self.source = path; self.chunks = split_text(raw, 3400)
        self.translations = [""] * len(self.chunks); self.index = 0
        self.show_chunk(); self.app.set_status(f"Đã nạp {len(self.chunks)} đoạn")

    def capture(self):
        if self.chunks: self.translations[self.index] = self.vi_box.get("1.0", "end-1c").strip()

    def show_chunk(self):
        self.raw_box.delete("1.0", "end"); self.vi_box.delete("1.0", "end")
        if not self.chunks: self.counter.set("Chưa có nội dung"); return
        self.raw_box.insert("1.0", self.chunks[self.index])
        self.vi_box.insert("1.0", self.translations[self.index])
        self.counter.set(f"ĐOẠN {self.index + 1}/{len(self.chunks)}")

    def prev_chunk(self):
        if self.index > 0:
            self.capture(); self.save_partial(); self.index -= 1; self.show_chunk()

    def next_chunk(self):
        if self.index + 1 < len(self.chunks):
            self.capture(); self.save_partial(); self.index += 1; self.show_chunk()

    def prompt(self):
        self.capture()
        name = self.source.stem if self.source else "Tiểu thuyết"
        return ("Dịch đoạn tiểu thuyết tiếng Trung sau sang tiếng Việt tự nhiên, mạch lạc; "
                "giữ nguyên tên riêng, thuật ngữ, quan hệ xưng hô; không thêm/bớt tình tiết. "
                "Chỉ trả bản dịch, không giải thích.\n"
                f"Tên truyện: {name} · Đoạn {self.index + 1}/{len(self.chunks)}\n\n"
                + self.chunks[self.index])

    def copy_prompt(self):
        if not self.chunks: messagebox.showinfo("Chưa có RAW", "Hãy mở file TXT trước."); return
        self.clipboard_clear(); self.clipboard_append(self.prompt()); self.update()
        self.status.set("Đã chép prompt. Dán vào ChatGPT, rồi copy câu trả lời về đây.")

    def paste_clipboard(self):
        try: text = self.clipboard_get().strip()
        except tk.TclError: text = ""
        if not text: messagebox.showwarning("Clipboard trống", "Hãy copy bản dịch từ ChatGPT trước."); return
        self.vi_box.delete("1.0", "end"); self.vi_box.insert("1.0", text)
        self.capture(); self.save_partial(); self.status.set("Đã nhận bản dịch từ clipboard.")

    def save_partial(self):
        if not self.source: return
        target = project_dir_for(self.source) / "translated" / "translated_partial.txt"
        target.write_text("\n\n".join(self.translations), encoding="utf-8-sig")

    def save_translation(self):
        self.capture()
        if not any(self.translations): messagebox.showinfo("Chưa có bản dịch", "Chưa có nội dung để lưu."); return
        target = project_dir_for(self.source) / "translated" / "translated.txt"
        target.write_text("\n\n".join(self.translations), encoding="utf-8-sig")
        self.save_partial()
        messagebox.showinfo("Đã lưu", f"Bản dịch đã lưu tại:\n{target}")

    def translate_local(self):
        if not self.chunks: messagebox.showinfo("Chưa có RAW", "Hãy mở file TXT trước."); return
        self.capture(); chunk = self.chunks[self.index]; model_id = HACHIMI_MODELS[self.model.get()]
        self.status.set("Đang dịch bằng Hachimi trên CPU...")
        def work():
            try:
                result = HachimiTranslator(model_id).translate(chunk)
                self.after(0, lambda: self.local_done(result))
            except Exception as exc:
                self.after(0, lambda e=str(exc): self.local_error(e))
        threading.Thread(target=work, daemon=True).start()

    def local_done(self, text):
        self.vi_box.delete("1.0", "end"); self.vi_box.insert("1.0", text)
        self.capture(); self.save_partial(); self.status.set("Đã dịch xong đoạn hiện tại.")

    def local_error(self, error):
        self.status.set("Dịch thất bại"); messagebox.showerror("Lỗi Hachimi", error)


class AudioPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        heading(self, "Tạo Audio", "SẢNH TRUYỆN gửi nội dung sang Story TTS API riêng; dịch vụ trả MP3 hoàn chỉnh về đây")

        saved = load_audio_api_settings()
        connection = panel(self, "Kết nối dịch vụ Story TTS API")
        connection.pack(fill="x", pady=(0, 10))
        row = tk.Frame(connection, bg=PANEL)
        row.pack(fill="x")
        tk.Label(row, text="API URL", bg=PANEL, fg=MUTED).pack(side="left")
        self.api_url = tk.StringVar(value=saved["url"])
        ttk.Entry(row, textvariable=self.api_url, width=39).pack(side="left", padx=(6, 14))
        tk.Label(row, text="API KEY", bg=PANEL, fg=MUTED).pack(side="left")
        self.api_key = tk.StringVar(value=saved["api_key"])
        ttk.Entry(row, textvariable=self.api_key, width=35, show="•").pack(side="left", padx=6)
        button(row, "LƯU & KIỂM TRA", self.check_api, accent=True).pack(side="left", padx=(8, 0))
        button(row, "REPO API", lambda: webbrowser.open("https://github.com/hantuyet425/Story-TTS-API")).pack(side="right", padx=(8, 0))
        tk.Label(
            connection,
            text="Mặc định: http://127.0.0.1:8000 · API key được lưu cục bộ trong data/settings.json, không đưa lên GitHub.",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(8, 0))

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", pady=(0, 10))
        button(top, "MỞ FILE TXT ĐÃ DỊCH", self.load_file, accent=True).pack(side="left")
        self.file_label = tk.Label(top, text="Chưa chọn file", bg=BG, fg=MUTED)
        self.file_label.pack(side="left", padx=10)

        source_panel = panel(self, "Nội dung nguồn · có thể xem/sửa trước khi tạo")
        source_panel.pack(fill="x", pady=(0, 8))
        self.content_frame, self.content = text_box(source_panel, 5)
        self.content_frame.pack(fill="x")
        try_enable_drop(self.content, self.drop_audio)

        panes = tk.Frame(self, bg=BG)
        panes.pack(fill="both", expand=True)
        panes.grid_columnconfigure(0, weight=5)
        panes.grid_columnconfigure(1, weight=4)
        panes.grid_rowconfigure(0, weight=1)
        left = panel(panes, "Danh sách đoạn xử lý · theo thứ tự gốc")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right = panel(panes, "Kết quả MP3 hoàn chỉnh theo AU")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.segments = ttk.Treeview(
            left, columns=("length", "state"), show="tree headings", height=18
        )
        self.segments.heading("#0", text="AU / ĐOẠN")
        self.segments.heading("length", text="ĐỘ DÀI")
        self.segments.heading("state", text="TRẠNG THÁI")
        self.segments.column("#0", width=230, minwidth=150, stretch=True)
        self.segments.column("length", width=95, anchor="center", stretch=False)
        self.segments.column("state", width=125, anchor="w", stretch=False)
        segment_scroll = ttk.Scrollbar(left, orient="vertical", command=self.segments.yview)
        self.segments.configure(yscrollcommand=segment_scroll.set)
        self.segments.pack(side="left", fill="both", expand=True)
        segment_scroll.pack(side="right", fill="y")

        self.results = ttk.Treeview(right, columns=("au", "state", "file"), show="headings", height=18)
        for col, label, width in [
            ("au", "TÁC VỤ", 175),
            ("state", "TIẾN ĐỘ API", 155),
            ("file", "FILE MP3", 130),
        ]:
            self.results.heading(col, text=label)
            self.results.column(col, width=width)
        self.results.pack(fill="both", expand=True)

        settings = tk.Frame(self, bg=BG)
        settings.pack(fill="x", pady=10)
        tk.Label(settings, text="Giọng", bg=BG, fg=MUTED).pack(side="left")
        self.voice = tk.StringVar(value=list(TTS_VOICES)[0])
        ttk.Combobox(settings, textvariable=self.voice, values=list(TTS_VOICES), state="readonly", width=18).pack(side="left", padx=6)
        tk.Label(settings, text="Tốc độ", bg=BG, fg=MUTED).pack(side="left")
        self.rate = tk.StringVar(value="1.0x")
        ttk.Combobox(settings, textvariable=self.rate, values=list(TTS_RATES), state="readonly", width=8).pack(side="left", padx=6)
        button(settings, "GỬI TẠO AUDIO", self.generate, accent=True).pack(side="left", padx=6)
        button(settings, "NGHE THỬ / MỞ MP3", self.play_selected).pack(side="left")
        button(settings, "MỞ THƯ MỤC AUDIO", self.open_audio_folder).pack(side="left", padx=6)
        self.status = tk.StringVar(value="Sẵn sàng")
        tk.Label(settings, textvariable=self.status, bg=BG, fg=COPPER).pack(side="left", padx=8)

        self.source = None
        self.audio_dir = None
        self.pending = queue.Queue()
        self.running = False
        self.segment_roots = {}

    def drop_audio(self, data):
        paths = parse_drop_files(data)
        if paths and Path(paths[0].strip("{}")).suffix.lower() == ".txt":
            self.load_path(Path(paths[0].strip("{}")))

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt")])
        if path:
            self.load_path(Path(path))

    def load_path(self, path):
        try:
            text = read_text_file(path)
        except Exception as exc:
            messagebox.showerror("Lỗi đọc TXT", str(exc))
            return
        if not text.strip():
            messagebox.showwarning("File trống", "TXT không có nội dung.")
            return
        self.source = path
        self.content.delete("1.0", "end")
        self.content.insert("1.0", text)
        self.audio_dir = project_dir_for(path) / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.file_label.config(text=path.name)
        self.status.set("Đã nạp nội dung.")

    def check_api(self):
        url = self.api_url.get().strip().rstrip("/")
        key = self.api_key.get().strip()
        if not url or not key:
            messagebox.showwarning("Thiếu cấu hình", "Nhập API URL và API key trước.")
            return
        try:
            save_audio_api_settings(url, key)
        except Exception as exc:
            messagebox.showerror("Không lưu được", str(exc))
            return
        self.status.set("Đang kiểm tra Story TTS API...")
        def worker():
            try:
                client = StoryTTSClient(url, key)
                result = client.check_connection()
                voices = ", ".join(item.get("name", item.get("id", "")) for item in result.get("voices", []))
                self.after(0, lambda: self.status.set(f"Kết nối thành công · {voices}"))
            except Exception as exc:
                self.after(0, lambda e=str(exc): self.status.set(f"API chưa kết nối: {e}"))
        threading.Thread(target=worker, daemon=True).start()

    def generate(self):
        if self.running:
            messagebox.showinfo("Đang chạy", "Tác vụ gửi audio đang chạy.")
            return
        text = self.content.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo("Thiếu nội dung", "Hãy mở TXT hoặc kéo file vào khung trái.")
            return
        url = self.api_url.get().strip().rstrip("/")
        key = self.api_key.get().strip()
        if not url or not key:
            messagebox.showwarning("Thiếu kết nối", "Nhập API URL và API key, sau đó nhấn LƯU & KIỂM TRA.")
            return
        try:
            save_audio_api_settings(url, key)
        except Exception as exc:
            messagebox.showerror("Không lưu được cấu hình", str(exc))
            return
        if self.audio_dir is None:
            self.audio_dir = Path.cwd() / "data" / "audio"
            self.audio_dir.mkdir(parents=True, exist_ok=True)

        chapters = split_chapters(text)
        if not chapters:
            messagebox.showwarning("Không có nội dung", "Không tìm thấy nội dung audio.")
            return
        self.results.delete(*self.results.get_children())
        self.segments.delete(*self.segments.get_children())
        self.segment_roots = {}
        for index, (title, _body) in enumerate(chapters, 1):
            self.results.insert(
                "", "end", iid=str(index),
                values=(f"AU ({index}) · {title[:22]}", "Đang chờ", f"AU_{index:03d}.mp3")
            )
            root_id = f"au-{index}"
            self.segment_roots[index] = root_id
            self.segments.insert(
                "", "end", iid=root_id, text=f"AU ({index}) · {title[:32]}",
                values=("Chờ tách đoạn", "Đang chờ"), open=True
            )
        voice = TTS_VOICES[self.voice.get()]
        try:
            rate = float(self.rate.get().rstrip("x"))
        except ValueError:
            messagebox.showerror("Tốc độ không hợp lệ", "Hãy chọn lại tốc độ đọc.")
            return
        self.running = True
        self.status.set("Đang gửi nội dung sang Story TTS API...")
        threading.Thread(
            target=self.audio_worker,
            args=(chapters, voice, rate, url, key),
            daemon=True,
        ).start()
        self.after(300, self.poll_audio)

    def audio_worker(self, chapters, voice, rate, api_url, api_key):
        client = None
        successes = 0
        failures = []
        try:
            client = StoryTTSClient(api_url, api_key)
            for index, (title, body) in enumerate(chapters, 1):
                self.pending.put(("state", index, "Đang gửi API"))
                try:
                    chapter_id = f"{self.source.stem if self.source else 'story'}/AU-{index:04d}"
                    job = client.create_job(body, voice, rate, chapter_id)
                    job_id = int(job["job_id"])
                    self.pending.put(("job_id", index, job_id))
                    if job.get("status") != "completed":
                        def on_update(item, i=index):
                            completed = int(item.get("completed_chunks", 0))
                            total = int(item.get("chunk_count", 0))
                            percent = int(item.get("progress_percent", 0))
                            segments = item.get("segments", [])
                            self.pending.put((
                                "progress", i, item.get("status", "queued"),
                                completed, total, percent, segments
                            ))
                        job = client.wait_for_job(job_id, on_update=on_update, poll_seconds=3.0)
                    path = self.audio_dir / f"AU_{index:03d}.mp3"
                    client.download_audio(job, path)
                    successes += 1
                    self.pending.put(("done_one", index, str(path)))
                except Exception as exc:
                    failures.append(f"AU ({index}): {exc}")
                    self.pending.put(("failed_one", index, str(exc)))
            self.pending.put(("done", successes, len(chapters), failures))
        except Exception as exc:
            self.pending.put(("error", str(exc)))

    def refresh_segment_rows(self, au_index, job_state, segments):
        """Render each server-side segment under its AU, preserving source numbering."""
        root_id = self.segment_roots.get(au_index, f"au-{au_index}")
        if not self.segments.exists(root_id):
            self.segments.insert("", "end", iid=root_id, text=f"AU ({au_index})", open=True)
            self.segment_roots[au_index] = root_id

        state_names = {
            "queued": "Đang chờ", "generating": "Đang tạo",
            "completed": "Đã tạo xong", "failed": "Lỗi",
        }
        root_names = {
            "queued": "Đang chờ", "generating": "Đang tạo đoạn",
            "merging": "Đang ghép MP3", "completed": "Đã ghép MP3",
            "failed": "Thất bại",
        }
        current_values = list(self.segments.item(root_id, "values"))
        total = len(segments) or (current_values[0] if current_values else "Chờ tách đoạn")
        if isinstance(total, int):
            total = f"{total} đoạn"
        self.segments.item(root_id, values=(total, root_names.get(job_state, job_state)))

        for segment in sorted(segments, key=lambda part: int(part.get("index", 0))):
            number = int(segment.get("index", 0))
            if number < 1:
                continue
            iid = f"seg-{au_index}-{number}"
            label = segment.get("label") or f"Đoạn {number:03d}"
            char_count = int(segment.get("char_count", 0))
            status = state_names.get(segment.get("status", "queued"), segment.get("status", "queued"))
            if segment.get("error"):
                status = "Lỗi · " + str(segment["error"])[:70]
            values = (f"{char_count:,} ký tự", status)
            if self.segments.exists(iid):
                self.segments.item(iid, text=label, values=values)
            else:
                self.segments.insert(root_id, "end", iid=iid, text=label, values=values)
        self.segments.item(root_id, open=True)

    def poll_audio(self):
        try:
            while True:
                item = self.pending.get_nowait()
                kind = item[0]
                if kind == "state":
                    index, state = item[1], item[2]
                    values = list(self.results.item(str(index), "values"))
                    values[1] = state
                    self.results.item(str(index), values=values)
                    self.status.set(f"Đang xử lý AU ({index})...")
                elif kind == "job_id":
                    index, job_id = item[1], item[2]
                    values = list(self.results.item(str(index), "values"))
                    values[1] = f"Đã nhận job #{job_id}"
                    self.results.item(str(index), values=values)
                elif kind == "progress":
                    index, state, completed, total, percent, segments = item[1:]
                    values = list(self.results.item(str(index), "values"))
                    state_names = {
                        "queued": "Đang chờ", "generating": "Đang tạo đoạn",
                        "merging": "ĐANG GHÉP MP3", "completed": "Hoàn thành",
                        "failed": "Thất bại",
                    }
                    values[1] = f"{state_names.get(state, state)} · {completed}/{total} ({percent}%)"
                    self.results.item(str(index), values=values)
                    self.refresh_segment_rows(index, state, segments)
                    self.status.set(f"AU ({index}) · {completed}/{total} đoạn · {percent}%")
                elif kind == "done_one":
                    index, path = item[1], item[2]
                    values = list(self.results.item(str(index), "values"))
                    values[1] = "Hoàn thành · MP3 đã tải"
                    values[2] = Path(path).name
                    self.results.item(str(index), values=values)
                    self.refresh_segment_rows(index, "completed", [])
                elif kind == "failed_one":
                    index, error = item[1], item[2]
                    values = list(self.results.item(str(index), "values"))
                    values[1] = "Thất bại"
                    self.results.item(str(index), values=values)
                    self.refresh_segment_rows(index, "failed", [])
                    self.status.set(f"AU ({index}) thất bại")
                elif kind == "done":
                    successes, total, failures = item[1:]
                    self.running = False
                    if failures:
                        self.status.set(f"Hoàn tất {successes}/{total} AU · có {len(failures)} lỗi")
                        messagebox.showwarning(
                            "Audio hoàn tất một phần",
                            f"Đã tạo {successes}/{total} AU.\n\n" + "\n".join(failures[:8])
                        )
                    else:
                        self.status.set(f"Đã tạo xong {successes} AU.")
                        messagebox.showinfo("Hoàn thành", f"MP3 được tải về:\n{self.audio_dir}")
                elif kind == "error":
                    self.running = False
                    self.status.set("Có lỗi khi kết nối API")
                    messagebox.showerror("Story TTS API", item[1])
        except queue.Empty:
            pass
        if self.running:
            self.after(300, self.poll_audio)

    def play_selected(self):
        selection = self.results.selection()
        if not selection:
            messagebox.showinfo("Chọn AU", "Hãy chọn một AU trong danh sách.")
            return
        filename = self.results.item(selection[0], "values")[2]
        path = self.audio_dir / filename
        if not path.exists():
            messagebox.showwarning("Chưa có file", "AU này chưa tải hoàn tất.")
            return
        if os.name == "nt":
            os.startfile(path)
        else:
            webbrowser.open(path.as_uri())

    def open_audio_folder(self):
        if not self.audio_dir:
            messagebox.showinfo("Chưa có thư mục", "Hãy nạp TXT trước.")
            return
        if os.name == "nt":
            os.startfile(self.audio_dir)
        else:
            webbrowser.open(self.audio_dir.as_uri())
