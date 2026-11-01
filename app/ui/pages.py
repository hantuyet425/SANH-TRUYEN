from pathlib import Path
import os
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from app.config import DOWNLOAD_DIR, PROJECTS_DIR, WEBTOEPUB_URL, TTS_VOICES, TTS_RATES, HACHIMI_MODELS, project_dir_for
from app.utils import read_text_file, split_text, parse_drop_files
from app.services.browser_service import open_chrome
from app.services.epub_service import convert_epub_to_txt
from app.services.hachimi_service import HachimiTranslator
from app.services.tts_service import split_chapters
from app.services.chapter_numbering import renumber_chapters, count_chapters
from app.services.audio_github_client import AudioGitHubClient, AudioGitHubError, generate_shared_key, load_audio_credentials, save_audio_credentials
from app.ui.widgets import heading, eyebrow, panel, button, text_box, field_label, try_enable_drop, BG, PANEL, PANEL_2, COPPER, RED, TEXT, MUTED, LINE, INPUT


class BasePage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app


class DashboardPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        eyebrow(self, "The Occult Library").pack(anchor="w", pady=(0, 8))
        heading(self, "Chào mừng đến SẢNH TRUYỆN", "Không gian thu thập, biên tập và lưu giữ những câu chuyện của bạn.")

        hero = tk.Frame(self, bg="#150B0C", padx=22, pady=18, highlightthickness=1, highlightbackground="#6B202B")
        hero.pack(fill="x", pady=(2, 16))
        hero.grid_columnconfigure(0, weight=1)
        tk.Label(hero, text="✧   THƯ VIỆN ĐÊM TỐI   ✧", bg="#150B0C", fg=COPPER,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(hero, text="Nơi những câu chuyện được đánh thức.", bg="#150B0C", fg=TEXT,
                 font=("Segoe UI", 21, "bold")).grid(row=1, column=0, sticky="w", pady=(10, 4))
        tk.Label(hero, text="Từ văn bản nguồn đến bản dịch và audiobook — trong một workspace gọn nhẹ.",
                 bg="#150B0C", fg="#C4A18A", font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w")
        actions = tk.Frame(hero, bg="#150B0C")
        actions.grid(row=3, column=0, sticky="w", pady=(14, 0))
        button(actions, "TIẾP TỤC LÀM VIỆC", lambda: app.show_page("translate"), accent=True).pack(side="left", padx=(0, 8))
        button(actions, "MỞ THƯ MỤC DỮ LIỆU", lambda: self.open_data()).pack(side="left")

        sigil = tk.Canvas(hero, width=104, height=104, bg="#150B0C", highlightthickness=0)
        sigil.grid(row=0, column=1, rowspan=4, padx=(20, 6))
        for inset, color, width in [(5, COPPER, 1), (15, "#6F302A", 1), (25, RED, 2), (34, COPPER, 1)]:
            sigil.create_oval(inset, inset, 104-inset, 104-inset, outline=color, width=width)
        sigil.create_polygon(52, 24, 80, 52, 52, 80, 24, 52, outline=RED, fill="", width=2)
        sigil.create_polygon(52, 34, 70, 52, 52, 70, 34, 52, outline=COPPER, fill="", width=1)
        sigil.create_oval(47, 47, 57, 57, fill=RED, outline=RED)
        sigil.create_line(52, 2, 52, 18, fill=COPPER)
        sigil.create_line(52, 86, 52, 102, fill=COPPER)

        cards = tk.Frame(self, bg=BG)
        cards.pack(fill="x")
        for col in range(3):
            cards.grid_columnconfigure(col, weight=1, uniform="dashboard")
        items = [
            ("01 / COLLECT", "⇩", "CÀO TRUYỆN", "Thu thập EPUB và chuyển thành TXT.", "MỞ CÔNG CỤ", "crawl", COPPER),
            ("02 / TRANSLATE", "文", "DỊCH TRUYỆN", "Dịch raw Trung hoặc viết lại bản convert.", "MỞ BẢN DỊCH", "translate", RED),
            ("03 / LISTEN", "♫", "TẠO AUDIO", "Tạo MP3 dài với giọng đọc đã chọn.", "MỞ PHÒNG THU", "audio", COPPER),
        ]
        for index, (overline, symbol, title, detail, action, page, color) in enumerate(items):
            card = tk.Frame(cards, bg="#15100F", padx=15, pady=14, highlightthickness=1,
                            highlightbackground=RED if index == 1 else LINE)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 8, 0 if index == 2 else 0))
            tk.Label(card, text=overline, bg="#15100F", fg=COPPER, font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(card, text=symbol, bg="#15100F", fg=color, font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(9, 5))
            tk.Label(card, text=title, bg="#15100F", fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
            tk.Label(card, text=detail, bg="#15100F", fg=MUTED, font=("Segoe UI", 9), wraplength=245,
                     justify="left").pack(anchor="w", pady=(6, 12))
            button(card, action, lambda p=page: app.show_page(p), accent=(index == 1)).pack(anchor="w")

    def open_data(self):
        path = PROJECTS_DIR
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)
        else:
            webbrowser.open(path.as_uri())


class CrawlPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        eyebrow(self, "01 / Collect").pack(anchor="w", pady=(0, 8))
        heading(self, "Cào truyện", "Thu thập sách điện tử và chuyển đổi thành văn bản để chuẩn bị dịch.")

        columns = tk.Frame(self, bg=BG)
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=1, uniform="crawl")
        columns.grid_columnconfigure(1, weight=1, uniform="crawl")
        columns.grid_rowconfigure(0, weight=1)

        left = panel(columns)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(left, text="THU THẬP NGUỒN TRUYỆN", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(left, text="Mở Chrome thật và dùng tiện ích WebToEpub để lưu truyện thành EPUB.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9), wraplength=440, justify="left").pack(anchor="w", pady=(5, 12))
        for number, title, detail in [
            ("01", "MỞ TRÌNH DUYỆT", "Mở Chrome và truy cập trang truyện."),
            ("02", "THU THẬP", "Dùng WebToEpub để xuất thành EPUB."),
            ("03", "LƯU NGUỒN", "Giữ file EPUB trong kho cục bộ."),
        ]:
            row = tk.Frame(left, bg="#1D1412", padx=12, pady=10, highlightthickness=1, highlightbackground="#33201B")
            row.pack(fill="x", pady=3)
            tk.Label(row, text=number, bg="#1D1412", fg=RED, font=("Segoe UI", 12, "bold"), width=4).pack(side="left")
            detail_box = tk.Frame(row, bg="#1D1412")
            detail_box.pack(side="left", fill="x", expand=True)
            tk.Label(detail_box, text=title, bg="#1D1412", fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(detail_box, text=detail, bg="#1D1412", fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))
        buttons = tk.Frame(left, bg=PANEL)
        buttons.pack(fill="x", pady=(13, 0))
        button(buttons, "MỞ CHROME / WEBTOEPUB", self.launch_chrome, accent=True).pack(side="left", padx=(0, 8))
        button(buttons, "MỞ THƯ MỤC EPUB", lambda: self.open_folder(DOWNLOAD_DIR)).pack(side="left")

        right = panel(columns)
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Label(right, text="CHUYỂN ĐỔI TÀI LIỆU → TXT", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(right, text="Trích xuất nội dung từ các định dạng tài liệu phổ biến để dùng trong mục Dịch truyện.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9), wraplength=440, justify="left").pack(anchor="w", pady=(5, 12))
        filebox = tk.Frame(right, bg=INPUT, padx=12, pady=12, highlightthickness=1, highlightbackground=LINE)
        filebox.pack(fill="x")
        tk.Label(filebox, text="TÀI LIỆU → TXT", bg=INPUT, fg=COPPER, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(filebox, text="EPUB · TXT/MD · HTML · DOCX/ODT · RTF · FB2 · PDF văn bản",
                 bg=INPUT, fg=TEXT, font=("Segoe UI", 8)).pack(anchor="w", pady=(7, 10))
        self.selected_file = tk.StringVar(value="Chưa chọn tài liệu")
        tk.Label(filebox, textvariable=self.selected_file, bg=INPUT, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        actions = tk.Frame(right, bg=PANEL)
        actions.pack(fill="x", pady=(14, 8))
        button(actions, "CHỌN TÀI LIỆU & CHUYỂN TXT", self.choose_epub, accent=True).pack(side="left", padx=(0, 8))
        button(actions, "MỞ RAW TXT", self.open_raw_txt).pack(side="left")
        tk.Label(right, text="File gốc không bị xóa. EPUB được trích xuất thành TXT trong kho dự án.\nPDF scan cần OCR riêng; bản MVP không tự OCR.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=(4, 0))

        log = panel(self, "Nhật ký xử lý")
        log.pack(fill="x", pady=(12, 0))
        tk.Label(log, text="Thông báo khi mở công cụ hoặc chuyển đổi tài liệu sẽ xuất hiện tại đây.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        self.note = tk.StringVar(value="Sẵn sàng")
        tk.Label(log, textvariable=self.note, bg=PANEL, fg=COPPER, font=("Segoe UI", 8)).pack(anchor="w", pady=(6, 0))

    def launch_chrome(self):
        ok, msg = open_chrome()
        self.note.set(msg)
        self.app.set_status(msg)
        if not ok:
            messagebox.showwarning("Chrome", msg)
        else:
            webbrowser.open(WEBTOEPUB_URL)

    def choose_epub(self):
        p = filedialog.askopenfilename(filetypes=[
            ("Tài liệu hỗ trợ", "*.epub *.txt *.html *.htm *.md *.docx *.odt *.rtf *.fb2 *.pdf"),
            ("EPUB", "*.epub"), ("Text", "*.txt"), ("Tất cả tệp", "*.*")
        ])
        if not p:
            return
        source = Path(p)
        self.selected_file.set(source.name)
        if source.suffix.lower() == ".epub":
            self.convert_path(source)
        elif source.suffix.lower() == ".txt":
            self.open_raw_path(source)
        else:
            messagebox.showinfo("Định dạng chưa hỗ trợ", "Bản hiện tại chỉ chuyển EPUB sang TXT trực tiếp. Các định dạng khác cần bộ chuyển đổi tương ứng.")

    def convert_path(self, source: Path):
        self.note.set(f"Đang chuyển {source.name}...")
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
        self.note.set(f"Đã tạo {path.name}")
        self.app.set_status("Chuyển EPUB → TXT hoàn tất")
        if messagebox.askyesno("Hoàn tất", f"Đã lưu:\n{path}\n\nMở trong mục Dịch truyện?"):
            self.open_raw_path(path)

    def open_raw_txt(self):
        p = filedialog.askopenfilename(filetypes=[("Text", "*.txt")])
        if p:
            self.open_raw_path(Path(p))

    def open_raw_path(self, path: Path):
        page = self.app.pages.get("translate")
        if page:
            page.load_path(path)
            self.app.show_page("translate")

    @staticmethod
    def open_folder(path):
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)
        else:
            webbrowser.open(path.as_uri())


class TranslatePage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        eyebrow(self, "02 / Translate").pack(anchor="w", pady=(0, 8))
        heading(self, "Phòng biên dịch", "Dịch raw tiếng Trung hoặc viết lại bản convert, giữ nguyên quy trình xử lý hiện có.")

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", pady=(0, 9))
        button(bar, "NẠP FILE RAW TXT", self.load_file, accent=True).pack(side="left", padx=(0, 7))
        button(bar, "MỞ BẢN DỊCH ĐÃ LƯU", self.open_saved).pack(side="left", padx=(0, 7))
        button(bar, "KẾT NỐI CHATGPT", self.connect_chatgpt).pack(side="left", padx=(0, 7))
        button(bar, "NGẮT KẾT NỐI", self.disconnect_chatgpt).pack(side="left")

        meta = tk.Frame(self, bg=PANEL, padx=11, pady=8, highlightthickness=1, highlightbackground=LINE)
        meta.pack(fill="x", pady=(0, 7))
        field_label(meta, "Từ điển").pack(side="left")
        self.dictionary = tk.StringVar(value="Mặc định")
        ttk.Combobox(meta, textvariable=self.dictionary, values=["Mặc định"], state="readonly", width=17).pack(side="left", padx=(7, 16))
        field_label(meta, "Tên truyện").pack(side="left")
        self.story_name = tk.StringVar(value="Chưa nạp truyện")
        ttk.Entry(meta, textvariable=self.story_name, width=32).pack(side="left", padx=7)
        self.saved_note = tk.Label(meta, text="Bản nháp tự lưu trên máy", bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
        self.saved_note.pack(side="right")

        engine = tk.Frame(self, bg=PANEL, padx=11, pady=8, highlightthickness=1, highlightbackground=LINE)
        engine.pack(fill="x", pady=(0, 8))
        field_label(engine, "Bộ máy dịch").pack(side="left")
        self.engine_choice = tk.StringVar(value="ChatGPT · Qua clipboard")
        ttk.Combobox(
            engine, textvariable=self.engine_choice,
            values=["ChatGPT · Qua clipboard", "HachimiMT-60 · Cục bộ"],
            state="readonly", width=25
        ).pack(side="left", padx=(8, 10))
        tk.Label(engine, text="Hachimi chạy CPU cục bộ · ChatGPT thao tác qua clipboard.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")
        self.model = tk.StringVar(value=list(HACHIMI_MODELS)[0])
        ttk.Combobox(engine, textvariable=self.model, values=list(HACHIMI_MODELS),
                     state="readonly", width=26).pack(side="right")
        self.mode_row = tk.Frame(self, bg=BG)
        self.mode_row.pack(fill="x", pady=(0, 8))
        field_label(self.mode_row, "Chế độ").pack(side="left", padx=(0, 10))
        self.translation_mode = tk.StringVar(value="raw")
        tk.Radiobutton(
            self.mode_row, text="Dịch raw Trung", variable=self.translation_mode, value="raw",
            bg=BG, fg=TEXT, selectcolor=PANEL_2, activebackground=BG, activeforeground=TEXT,
            font=("Segoe UI", 9)
        ).pack(side="left", padx=(0, 12))
        tk.Radiobutton(
            self.mode_row, text="Viết lại convert", variable=self.translation_mode, value="convert",
            bg=BG, fg=TEXT, selectcolor=PANEL_2, activebackground=BG, activeforeground=TEXT,
            font=("Segoe UI", 9)
        ).pack(side="left")

        panes = tk.Frame(self, bg=BG)
        panes.pack(fill="both", expand=True)
        panes.grid_columnconfigure(0, weight=1)
        panes.grid_columnconfigure(1, weight=1)
        panes.grid_rowconfigure(0, weight=1)
        left = panel(panes)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(left, text="01 / VĂN BẢN NGUỒN", bg=PANEL, fg=COPPER, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 7))
        self.raw_frame, self.raw_box = text_box(left, 18)
        self.raw_frame.pack(fill="both", expand=True)
        right = panel(panes)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(right, text="02 / BẢN DỊCH TIẾNG VIỆT", bg=PANEL, fg=COPPER, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        tk.Label(right, text="Kết quả sẽ xuất hiện ở đây; có thể chỉnh sửa trước khi lưu.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 7))
        self.vi_frame, self.vi_box = text_box(right, 18)
        self.vi_frame.pack(fill="both", expand=True)
        try_enable_drop(self.raw_box, self.drop_raw)

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", pady=(8, 0))
        self.counter = tk.StringVar(value="Chưa có nội dung")
        tk.Label(footer, textvariable=self.counter, bg=BG, fg=COPPER, font=("Segoe UI", 8)).pack(side="left")
        self.numbering_note = tk.StringVar(value="Số chương xuyên suốt toàn bộ RAW")
        tk.Label(footer, textvariable=self.numbering_note, bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))
        self.status = tk.StringVar(value="Sẵn sàng")
        tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=(12, 0))
        button(footer, "LƯU BẢN DỊCH", self.save_translation).pack(side="right", padx=(7, 0))
        button(footer, "NHẬN CLIPBOARD", self.paste_clipboard).pack(side="right", padx=(7, 0))
        button(footer, "BẮT ĐẦU DỊCH", self.run_selected_engine, accent=True).pack(side="right", padx=(7, 0))
        button(footer, "ĐOẠN TIẾP →", self.next_chunk).pack(side="right", padx=(7, 0))
        button(footer, "← ĐOẠN TRƯỚC", self.prev_chunk).pack(side="right")

        self.source = None
        self.chunks = []
        self.translations = []
        self.index = 0
        self.original_raw = ""
        self.numbered_raw = ""
        self.chapter_report = {}
        self.chatgpt_connected = False

    def open_saved(self):
        p = filedialog.askopenfilename(
            filetypes=[("Bản dịch", "*.txt"), ("Tất cả tệp", "*.*")],
            initialdir=str(PROJECTS_DIR)
        )
        if not p:
            return
        try:
            text = read_text_file(p)
            self.vi_box.delete("1.0", "end")
            self.vi_box.insert("1.0", text)
            self.status.set("Đã mở bản dịch đã lưu.")
        except Exception as exc:
            messagebox.showerror("Lỗi mở bản dịch", str(exc))

    def connect_chatgpt(self):
        self.chatgpt_connected = True
        webbrowser.open("https://chatgpt.com/")
        self.status.set("Đã mở ChatGPT. Sao chép prompt, gửi thủ công rồi nhận phản hồi qua clipboard.")

    def disconnect_chatgpt(self):
        self.chatgpt_connected = False
        self.status.set("Đã ngắt trạng thái kết nối ChatGPT.")

    def run_selected_engine(self):
        if self.engine_choice.get().startswith("Hachimi"):
            self.translate_local()
        else:
            self.copy_prompt()

    def drop_raw(self, data):
        paths = parse_drop_files(data)
        if paths and Path(paths[0].strip("{}")).suffix.lower() == ".txt":
            self.load_path(Path(paths[0].strip("{}")))

    def load_file(self):
        p = filedialog.askopenfilename(filetypes=[("Text", "*.txt")])
        if p: self.load_path(Path(p))

    def load_path(self, path):
        try:
            raw = read_text_file(path)
        except Exception as exc:
            messagebox.showerror("Lỗi đọc file", str(exc))
            return

        # Keep the user's RAW file untouched. Work on an in-memory copy whose
        # chapter headings continue globally across volume boundaries.
        self.original_raw = raw
        self.numbered_raw, self.chapter_report = renumber_chapters(raw)
        self.source = path
        self.chunks = split_text(self.numbered_raw, 3400)
        self.translations = [""] * len(self.chunks)
        self.index = 0

        chapter_count = self.chapter_report["chapter_count"]
        reset_count = self.chapter_report["reset_count"]
        if chapter_count:
            self.numbering_note.set(
                f"{chapter_count} chương · đã nối {reset_count} lần đặt lại số"
            )
            status = (
                f"Đã nạp {len(self.chunks)} đoạn · {chapter_count} chương"
                + (f" · nối {reset_count} lần reset" if reset_count else " · số chương đã liên tục")
            )
        else:
            self.numbering_note.set("Chưa nhận diện được tiêu đề chương")
            status = f"Đã nạp {len(self.chunks)} đoạn · giữ nguyên vì không nhận diện được chương"

        self.show_chunk()
        self.app.set_status(status)

    def capture(self):
        if not self.chunks:
            return

        current_text = self.vi_box.get("1.0", "end-1c").strip()
        # Derive the global starting chapter number from the RAW source, not
        # from completed translations. This also works when earlier chunks
        # have not been translated yet.
        preceding_source = "\n\n".join(self.chunks[:self.index])
        start_number = count_chapters(preceding_source) + 1
        normalized, _report = renumber_chapters(
            current_text,
            start_number=start_number,
        )
        self.translations[self.index] = normalized

        if normalized != current_text:
            self.vi_box.delete("1.0", "end")
            self.vi_box.insert("1.0", normalized)

    def show_chunk(self):
        self.raw_box.delete("1.0", "end"); self.vi_box.delete("1.0", "end")
        if not self.chunks: self.counter.set("Chưa có nội dung"); return
        self.raw_box.insert("1.0", self.chunks[self.index])
        self.vi_box.insert("1.0", self.translations[self.index])
        chapter_count = count_chapters(self.chunks[self.index])
        suffix = f" · {chapter_count} tiêu đề chương" if chapter_count else ""
        self.counter.set(f"ĐOẠN {self.index + 1}/{len(self.chunks)}{suffix}")

    def prev_chunk(self):
        if self.index > 0:
            self.capture(); self.save_partial(); self.index -= 1; self.show_chunk()

    def next_chunk(self):
        if self.index + 1 < len(self.chunks):
            self.capture(); self.save_partial(); self.index += 1; self.show_chunk()

    def prompt(self):
        self.capture()
        name = self.story_name.get().strip() or (self.source.stem if self.source else "Tiểu thuyết")
        if self.translation_mode.get() == "convert":
            instruction = (
                "Biên tập và viết lại bản convert tiếng Việt thành văn xuôi tiểu thuyết tự nhiên, "
                "mạch lạc, trau chuốt; bỏ lối dịch máy cứng nhắc nhưng tuyệt đối không thêm, bớt "
                "tình tiết, thông tin, cảm xúc hoặc diễn biến. Giữ nguyên tên riêng, thuật ngữ, "
                "xưng hô và quan hệ nhân vật."
            )
        else:
            instruction = (
                "Dịch tiểu thuyết tiếng Trung sang tiếng Việt tự nhiên, mạch lạc và trau chuốt; "
                "không bám máy móc trật tự câu tiếng Trung. Giữ nguyên tên riêng, thuật ngữ, "
                "xưng hô và quan hệ nhân vật; không thêm hoặc lược tình tiết."
            )
        return (instruction + " "
                "Giữ nguyên mọi tiêu đề chương và số chương đã được chuẩn hóa xuyên suốt toàn bộ truyện. "
                "Khi gặp tiêu đề quyển/tập mới, tuyệt đối không đánh số chương quay lại từ 1. "
                "Không tự ý đổi, xóa, gộp hoặc tạo thêm tiêu đề chương. "
                "Chỉ trả nội dung đã xử lý, không giải thích.\n"
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


class AudioConnectionDialog(tk.Toplevel):
    def __init__(self, parent, on_saved):
        super().__init__(parent)
        self.title("Kết nối GitHub Audio")
        self.configure(bg=BG)
        self.geometry("720x560")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_saved = on_saved
        self.busy = False

        tk.Label(
            self, text="KẾT NỐI PHÒNG THU GITHUB",
            bg=BG, fg=COPPER, font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=24, pady=(22, 5))
        tk.Label(
            self,
            text="Token và khóa mã hóa chỉ được lưu trong Windows Credential Manager trên máy này.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=660, justify="left"
        ).pack(anchor="w", padx=24, pady=(0, 16))

        body = tk.Frame(self, bg=PANEL, padx=18, pady=16, highlightthickness=1, highlightbackground=LINE)
        body.pack(fill="x", padx=22)
        tk.Label(body, text="1. GITHUB PERSONAL ACCESS TOKEN", bg=PANEL, fg=COPPER,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.token_var = tk.StringVar()
        try:
            saved_token, saved_key = load_audio_credentials()
        except AudioGitHubError as exc:
            saved_token, saved_key = "", ""
            self.initial_error = str(exc)
        else:
            self.initial_error = ""
        self.token_var.set(saved_token or "")
        token_entry = tk.Entry(
            body, textvariable=self.token_var, show="*", bg=INPUT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10)
        )
        token_entry.pack(fill="x", pady=(6, 6), ipady=7)
        token_row = tk.Frame(body, bg=PANEL)
        token_row.pack(fill="x")
        button(token_row, "MỞ TRANG TẠO TOKEN", self.open_token_page).pack(side="left")
        tk.Label(
            token_row, text="Chọn riêng repo SANH-TRUYEN-AUDIO.",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 8)
        ).pack(side="left", padx=10)

        tk.Frame(body, bg=LINE, height=1).pack(fill="x", pady=14)
        tk.Label(body, text="2. KHÓA AES-256-GCM DÙNG CHUNG", bg=PANEL, fg=COPPER,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.key_var = tk.StringVar(value=saved_key or "")
        key_entry = tk.Entry(
            body, textvariable=self.key_var, show="*", bg=INPUT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10)
        )
        key_entry.pack(fill="x", pady=(6, 7), ipady=7)
        key_row = tk.Frame(body, bg=PANEL)
        key_row.pack(fill="x")
        button(key_row, "TẠO KHÓA MỚI", self.make_key).pack(side="left")
        button(key_row, "SAO CHÉP KHÓA", self.copy_key).pack(side="left", padx=7)
        tk.Label(
            body,
            text="Đưa đúng khóa này vào GitHub → Settings → Secrets and variables → Actions "
                 "với tên AUDIO_SHARED_KEY. Nếu tạo khóa mới, phải thay Secret trên GitHub bằng khóa mới.",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 8), wraplength=630, justify="left"
        ).pack(anchor="w", pady=(9, 0))

        permissions = tk.Frame(self, bg="#1D1412", padx=14, pady=12, highlightthickness=1, highlightbackground=LINE)
        permissions.pack(fill="x", padx=22, pady=12)
        tk.Label(
            permissions, text="QUYỀN TOKEN BẮT BUỘC",
            bg="#1D1412", fg=COPPER, font=("Segoe UI", 8, "bold")
        ).pack(anchor="w")
        tk.Label(
            permissions,
            text="Fine-grained PAT · Repository access: Only select repositories → SANH-TRUYEN-AUDIO\n"
                 "Contents: Read and write  ·  Actions: Read and write",
            bg="#1D1412", fg=TEXT, font=("Segoe UI", 9), justify="left"
        ).pack(anchor="w", pady=(5, 0))

        self.status_var = tk.StringVar(value=self.initial_error or "Chưa kiểm tra kết nối.")
        tk.Label(
            self, textvariable=self.status_var, bg=BG, fg=MUTED,
            font=("Segoe UI", 8), wraplength=660, justify="left"
        ).pack(anchor="w", padx=24, pady=(0, 8))
        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=22, pady=(0, 18))
        self.save_button = button(footer, "KIỂM TRA & LƯU AN TOÀN", self.test_and_save, accent=True)
        self.save_button.pack(side="right")
        button(footer, "ĐÓNG", self.destroy).pack(side="right", padx=8)

    def open_token_page(self):
        webbrowser.open("https://github.com/settings/personal-access-tokens/new")

    def make_key(self):
        self.key_var.set(generate_shared_key())
        self.status_var.set(
            "Đã tạo khóa mới. Sao chép khóa và cập nhật GitHub Secret AUDIO_SHARED_KEY trước khi chạy Audio."
        )

    def copy_key(self):
        value = self.key_var.get().strip()
        if not value:
            messagebox.showwarning("Chưa có khóa", "Hãy tạo hoặc nhập khóa trước.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()
        self.status_var.set("Đã sao chép khóa. Hãy dán vào GitHub Secret AUDIO_SHARED_KEY.")

    def test_and_save(self):
        if self.busy:
            return
        token = self.token_var.get().strip()
        key = self.key_var.get().strip()
        if not token or not key:
            messagebox.showwarning("Thiếu thông tin", "Cần nhập GitHub token và khóa AES.", parent=self)
            return
        self.busy = True
        self.save_button.configure(state="disabled")
        self.status_var.set("Đang kiểm tra quyền đọc repo/workflow và lưu vào Windows Credential Manager...")

        def work():
            try:
                client = AudioGitHubClient(token, key)
                client.test_connection()
                save_audio_credentials(token, key)
                self.after(0, self.saved)
            except Exception as exc:
                self.after(0, lambda error=str(exc): self.failed(error))

        threading.Thread(target=work, daemon=True).start()

    def saved(self):
        self.busy = False
        self.on_saved()
        messagebox.showinfo(
            "Đã lưu kết nối",
            "Đã kiểm tra repo và workflow, thông tin đã được lưu trong Windows Credential Manager.\n\n"
            "Lưu ý: GitHub không cho ứng dụng đọc lại Actions Secret. Hãy chắc chắn Secret AUDIO_SHARED_KEY "
            "trên repo khớp chính xác với khóa vừa lưu.",
            parent=self
        )
        self.destroy()

    def failed(self, error):
        self.busy = False
        self.save_button.configure(state="normal")
        self.status_var.set(error)
        messagebox.showerror("Không kết nối được", error, parent=self)


class AudioPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        eyebrow(self, "03 / Listen").pack(anchor="w", pady=(0, 8))
        heading(self, "Phòng thu audio", "Biến bản truyện thành MP3 dài với giọng đọc và tốc độ bạn lựa chọn.")

        columns = tk.Frame(self, bg=BG)
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=6)
        columns.grid_columnconfigure(1, weight=4)
        columns.grid_rowconfigure(0, weight=1)

        left = panel(columns)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(left, text="NỘI DUNG AUDIO", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(left, text="Dán toàn bộ nội dung hoặc mở một file TXT đã dịch.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 10))
        file_row = tk.Frame(left, bg=PANEL)
        file_row.pack(fill="x", pady=(0, 8))
        button(file_row, "MỞ FILE TXT", self.load_file, accent=True).pack(side="left")
        self.file_label = tk.Label(file_row, text="Chưa chọn file", bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
        self.file_label.pack(side="left", padx=12)
        self.content_frame, self.content = text_box(left, 16)
        self.content_frame.pack(fill="both", expand=True)
        try_enable_drop(self.content, self.drop_audio)

        controls = tk.Frame(left, bg="#1D1412", padx=10, pady=9, highlightthickness=1, highlightbackground=LINE)
        controls.pack(fill="x", pady=(10, 8))
        field_label(controls, "Giọng đọc", bg="#1D1412").pack(side="left")
        self.voice = tk.StringVar(value="Nam Minh")
        ttk.Combobox(controls, textvariable=self.voice,
                     values=["Nam Minh", "Hoài My"], state="readonly", width=16).pack(side="left", padx=(7, 18))
        field_label(controls, "Tốc độ", bg="#1D1412").pack(side="left")
        self.rate = tk.StringVar(value="1.25")
        ttk.Combobox(controls, textvariable=self.rate,
                     values=["0.75", "1.0", "1.25", "1.5", "2.0"], state="readonly", width=9).pack(side="left", padx=7)
        actions = tk.Frame(left, bg=PANEL)
        actions.pack(fill="x", pady=(2, 0))
        self.start_button = button(actions, "TẠO AUDIO", self.start_actions_job, accent=True)
        self.start_button.pack(side="left")
        button(actions, "CẤU HÌNH GITHUB", self.configure_connection).pack(side="left", padx=8)
        tk.Label(actions, text="Xử lý trên GitHub Actions · MP3 giải mã tại máy",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=4)

        right = panel(columns)
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Label(right, text="KẾT QUẢ AUDIO", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(right, text="Theo dõi tiến trình và mở các file MP3 đã tạo.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 10))
        self.connection_status = tk.StringVar(value="Đang kiểm tra cấu hình...")
        tk.Label(right, textvariable=self.connection_status, bg=PANEL, fg=COPPER,
                 font=("Segoe UI", 8), wraplength=300, justify="left").pack(anchor="w", pady=(0, 10))
        button(right, "QUẢN LÝ KẾT NỐI", self.configure_connection).pack(anchor="w", pady=(0, 10))
        tk.Label(right, text="LỊCH SỬ AUDIO", bg=PANEL, fg=COPPER,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 6))
        list_frame = tk.Frame(right, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
        list_frame.pack(fill="both", expand=True)
        self.history = tk.Listbox(
            list_frame, bg=INPUT, fg=TEXT, selectbackground="#5B1A25",
            relief="flat", bd=0, font=("Segoe UI", 9), activestyle="none",
            selectmode="browse", height=12
        )
        self.history.pack(fill="both", expand=True, padx=5, pady=5)
        self.history.bind("<<ListboxSelect>>", self.on_history_select)

        self.job_panel = tk.Frame(right, bg="#1D1412", padx=12, pady=12,
                                  highlightthickness=1, highlightbackground=LINE)
        self.job_panel.pack(fill="x", pady=(9, 9))
        self.job_status = tk.StringVar(value="Chưa có tác vụ")
        tk.Label(self.job_panel, text="◌", bg="#1D1412", fg=COPPER,
                 font=("Segoe UI", 22)).pack(side="left", padx=(0, 12))
        status_box = tk.Frame(self.job_panel, bg="#1D1412")
        status_box.pack(side="left", fill="x", expand=True)
        tk.Label(status_box, text="GITHUB ACTIONS", bg="#1D1412", fg=COPPER,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(status_box, textvariable=self.job_status, bg="#1D1412", fg=TEXT,
                 font=("Segoe UI", 9), wraplength=220, justify="left").pack(anchor="w", pady=(4, 0))
        self.job_detail = tk.StringVar(value="MP3 sẽ được tải về và giải mã trực tiếp trên máy này.")
        tk.Label(right, textvariable=self.job_detail, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8), wraplength=300, justify="left").pack(anchor="w", pady=(0, 10))
        result_buttons = tk.Frame(right, bg=PANEL)
        result_buttons.pack(fill="x")
        button(result_buttons, "NGHE / MỞ FILE", self.play_selected, accent=True).pack(side="left", padx=(0, 8))
        button(result_buttons, "MỞ THƯ MỤC", self.open_audio_folder).pack(side="left")

        self.source = None
        self.audio_dir = None
        self.history_paths = []
        self.busy = False
        self._update_connection_status()
        self._refresh_history()

    def _update_connection_status(self):
        try:
            token, key = load_audio_credentials()
            configured = bool(token and key)
        except AudioGitHubError:
            configured = False
        self.connection_status.set(
            "● GitHub Audio đã lưu thông tin kết nối" if configured
            else "○ Chưa cấu hình GitHub token và khóa mã hóa"
        )

    def configure_connection(self):
        AudioConnectionDialog(self, self._update_connection_status)

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
        self.job_status.set("Đã nạp nội dung · sẵn sàng tạo audio")
        self.job_detail.set("Văn bản chỉ được gửi đi sau khi mã hóa AES-256-GCM.")
        self._refresh_history()
        self.app.set_status(f"Đã nạp {path.name}")

    def _refresh_history(self):
        if not hasattr(self, "history"):
            return
        files = []
        if self.audio_dir and self.audio_dir.exists():
            files = sorted(
                self.audio_dir.rglob("*.mp3"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        self.history_paths = files
        self.history.delete(0, "end")
        if not files:
            self.history.insert("end", "Chưa có tác vụ audio")
        else:
            for path in files:
                self.history.insert("end", f"{path.parent.name} · {path.name}")

    def start_actions_job(self):
        if self.busy:
            return
        source_text = self.content.get("1.0", "end-1c").strip()
        if not source_text:
            messagebox.showinfo("Chưa có nội dung", "Hãy mở TXT hoặc dán nội dung trước.")
            return
        try:
            token, shared_key = load_audio_credentials()
        except AudioGitHubError as exc:
            messagebox.showerror("Lỗi Credential Manager", str(exc))
            return
        if not token or not shared_key:
            messagebox.showinfo(
                "Chưa cấu hình GitHub",
                "Hãy chọn CẤU HÌNH GITHUB, nhập Fine-grained PAT và khóa AES trước khi tạo audio."
            )
            self.configure_connection()
            return

        if self.audio_dir is None:
            self.audio_dir = PROJECTS_DIR / "Audio-moi" / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        voice_name = self.voice.get().strip()
        rate = float(self.rate.get())
        self.busy = True
        self.start_button.configure(state="disabled")
        self.job_status.set("Đang chuẩn bị tác vụ...")
        self.job_detail.set("Đang mã hóa nội dung; chưa tải văn bản rõ lên GitHub.")
        self.app.set_status("Đang gửi tác vụ audio lên GitHub Actions...")

        def report(status):
            try:
                self.after(0, lambda value=status: self._set_job_status(value))
            except tk.TclError:
                pass

        def work():
            try:
                client = AudioGitHubClient(token, shared_key)
                outputs = client.generate_audio(
                    source_text, voice_name, rate, self.audio_dir, progress=report
                )
                self.after(0, lambda paths=outputs: self._audio_job_done(paths))
            except Exception as exc:
                self.after(0, lambda error=str(exc): self._audio_job_failed(error))

        threading.Thread(target=work, daemon=True).start()

    def _set_job_status(self, status):
        self.job_status.set(status)
        self.app.set_status(status)

    def _audio_job_done(self, outputs):
        self.busy = False
        self.start_button.configure(state="normal")
        self.job_status.set("Hoàn tất · đã nhận MP3")
        self.job_detail.set(
            f"Đã tải {len(outputs)} file MP3 vào thư mục audio cục bộ. "
            "Bản tải từ GitHub đã được giải mã bằng khóa đang lưu trên máy."
        )
        self._refresh_history()
        self.app.set_status(f"Đã tạo xong {len(outputs)} file MP3.")
        messagebox.showinfo(
            "Tạo audio hoàn tất",
            f"Đã tạo {len(outputs)} file MP3.\nLưu tại:\n{self.audio_dir}"
        )

    def _audio_job_failed(self, error):
        self.busy = False
        self.start_button.configure(state="normal")
        self.job_status.set("Tác vụ thất bại")
        self.job_detail.set(error)
        self.app.set_status("Tác vụ audio thất bại.")
        messagebox.showerror("Không tạo được audio", error)

    def on_history_select(self, _event=None):
        return

    def play_selected(self):
        selection = self.history.curselection()
        if selection and selection[0] < len(self.history_paths):
            path = self.history_paths[selection[0]]
            if path.exists() and os.name == "nt":
                os.startfile(path)
            elif path.exists():
                webbrowser.open(path.as_uri())
            else:
                messagebox.showwarning("Chưa có file", "File MP3 này không còn tồn tại.")
        else:
            messagebox.showinfo("Chưa có MP3", "Chưa có tác vụ audio hoàn thành.")

    def open_audio_folder(self):
        if not self.audio_dir:
            messagebox.showinfo("Chưa có thư mục", "Hãy nạp TXT hoặc tạo audio trước.")
            return
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(self.audio_dir)
        else:
            webbrowser.open(self.audio_dir.as_uri())
