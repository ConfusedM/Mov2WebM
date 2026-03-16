"""MOV to WebM Converter - Preserves transparency/alpha channel."""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except Exception:
    HAS_DND = False

from ffmpeg_utils import convert, get_ffmpeg_path


# ── Theme colors ──
BG = "#1e1e2e"
BG_LIGHT = "#2a2a3e"
FG = "#cdd6f4"
FG_DIM = "#6c7086"
ACCENT = "#89b4fa"
ACCENT_HOVER = "#b4d0fb"
SUCCESS = "#a6e3a1"
ERROR = "#f38ba8"
BORDER = "#45475a"


class App:
    def __init__(self):
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("MOV → WebM Converter")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Center window
        w, h = 560, 520
        sx = self.root.winfo_screenwidth() // 2 - w // 2
        sy = self.root.winfo_screenheight() // 2 - h // 2
        self.root.geometry(f"{w}x{h}+{sx}+{sy}")

        self.input_path = None
        self.output_path = None
        self.converting = False
        self.cancel_event = threading.Event()

        self._build_ui()

    # ── UI ──

    def _build_ui(self):
        root = self.root

        # Title
        tk.Label(root, text="MOV → WebM", font=("Segoe UI", 20, "bold"),
                 bg=BG, fg=FG).pack(pady=(24, 2))
        tk.Label(root, text="Transparent video converter", font=("Segoe UI", 10),
                 bg=BG, fg=FG_DIM).pack(pady=(0, 16))

        # Drop zone
        self.drop_frame = tk.Frame(root, bg=BG_LIGHT, highlightbackground=BORDER,
                                   highlightthickness=2, cursor="hand2")
        self.drop_frame.pack(padx=32, fill="x", ipady=32)

        self.drop_label = tk.Label(
            self.drop_frame,
            text="Drop a .mov file here\nor click to browse",
            font=("Segoe UI", 12), bg=BG_LIGHT, fg=FG_DIM, justify="center",
        )
        self.drop_label.pack(expand=True, fill="both", pady=16)

        # Bind click to browse
        self.drop_frame.bind("<Button-1>", lambda e: self._browse())
        self.drop_label.bind("<Button-1>", lambda e: self._browse())

        # Register drag-and-drop
        if HAS_DND:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self._on_drop)

        # File info
        self.file_label = tk.Label(root, text="No file selected", font=("Segoe UI", 9),
                                   bg=BG, fg=FG_DIM, wraplength=480)
        self.file_label.pack(pady=(12, 4), padx=32, anchor="w")

        self.output_label = tk.Label(root, text="", font=("Segoe UI", 9),
                                     bg=BG, fg=FG_DIM, wraplength=480)
        self.output_label.pack(padx=32, anchor="w")

        # Quality slider
        slider_frame = tk.Frame(root, bg=BG)
        slider_frame.pack(padx=32, fill="x", pady=(16, 0))

        tk.Label(slider_frame, text="Quality", font=("Segoe UI", 10),
                 bg=BG, fg=FG).pack(side="left")

        self.crf_var = tk.IntVar(value=18)
        self.crf_label = tk.Label(slider_frame, text="18 (High)", font=("Segoe UI", 10),
                                  bg=BG, fg=ACCENT)
        self.crf_label.pack(side="right")

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Custom.Horizontal.TScale", background=BG, troughcolor=BG_LIGHT)

        self.crf_slider = ttk.Scale(
            root, from_=4, to=50, orient="horizontal",
            variable=self.crf_var, command=self._on_crf_change,
            style="Custom.Horizontal.TScale",
        )
        self.crf_slider.pack(padx=32, fill="x", pady=(4, 0))

        # Buttons
        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(padx=32, fill="x", pady=(20, 0))

        self.convert_btn = tk.Button(
            btn_frame, text="Convert", font=("Segoe UI", 12, "bold"),
            bg=ACCENT, fg="#11111b", activebackground=ACCENT_HOVER,
            relief="flat", cursor="hand2", height=1,
            command=self._start_convert, state="disabled",
        )
        self.convert_btn.pack(fill="x", ipady=4)

        self.cancel_btn = tk.Button(
            btn_frame, text="Cancel", font=("Segoe UI", 10),
            bg=BG_LIGHT, fg=FG, activebackground=BORDER,
            relief="flat", cursor="hand2",
            command=self._cancel_convert,
        )

        # Progress
        style.configure("Custom.Horizontal.TProgressbar",
                         troughcolor=BG_LIGHT, background=ACCENT, thickness=8)
        self.progress = ttk.Progressbar(root, maximum=100, mode='determinate',
                                         style="Custom.Horizontal.TProgressbar")
        self.progress.pack(padx=32, fill="x", pady=(16, 4))

        self.status_label = tk.Label(root, text="Ready", font=("Segoe UI", 9),
                                     bg=BG, fg=FG_DIM)
        self.status_label.pack(padx=32, anchor="w")

    # ── Handlers ──

    def _on_crf_change(self, val):
        crf = int(float(val))
        self.crf_var.set(crf)
        if crf <= 15:
            desc = "Very High"
        elif crf <= 23:
            desc = "High"
        elif crf <= 35:
            desc = "Medium"
        else:
            desc = "Low"
        self.crf_label.config(text=f"{crf} ({desc})")

    def _browse(self):
        if self.converting:
            return
        path = filedialog.askopenfilename(
            title="Select a MOV file",
            filetypes=[("MOV files", "*.mov"), ("All files", "*.*")],
        )
        if path:
            self._set_input(path)

    def _on_drop(self, event):
        if self.converting:
            return
        path = event.data.strip()
        # Handle paths wrapped in braces (tkdnd behavior for paths with spaces)
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        # Handle multiple files - take the first
        if '\n' in path:
            path = path.split('\n')[0].strip()
        if path.lower().endswith('.mov'):
            self._set_input(path)
        else:
            messagebox.showwarning("Wrong file type", "Please drop a .mov file.")

    def _set_input(self, path):
        self.input_path = path
        self.output_path = os.path.splitext(path)[0] + '.webm'

        name = os.path.basename(path)
        self.file_label.config(text=f"Input: {name}", fg=FG)
        self.drop_label.config(text=f"✓  {name}", fg=SUCCESS)

        out_name = os.path.basename(self.output_path)
        self.output_label.config(text=f"Output: {out_name}", fg=FG_DIM)

        self.convert_btn.config(state="normal")
        self.status_label.config(text="Ready to convert", fg=FG_DIM)
        self.progress['value'] = 0

    def _start_convert(self):
        if not self.input_path:
            return
        if not os.path.isfile(self.input_path):
            messagebox.showerror("File not found", f"Cannot find:\n{self.input_path}")
            return

        ffmpeg = get_ffmpeg_path()
        if not os.path.isfile(ffmpeg):
            messagebox.showerror("FFmpeg missing",
                                 f"FFmpeg not found at:\n{ffmpeg}\n\n"
                                 "The application may be corrupted. Please re-download it.")
            return

        # Check if output exists
        if os.path.isfile(self.output_path):
            ok = messagebox.askyesno("File exists",
                                     f"{os.path.basename(self.output_path)} already exists.\nOverwrite?")
            if not ok:
                return

        self.converting = True
        self.cancel_event.clear()
        self.convert_btn.config(state="disabled")
        self.cancel_btn.pack(fill="x", ipady=2, pady=(6, 0))
        self.crf_slider.config(state="disabled")
        self.status_label.config(text="Starting conversion...", fg=ACCENT)
        self.progress['value'] = 0

        crf = self.crf_var.get()
        thread = threading.Thread(
            target=self._run_convert, args=(self.input_path, self.output_path, crf),
            daemon=True,
        )
        thread.start()

    def _run_convert(self, inp, out, crf):
        def on_progress(pct, status):
            self.root.after(0, self._update_progress, pct, status)

        success, error = convert(inp, out, crf, on_progress, self.cancel_event)
        self.root.after(0, self._on_done, success, error)

    def _update_progress(self, pct, status):
        self.progress['value'] = pct
        self.status_label.config(text=f"{status} {pct:.0f}%", fg=ACCENT)

    def _on_done(self, success, error):
        self.converting = False
        self.convert_btn.config(state="normal")
        self.cancel_btn.pack_forget()
        self.crf_slider.config(state="normal")

        if success:
            self.progress['value'] = 100
            self.status_label.config(text="Conversion complete!", fg=SUCCESS)

            # Show file size
            size_mb = os.path.getsize(self.output_path) / (1024 * 1024)
            messagebox.showinfo("Done!",
                                f"Converted successfully!\n\n"
                                f"Output: {os.path.basename(self.output_path)}\n"
                                f"Size: {size_mb:.1f} MB")
        else:
            self.progress['value'] = 0
            if error and "Cancelled" in error:
                self.status_label.config(text="Cancelled", fg=FG_DIM)
            else:
                self.status_label.config(text="Conversion failed", fg=ERROR)
                messagebox.showerror("Conversion failed",
                                     f"FFmpeg error:\n\n{error}")

    def _cancel_convert(self):
        self.cancel_event.set()
        self.status_label.config(text="Cancelling...", fg=FG_DIM)

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = App()
    app.run()
