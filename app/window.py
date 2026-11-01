import tkinter as tk
from tkinter import ttk, messagebox

try:
    from tkinterdnd2 import TkinterDnD
    BaseWindow = TkinterDnD.Tk
except Exception:
    TkinterDnD = None
    BaseWindow = tk.Tk

from app.config import APP_NAME
from app.ui.pages import DashboardPage, CrawlPage, TranslatePage, AudioPage


class SảnhTruyệnApp(BaseWindow):
    BG = "#090707"
    SIDEBAR = "#100B0A"
    PANEL = "#17100F"
    PANEL_2 = "#201513"
    COPPER = "#B97848"
    RED = "#D21F32"
    TEXT = "#E9DFD2"
    MUTED = "#A89A8C"

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1280x820")
        self.minsize(980, 680)
        self.configure(bg=self.BG)
        self._configure_style()
        self.current_page = None
        self.pages = {}
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
        style.configure("Heading.TLabel", background=self.BG, foreground=self.TEXT, font=("Georgia", 24, "bold"))
        style.configure("Subheading.TLabel", background=self.BG, foreground=self.COPPER, font=("Segoe UI", 10))
        style.configure("TButton", background=self.PANEL_2, foreground=self.TEXT, padding=(12, 8), borderwidth=0)
        style.map("TButton", background=[("active", "#39241D")], foreground=[("disabled", "#776B62")])
        style.configure("Accent.TButton", background=self.COPPER, foreground="#110B09", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#D39A68")])
        style.configure("Treeview", background=self.PANEL, fieldbackground=self.PANEL, foreground=self.TEXT, rowheight=28)
        style.configure("Treeview.Heading", background=self.PANEL_2, foreground=self.COPPER, font=("Segoe UI", 9, "bold"))
        style.configure("TCombobox", fieldbackground=self.PANEL_2, background=self.PANEL_2, foreground=self.TEXT)
        style.configure("Horizontal.TProgressbar", background=self.COPPER, troughcolor=self.PANEL_2)

    def _build_shell(self):
        header = tk.Frame(self, bg=self.SIDEBAR, height=72, highlightthickness=1, highlightbackground="#38251D")
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="✦", bg=self.SIDEBAR, fg=self.COPPER, font=("Georgia", 24)).pack(side="left", padx=(24, 10))
        tk.Label(header, text="SẢNH TRUYỆN", bg=self.SIDEBAR, fg=self.TEXT, font=("Georgia", 21, "bold")).pack(side="left")
        tk.Label(header, text="THƯ VIỆN BÍ MẬT · XƯỞNG BIÊN TẬP", bg=self.SIDEBAR, fg=self.MUTED, font=("Segoe UI", 8)).pack(side="left", padx=18, pady=(8, 0))
        self.back_button = tk.Button(header, text="←  TRANG CHỦ", command=lambda: self.show_page("dashboard"), bg=self.PANEL_2, fg=self.TEXT, activebackground="#39241D", activeforeground=self.TEXT, relief="flat", padx=14, pady=8, cursor="hand2")
        self.back_button.pack(side="right", padx=22)
        self.container = tk.Frame(self, bg=self.BG)
        self.container.pack(fill="both", expand=True, padx=26, pady=(22, 12))
        footer = tk.Frame(self, bg=self.SIDEBAR, height=28)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self.status_var = tk.StringVar(value="Sẵn sàng")
        tk.Label(footer, textvariable=self.status_var, bg=self.SIDEBAR, fg=self.MUTED, anchor="w", font=("Segoe UI", 8)).pack(fill="both", padx=16)
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
        page = self.pages[name]
        page.pack(fill="both", expand=True)
        self.back_button.pack_forget() if name == "dashboard" else self.back_button.pack(side="right", padx=22)
        if hasattr(page, "on_show"):
            page.on_show()

    def set_status(self, message: str):
        self.status_var.set(message)

    def _on_close(self):
        if messagebox.askyesno("Thoát SẢNH TRUYỆN", "Đóng ứng dụng? Các tác vụ đang chạy có thể bị dừng."):
            self.destroy()
