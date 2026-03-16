"""FFmpeg utility functions for MOV to WebM conversion."""

import os
import re
import sys
import subprocess


def get_ffmpeg_path():
    """Get the path to the bundled ffmpeg.exe."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'ffmpeg.exe')
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'ffmpeg.exe')


def get_duration_seconds(input_path):
    """Get the duration of a video file in seconds."""
    ffmpeg = get_ffmpeg_path()
    proc = subprocess.run(
        [ffmpeg, '-i', input_path],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    match = re.search(r'Duration:\s*(\d+):(\d+):(\d+)\.(\d+)', proc.stderr)
    if match:
        h, m, s, cs = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        return h * 3600 + m * 60 + s + cs / 100.0
    return 0


def has_audio(input_path):
    """Check if the input file has an audio stream."""
    ffmpeg = get_ffmpeg_path()
    proc = subprocess.run(
        [ffmpeg, '-i', input_path],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return 'Audio:' in proc.stderr


def convert(input_path, output_path, crf, progress_callback, cancel_event=None):
    """
    Convert a MOV file to WebM with alpha transparency.

    Args:
        input_path: Path to input .mov file
        output_path: Path for output .webm file
        crf: Quality value (0-63, lower is better)
        progress_callback: Called with (percentage: float, status: str)
        cancel_event: threading.Event, set to cancel conversion

    Returns:
        (success: bool, error_message: str or None)
    """
    ffmpeg = get_ffmpeg_path()

    if not os.path.isfile(ffmpeg):
        return False, f"FFmpeg not found at: {ffmpeg}"

    duration = get_duration_seconds(input_path)

    cmd = [
        ffmpeg,
        '-i', input_path,
        '-c:v', 'libvpx-vp9',
        '-pix_fmt', 'yuva420p',
        '-crf', str(crf),
        '-b:v', '0',
        '-row-mt', '1',
        '-deadline', 'good',
        '-cpu-used', '2',
    ]

    if has_audio(input_path):
        cmd.extend(['-c:a', 'libopus', '-b:a', '128k'])
    else:
        cmd.extend(['-an'])

    cmd.extend([
        '-progress', 'pipe:1',
        '-nostats',
        '-y',
        output_path,
    ])

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        return False, str(e)

    try:
        for line in proc.stdout:
            if cancel_event and cancel_event.is_set():
                proc.kill()
                # Clean up partial output
                try:
                    os.remove(output_path)
                except OSError:
                    pass
                return False, "Cancelled by user."

            line = line.strip()
            if line.startswith('out_time_us='):
                try:
                    us = int(line.split('=')[1])
                    if duration > 0:
                        pct = min((us / 1_000_000) / duration * 100, 99.9)
                        progress_callback(pct, "Converting...")
                except ValueError:
                    pass

        proc.wait()

        if proc.returncode == 0:
            progress_callback(100, "Done!")
            return True, None
        else:
            stderr = proc.stderr.read()
            return False, stderr[-1000:] if len(stderr) > 1000 else stderr

    except Exception as e:
        proc.kill()
        return False, str(e)
