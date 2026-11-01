import tkinter as tk
from tkinter import ttk

BG = "#090707"
PANEL = "#17100F"
PANEL_2 = "#201513"
COPPER = "#B97848"
TEXT = "#E9DFD2"
MUTED = "#A89A8C"


def heading(parent, title: str, subtitle: str = ""):
    box = tk.Frame(parent, bg=BG)
    box.pack(fill="x", pady=(0, 18))
    tk.Label(box, text=title, bg=BG, fg=TEXT, font=("Georgia", 25, "bold")).pack(anchor="w")
    if subtitle:
        tk.Label(box, text=subtitle, bg=BG, fg=COPPER, font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))
    return box


def panel(parent, title: str | None = None):
    frame = tk.Frame(parent, bg=PANEL, padx=14, pady=12, highlightthickness=1, highlightbackground="#38251D")
    if title:
        tk.Label(frame, text=title.upper(), bg=PANEL, fg=COPPER, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 9))
    return frame


def button(parent, text: str, command, accent: bool = False):
    bg = COPPER if accent else PANEL_2
    fg = "#110B09" if accent else TEXT
    return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground="#D39A68" if accent else "#39241D", activeforeground=fg, relief="flat", bd=0, padx=13, pady=8, font=("Segoe UI", 9, "bold" if accent else "normal"), cursor="hand2")


def text_box(parent, height=16):
    frame = tk.Frame(parent, bg="#100B0A", highlightthickness=1, highlightbackground="#38251D")
    widget = tk.Text(frame, height=height, wrap="word", bg="#100B0A", fg=TEXT, insertbackground=COPPER, selectbackground="#63402F", relief="flat", padx=10, pady=10, font=("Segoe UI", 10), undo=True)
    scroll = ttk.Scrollbar(frame, orient="vertical", command=widget.yview)
    widget.configure(yscrollcommand=scroll.set)
    widget.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return frame, widget


def try_enable_drop(widget, callback):
    try:
        from tkinterdnd2 import DND_FILES
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", lambda event: callback(event.data))
        return True
    except Exception:
        return False
