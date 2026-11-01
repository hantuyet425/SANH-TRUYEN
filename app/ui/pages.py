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
from app.services.tts_api_client import StoryTTSClient, StoryTTSAPIError, load_audio_api_settings, save_audio_api_settings
from app.ui.widgets import heading, panel, button, text_box, try_enable_drop, BG, PANEL, COPPER, TEXT, MUTED


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
