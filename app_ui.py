# app_ui.py
# This module defines the UI for the VRChat Uploader application.

import tkinter as tk
from tkinter import ttk


def set_dark_mode(style: ttk.Style) -> None:
    """Dark theme + clear, thick progress bar + button styles."""
    style.theme_use('clam')

    style.configure("TFrame", background="#23272f")
    style.configure("TLabel", background="#23272f", foreground="#e9ecef")
    style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"),
                    background="#23272f", foreground="#00bfff")
    style.configure("Status.TLabel", font=("Segoe UI", 10),
                    background="#23272f", foreground="#e9ecef")

    style.configure("Treeview", background="#2c313c", foreground="#e9ecef",
                    fieldbackground="#2c313c", borderwidth=0, relief="flat")
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                    background="#23272f", foreground="#00bfff")

    style.configure("Green.Horizontal.TProgressbar",
                    troughcolor="#2b2f3a",
                    background="#6c757d",  
                    bordercolor="#2b2f3a",
                    lightcolor="#6c757d",
                    darkcolor="#6c757d",
                    thickness=14)

    style.configure("Accent.TButton", foreground="#23272f", background="#00bfff",
                    relief="flat", font=("Segoe UI", 12, "bold"),
                    padding=(25, 14), borderwidth=0)
    style.map("Accent.TButton",
              foreground=[('active', '#23272f')],
              background=[('active', '#0099cc')])

def setup_ui(root: tk.Tk,
             file_path_var: tk.StringVar,
             status_var: tk.StringVar,
             progress_bar_var: tk.IntVar,
             upload_count_var: tk.StringVar,
             upload_progress_var: tk.StringVar,
             current_file_var: tk.StringVar,
             browse_callback,
             has_dnd: bool):
    """Build the UI. Returns (browse_button, tree, progressbar, status_label, progress_label, current_file_label)."""
    style = ttk.Style(root)
    set_dark_mode(style)

    main_frame = ttk.Frame(root, padding=(40, 30))
    main_frame.pack(fill="both", expand=True)

    ttk.Label(main_frame, text="VRChat Avatar Uploader", style="Title.TLabel").pack(pady=(0, 10))
    dnd_text = "Drag and drop avatar files here, or click Browse." if has_dnd else "Click Browse to select avatar files."
    ttk.Label(main_frame, text=dnd_text, style="Status.TLabel").pack(pady=(0, 10))
    ttk.Label(main_frame, textvariable=file_path_var, wraplength=600, justify="center",
              style="Status.TLabel").pack(fill="x", pady=(10, 20))

    queue_frame = ttk.Frame(main_frame)
    queue_frame.pack(fill="both", expand=True, pady=(10, 20))
    scroll = ttk.Scrollbar(queue_frame)
    scroll.pack(side="right", fill="y")

    upload_queue_tree = ttk.Treeview(
        queue_frame,
        columns=("File Name", "Status", "Progress"),
        show="headings",
        yscrollcommand=scroll.set,
        style="Treeview"
    )
    for col, w in (("File Name", 300), ("Status", 140), ("Progress", 110)):
        upload_queue_tree.heading(col, text=col)
        upload_queue_tree.column(col, width=w, anchor=("w" if col == "File Name" else "center"))
    upload_queue_tree.pack(side="left", fill="both", expand=True)
    scroll.config(command=upload_queue_tree.yview)

    for tag, color in (("too_big", "#3a2b2b"),
                       ("duplicate", "#3a372b"),
                       ("success", "#2b3a2e"),
                       ("skipped", "#2b313a")):
        upload_queue_tree.tag_configure(tag, background=color)

    current_file_label = ttk.Label(main_frame, textvariable=current_file_var, style="Status.TLabel")
    current_file_label.pack(pady=(0, 10))

    progress_frame = ttk.Frame(main_frame)
    progress_frame.pack(fill="x", pady=(0, 10))
    progress_bar = ttk.Progressbar(
        progress_frame,
        variable=progress_bar_var,
        mode='determinate',
        style="Green.Horizontal.TProgressbar"
    )
    progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
    progress_label = ttk.Label(progress_frame, textvariable=upload_progress_var, style="Status.TLabel")
    progress_label.pack(side="right")

    info_frame = ttk.Frame(main_frame)
    info_frame.pack(fill="x", pady=(10, 14))
    status_label = ttk.Label(info_frame, textvariable=status_var, style="Status.TLabel")
    status_label.pack(side="left", padx=(0, 10))
    ttk.Label(info_frame, textvariable=upload_count_var, style="Status.TLabel").pack(side="right")

    file_select_frame = ttk.Frame(main_frame)
    file_select_frame.pack(fill="x", pady=(4, 8))

    browse_button = tk.Button(
        file_select_frame,
        text="📂  Browse Files",
        command=browse_callback,
        font=("Segoe UI", 12, "bold"),
        height=2,            
        bg="#0d6efd",
        fg="#ffffff",
        activebackground="#0b5ed7",
        activeforeground="#ffffff",
        bd=0,
        relief="flat",
        cursor="hand2"
    )
    browse_button.pack(side="top", fill="x", padx=40, pady=12)


    ttk.Label(main_frame, text="VRChat Uploader v1.0", style="Status.TLabel") \
       .pack(side="bottom", pady=(12, 0))

    return browse_button, upload_queue_tree, progress_bar, status_label, progress_label, current_file_label
