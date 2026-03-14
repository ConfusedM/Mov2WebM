"""
MOV to WebM Converter - Preserves Transparency
Converts MOV files (with alpha channel) to WebM (VP9) with transparent background.
"""

import subprocess
import sys
import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox


def find_ffmpeg():
    """Find ffmpeg executable."""
    # Check if bundled ffmpeg exists next to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_ffmpeg = os.path.join(script_dir, "ffmpeg.exe")
    if os.path.isfile(local_ffmpeg):
        return local_ffmpeg
    # Check PATH
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return "ffmpeg"
    except FileNotFoundError:
        return None


class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MOV to WebM Converter (Transparent)")
        self.root.geometry("620x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.files = []
        self.ffmpeg = find_ffmpeg()
        self.converting = False

        self._build_ui()

        if not self.ffmpeg:
            messagebox.showerror(
                "FFmpeg Not Found",
                "FFmpeg is required.\n\n"
                "Run setup.bat to install it automatically,\n"
                "or download it from https://ffmpeg.org and place ffmpeg.exe\n"
                "next to this script.",
            )

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#89b4fa")
        style.configure("TProgressbar", troughcolor="#313244", background="#a6e3a1")

        # Header
        ttk.Label(self.root, text="MOV → WebM  (Alpha Preserved)", style="Header.TLabel").pack(pady=(18, 4))
        ttk.Label(self.root, text="Converts MOV files to WebM with transparent background").pack()

        # Buttons row
        btn_frame = tk.Frame(self.root, bg="#1e1e2e")
        btn_frame.pack(pady=12)

        ttk.Button(btn_frame, text="Add Files", command=self._add_files).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Clear List", command=self._clear_files).pack(side=tk.LEFT, padx=4)

        # File list
        list_frame = tk.Frame(self.root, bg="#313244", bd=1, relief=tk.SUNKEN)
        list_frame.pack(padx=18, fill=tk.BOTH, expand=True)

        self.file_listbox = tk.Listbox(
            list_frame,
            bg="#313244",
            fg="#cdd6f4",
            selectbackground="#45475a",
            font=("Consolas", 9),
            borderwidth=0,
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(padx=18, pady=(10, 2), fill=tk.X)

        self.status_var = tk.StringVar(value="Ready — add some MOV files to get started.")
        ttk.Label(self.root, textvariable=self.status_var).pack(pady=(0, 4))

        # Convert button
        self.convert_btn = ttk.Button(self.root, text="Convert All", command=self._start_convert)
        self.convert_btn.pack(pady=(0, 16))

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select MOV files",
            filetypes=[("MOV files", "*.mov"), ("All video files", "*.mov *.mp4 *.avi *.mkv"), ("All files", "*.*")],
        )
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.file_listbox.insert(tk.END, os.path.basename(p))
        self.status_var.set(f"{len(self.files)} file(s) ready.")

    def _clear_files(self):
        self.files.clear()
        self.file_listbox.delete(0, tk.END)
        self.progress_var.set(0)
        self.status_var.set("Ready — add some MOV files to get started.")

    def _start_convert(self):
        if self.converting:
            return
        if not self.files:
            messagebox.showinfo("No files", "Add some MOV files first.")
            return
        if not self.ffmpeg:
            messagebox.showerror("FFmpeg missing", "FFmpeg not found. Run setup.bat first.")
            return
        self.converting = True
        self.convert_btn.configure(state=tk.DISABLED)
        threading.Thread(target=self._convert_all, daemon=True).start()

    def _convert_all(self):
        total = len(self.files)
        succeeded = 0
        failed = []

        for i, filepath in enumerate(self.files):
            name = os.path.basename(filepath)
            self.root.after(0, self.status_var.set, f"Converting ({i+1}/{total}): {name}")

            out_path = os.path.splitext(filepath)[0] + ".webm"

            cmd = [
                self.ffmpeg,
                "-y",
                "-i", filepath,
                "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p",
                "-auto-alt-ref", "0",
                "-b:v", "2M",
                "-an",              # drop audio (typical for transparent overlays)
                out_path,
            ]

            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode != 0:
                    failed.append((name, result.stderr.decode(errors="replace")[-300:]))
                else:
                    succeeded += 1
            except Exception as e:
                failed.append((name, str(e)))

            self.root.after(0, self.progress_var.set, ((i + 1) / total) * 100)

        # Done
        def finish():
            self.converting = False
            self.convert_btn.configure(state=tk.NORMAL)
            if failed:
                details = "\n".join(f"  • {n}" for n, _ in failed)
                messagebox.showwarning(
                    "Done with errors",
                    f"Converted {succeeded}/{total} files.\n\nFailed:\n{details}",
                )
                self.status_var.set(f"Done — {succeeded} OK, {len(failed)} failed.")
            else:
                messagebox.showinfo("Done", f"All {total} file(s) converted successfully!")
                self.status_var.set(f"Done — {succeeded} file(s) converted.")

        self.root.after(0, finish)


if __name__ == "__main__":
    root = tk.Tk()
    app = ConverterApp(root)
    root.mainloop()
