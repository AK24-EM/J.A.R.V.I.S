"""
Native macOS System Automation Tools for JARVIS.
Controls applications, volume, brightness, URLs, and files via AppleScript / native tools.
"""

import subprocess
import shutil
from typing import Optional


def open_app(name: str) -> str:
    """Open a macOS application by name."""
    try:
        subprocess.run(["open", "-a", name], check=True, capture_output=True, text=True)
        return f"Opened {name}"
    except subprocess.CalledProcessError as e:
        return f"Could not open application '{name}'. Error: {e.stderr.strip()}"


def quit_app(name: str) -> str:
    """Quit a macOS application by name via AppleScript."""
    script = f'tell application "{name}" to quit'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
        return f"Closed {name}"
    except subprocess.CalledProcessError as e:
        return f"Could not close '{name}'. Error: {e.stderr.strip()}"


def open_url(url: str) -> str:
    """Open a website URL in the default browser."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    try:
        subprocess.run(["open", url], check=True, capture_output=True)
        return f"Opened {url}"
    except Exception as e:
        return f"Failed to open URL {url}: {e}"


def set_volume(level: int) -> str:
    """Set macOS master output volume (0 to 100)."""
    level = max(0, min(100, int(level)))
    script = f"set volume output volume {level}"
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return f"Volume set to {level} percent"
    except Exception as e:
        return f"Failed to set volume: {e}"


def get_volume() -> str:
    """Get the current macOS master volume."""
    script = "output volume of (get volume settings)"
    try:
        res = subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
        return f"Volume is at {res.stdout.strip()} percent"
    except Exception as e:
        return f"Failed to get volume: {e}"


def mute_volume() -> str:
    """Mute system audio."""
    script = "set volume output muted true"
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return "Audio muted"
    except Exception as e:
        return f"Failed to mute: {e}"


def unmute_volume() -> str:
    """Unmute system audio."""
    script = "set volume output muted false"
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return "Audio unmuted"
    except Exception as e:
        return f"Failed to unmute: {e}"


def find_file(filename: str) -> str:
    """Search for files matching the given name using macOS Spotlight (mdfind)."""
    try:
        res = subprocess.run(["mdfind", "-name", filename], check=True, capture_output=True, text=True)
        lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
        if not lines:
            return f"No files found matching '{filename}'"
        top_matches = lines[:5]
        return f"Found {len(lines)} files. Top results: " + ", ".join(top_matches)
    except Exception as e:
        return f"File search error: {e}"


def open_file(filepath: str) -> str:
    """Open a file using its default macOS application."""
    try:
        subprocess.run(["open", filepath], check=True, capture_output=True)
        return f"Opened file {filepath}"
    except Exception as e:
        return f"Failed to open file: {e}"

