import tkinter as tk
from tkinter import ttk

BG = "#090707"
PANEL = "#17100F"
PANEL_2 = "#201513"
COPPER = "#B97848"
RED = "#D21F32"
TEXT = "#E9DFD2"
MUTED = "#A89A8C"
LINE = "#4A2920"
INPUT = "#100B0A"


def heading(parent, title: str, subtitle: str = ""):
    box = tk.Frame(parent, bg=BG)
    box.pack(fill="x", pady=(0, 16))
    label = tk.Label(box, text=title, bg=BG, fg=TEXT, font=("Segoe UI", 23, "bold"))
    label.pack(anchor="w")
    if subtitle:
        tk.Label(box, text=subtitle, bg=BG, fg="#C4A18A", font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))
    return box


def eyebrow(parent, text: str):
    return tk.Label(parent, text=text.upper(), bg=BG, fg=COPPER, font=("Segoe UI", 8, "bold"))


def panel(parent, title: str | None = None):
    frame = tk.Frame(parent, bg=PANEL, padx=14, pady=12, highlightthickness=1, highlightbackground=LINE)
    if title:
        tk.Label(frame, text=title.upper(), bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 9))
    return frame


def button(parent, text: str, command, accent: bool = False):
    bg = RED if accent else PANEL_2
    fg = "#FFFFFF" if accent else TEXT
    return tk.Button(
        parent, text=text, command=command, bg=bg, fg=fg,
        activebackground="#EA3548" if accent else "#39241D",
        activeforeground="#FFFFFF", relief="flat", bd=0,
        padx=14, pady=8, font=("Segoe UI", 9, "bold" if accent else "normal"),
        cursor="hand2", highlightthickness=1,
        highlightbackground=RED if accent else LINE,
        highlightcolor=RED
    )


def text_box(parent, height=16):
    frame = tk.Frame(parent, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
    widget = tk.Text(
        frame, height=height, wrap="word", bg=INPUT, fg=TEXT,
        insertbackground=COPPER, selectbackground="#5B1A25",
        relief="flat", padx=10, pady=10, font=("Segoe UI", 10),
        undo=True, spacing1=2, spacing3=3
    )
    scroll = ttk.Scrollbar(frame, orient="vertical", command=widget.yview)
    widget.configure(yscrollcommand=scroll.set)
    widget.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return frame, widget


def field_label(parent, text: str, bg=PANEL):
    return tk.Label(parent, text=text.upper(), bg=bg, fg=COPPER, font=("Segoe UI", 8, "bold"))


def divider(parent, bg=LINE):
    return tk.Frame(parent, bg=bg, height=1)


def try_enable_drop(widget, callback):
    try:
        from tkinterdnd2 import DND_FILES
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", lambda event: callback(event.data))
        return True
    except Exception:
        return False
