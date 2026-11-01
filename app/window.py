import tkinter as tk
from tkinter import ttk, messagebox

try:
    from tkinterdnd2 import TkinterDnD
    BaseWindow = TkinterDnD.Tk
except Exception:
    TkinterDnD = None
    BaseWindow = tk.Tk

from app.config import APP_NAME, PROJECTS_DIR, DOWNLOAD_DIR
from app.ui.pages import DashboardPage, CrawlPage, TranslatePage, AudioPage


class SảnhTruyệnApp(BaseWindow):
    BG = "#090707"
    SIDEBAR = "#100B0A"
    PANEL = "#17100F"
    PANEL_2 = "#201513"
    LINE = "#4A2920"
    COPPER = "#B97848"
    RED = "#D21F32"
    RED_DARK = "#5A1720"
    TEXT = "#E9DFD2"
    MUTED = "#A89A8C"

    NAV_ITEMS = [
        ("dashboard", "◉", "Tổng quan"),
        ("crawl", "⇩", "Cào truyện"),
        ("translate", "▤", "Dịch truyện"),
        ("audio", "♫", "Tạo audio"),
    ]

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(1280, max(960, screen_width - 40))
        height = min(700, max(560, screen_height - 110))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(960, 560)
        self.configure(bg=self.BG)
        self._configure_style()
        self.current_page = None
        self.pages = {}
        self.nav_buttons = {}
        self._build_shell()
        self.show_page("dashboard")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.BG, foreground=self.MUTED)
        style.configure("Panel.TLabel", background=self.PANEL, foreground=self.TEXT)
        style.configure("Heading.TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 23, "bold"))
        style.configure("Subheading.TLabel", background=self.BG, foreground=self.COPPER, font=("Segoe UI", 9))
        style.configure("TButton", background=self.PANEL_2, foreground=self.TEXT, padding=(12, 8), borderwidth=0)
        style.map("TButton", background=[("active", "#39241D")], foreground=[("disabled", "#776B62")])
        style.configure("Accent.TButton", background=self.RED, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"))
        style.map("Accent.TButton", background=[("active", "#EA3548")])
        style.configure("Treeview", background=self.PANEL, fieldbackground=self.PANEL, foreground=self.TEXT, rowheight=27, borderwidth=0)
        style.configure("Treeview.Heading", background=self.PANEL_2, foreground=self.COPPER, font=("Segoe UI", 9, "bold"))
        style.configure("TCombobox", fieldbackground=self.PANEL_2, background=self.PANEL_2, foreground=self.TEXT, arrowcolor=self.COPPER)
        style.map("TCombobox", fieldbackground=[("readonly", self.PANEL_2)], foreground=[("readonly", self.TEXT)])
        style.configure("Horizontal.TProgressbar", background=self.RED, troughcolor=self.PANEL_2)

    def _build_shell(self):
        header = tk.Frame(self, bg="#0D0909", height=58, highlightthickness=1, highlightbackground=self.LINE)
        header.pack(fill="x")
        header.pack_propagate(False)

        emblem = tk.Canvas(header, width=28, height=28, bg="#0D0909", highlightthickness=0)
        emblem.pack(side="left", padx=(20, 8), pady=14)
        emblem.create_oval(2, 2, 26, 26, outline=self.RED, width=1)
        emblem.create_oval(7, 7, 21, 21, outline=self.COPPER, width=1)
        emblem.create_oval(11, 11, 17, 17, fill=self.RED, outline=self.RED)

        tk.Label(header, text="SẢNH TRUYỆN", bg="#0D0909", fg=self.TEXT, font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Label(header, text="ĐỌC  ·  DỊCH  ·  NGHE", bg="#0D0909", fg=self.COPPER, font=("Segoe UI", 9, "bold")).pack(side="left", padx=22, pady=(8, 0))
        workspace = tk.Frame(header, bg="#0D0909")
        workspace.pack(side="right", padx=22)
        tk.Label(workspace, text="LOCAL WORKSPACE", bg="#0D0909", fg=self.MUTED, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 10))
        tk.Label(workspace, text="●", bg="#0D0909", fg="#79B98B", font=("Segoe UI", 9)).pack(side="left")

        body = tk.Frame(self, bg=self.BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, minsize=148, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(body, bg=self.SIDEBAR, width=148, highlightthickness=1, highlightbackground="#2F1C17")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        tk.Label(sidebar, text="THƯ VIỆN HUYỀN BÍ", bg=self.SIDEBAR, fg=self.COPPER, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=14, pady=(24, 18))

        for key, symbol, label in self.NAV_ITEMS:
            btn = tk.Button(
                sidebar, text=f"  {symbol}   {label}", anchor="w",
                command=lambda value=key: self.show_page(value),
                bg=self.SIDEBAR, fg=self.TEXT, activebackground=self.RED_DARK,
                activeforeground="#FFFFFF", relief="flat", bd=0, padx=8, pady=10,
                font=("Segoe UI", 9), cursor="hand2"
            )
            btn.pack(fill="x", padx=8, pady=1)
            self.nav_buttons[key] = btn

        tk.Frame(sidebar, bg=self.LINE, height=1).pack(fill="x", padx=12, pady=(16, 14))
        tk.Label(sidebar, text="THƯ MỤC DỮ LIỆU", bg=self.SIDEBAR, fg=self.MUTED, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=14, pady=(0, 8))
        for label in ("›  EPUB", "›  RAW TXT", "›  BẢN DỊCH", "›  AUDIO"):
            tk.Label(sidebar, text=label, bg=self.SIDEBAR, fg="#89796E", font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=18, pady=4)
        tk.Label(sidebar, text="OCCULT LIBRARY\nCPU EDITION · v0.3", bg=self.SIDEBAR, fg="#68564D", font=("Segoe UI", 7), justify="left", anchor="w").pack(side="bottom", fill="x", padx=14, pady=14)

        self.container = tk.Frame(body, bg=self.BG)
        self.container.grid(row=0, column=1, sticky="nsew", padx=(26, 24), pady=(22, 12))

        footer = tk.Frame(self, bg="#0D0909", height=26, highlightthickness=1, highlightbackground="#241611")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self.status_var = tk.StringVar(value="Sẵn sàng")
        tk.Label(footer, textvariable=self.status_var, bg="#0D0909", fg=self.MUTED, anchor="w", font=("Segoe UI", 8)).pack(fill="both", padx=14)

        self.pages = {
            "dashboard": DashboardPage(self.container, self),
            "crawl": CrawlPage(self.container, self),
            "translate": TranslatePage(self.container, self),
            "audio": AudioPage(self.container, self),
        }

    def show_page(self, name: str):
        for page in self.pages.values():
            page.pack_forget()
        self.current_page = name
        self.pages[name].pack(fill="both", expand=True)
        for key, button in self.nav_buttons.items():
            active = key == name
            button.configure(
                bg=self.RED_DARK if active else self.SIDEBAR,
                fg="#FFFFFF" if active else self.TEXT,
                font=("Segoe UI", 9, "bold" if active else "normal")
            )
        if hasattr(self.pages[name], "on_show"):
            self.pages[name].on_show()

    def set_status(self, message: str):
        self.status_var.set(message)

    def _on_close(self):
        if messagebox.askyesno("Thoát SẢNH TRUYỆN", "Đóng ứng dụng? Các tác vụ đang chạy có thể bị dừng."):
            self.destroy()
