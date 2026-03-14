"""
MOV to WebM Converter - Preserves Transparency
Converts MOV files (with alpha channel) to WebM (VP9) with transparent background.
Zero-setup: auto-downloads FFmpeg if not bundled.
"""

import subprocess
import sys
import os
import threading
import zipfile
import shutil
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from urllib.request import urlretrieve

FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"


def get_app_dir():
    """Get the directory where the exe (or script) lives."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_ffmpeg():
    """Find ffmpeg executable next to the app or on PATH."""
    local = os.path.join(get_app_dir(), "ffmpeg.exe")
    if os.path.isfile(local):
        return local
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


def download_ffmpeg(progress_callback=None):
    """Download and extract ffmpeg.exe to the app directory."""
    app_dir = get_app_dir()
    zip_path = os.path.join(app_dir, "ffmpeg_download.zip")

    def reporthook(block, block_size, total):
        if progress_callback and total > 0:
            progress_callback(block * block_size / total)

    urlretrieve(FFMPEG_URL, zip_path, reporthook)

    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith("/ffmpeg.exe"):
                with zf.open(name) as src, open(os.path.join(app_dir, "ffmpeg.exe"), "wb") as dst:
                    shutil.copyfileobj(src, dst)
                break

    os.remove(zip_path)
    return os.path.join(app_dir, "ffmpeg.exe")


class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MOV to WebM Converter")
        self.root.geometry("620x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.files = []
        self.ffmpeg = find_ffmpeg()
        self.converting = False

        self._build_ui()

        if not self.ffmpeg:
            self._prompt_download_ffmpeg()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#89b4fa")
        style.configure("TProgressbar", troughcolor="#313244", background="#a6e3a1")

        # Header
        ttk.Label(self.root, text="MOV \u2192 WebM  (Alpha Preserved)", style="Header.TLabel").pack(pady=(18, 4))
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

        self.status_var = tk.StringVar(value="Ready \u2014 add some MOV files to get started.")
        ttk.Label(self.root, textvariable=self.status_var).pack(pady=(0, 4))

        # Convert button
        self.convert_btn = ttk.Button(self.root, text="Convert All", command=self._start_convert)
        self.convert_btn.pack(pady=(0, 16))

    def _prompt_download_ffmpeg(self):
        answer = messagebox.askyesno(
            "FFmpeg Required",
            "FFmpeg is needed to convert videos but wasn't found.\n\n"
            "Download it automatically? (~90 MB, one-time only)\n\n"
            "It will be saved right next to this app.",
        )
        if answer:
            self._download_ffmpeg_threaded()

    def _download_ffmpeg_threaded(self):
        self.convert_btn.configure(state=tk.DISABLED)
        self.status_var.set("Downloading FFmpeg... please wait.")

        def run():
            try:
                def on_progress(fraction):
                    self.root.after(0, self.progress_var.set, fraction * 100)
                    self.root.after(0, self.status_var.set, f"Downloading FFmpeg... {int(fraction * 100)}%")

                path = download_ffmpeg(on_progress)
                self.ffmpeg = path

                def done():
                    self.progress_var.set(0)
                    self.status_var.set("FFmpeg ready! Add some MOV files to get started.")
                    self.convert_btn.configure(state=tk.NORMAL)
                    messagebox.showinfo("Done", "FFmpeg downloaded successfully!\nYou're all set.")

                self.root.after(0, done)
            except Exception as e:

                def fail():
                    self.progress_var.set(0)
                    self.status_var.set("FFmpeg download failed.")
                    self.convert_btn.configure(state=tk.NORMAL)
                    messagebox.showerror("Download Failed", f"Could not download FFmpeg:\n{e}")

                self.root.after(0, fail)

        threading.Thread(target=run, daemon=True).start()

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
        self.status_var.set("Ready \u2014 add some MOV files to get started.")

    def _start_convert(self):
        if self.converting:
            return
        if not self.files:
            messagebox.showinfo("No files", "Add some MOV files first.")
            return
        if not self.ffmpeg:
            self._prompt_download_ffmpeg()
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
            self.root.after(0, self.status_var.set, f"Converting ({i + 1}/{total}): {name}")

            out_path = os.path.splitext(filepath)[0] + ".webm"

            cmd = [
                self.ffmpeg,
                "-y",
                "-i", filepath,
                "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p",
                "-auto-alt-ref", "0",
                "-b:v", "2M",
                "-an",
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

        def finish():
            self.converting = False
            self.convert_btn.configure(state=tk.NORMAL)
            if failed:
                details = "\n".join(f"  \u2022 {n}" for n, _ in failed)
                messagebox.showwarning(
                    "Done with errors",
                    f"Converted {succeeded}/{total} files.\n\nFailed:\n{details}",
                )
                self.status_var.set(f"Done \u2014 {succeeded} OK, {len(failed)} failed.")
            else:
                messagebox.showinfo("Done", f"All {total} file(s) converted successfully!")
                self.status_var.set(f"Done \u2014 {succeeded} file(s) converted.")

        self.root.after(0, finish)


if __name__ == "__main__":
    root = tk.Tk()
    app = ConverterApp(root)
    root.mainloop()
