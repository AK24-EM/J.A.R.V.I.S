"""
Audio Text-to-Speech (TTS) module for JARVIS.
Uses macOS native `say` command for zero-setup, zero-latency local speech.
"""

import re
import subprocess
from typing import Optional


def sanitize_text_for_speech(text: str) -> str:
    """Strip markdown, backticks, URLs, emojis, and unpronounceable characters."""
    # Remove markdown code blocks and backticks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`.*?`", "", text)
    # Remove links / URLs
    text = re.sub(r"http[s]?://\S+", "", text)
    # Remove markdown bold/italics
    text = re.sub(r"[\*_#~]", "", text)
    # Clean quotes
    text = text.replace('"', "").replace("'", "")
    return text.strip()


def speak(text: str, voice: str = "Samantha", rate: int = 195, wait: bool = True) -> subprocess.Popen:
    """
    Speak text aloud using macOS `say`.
    If wait is True, blocks until speech completes.
    If wait is False, returns the running Popen process.
    """
    clean_text = sanitize_text_for_speech(text)
    if not clean_text:
        return None

    cmd = ["say", "-v", voice, "-r", str(rate), clean_text]
    
    if wait:
        subprocess.run(cmd, check=False)
        return None
    else:
        return subprocess.Popen(cmd)


def stop_speech(proc: Optional[subprocess.Popen]):
    """Stop currently playing speech (barge-in support)."""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            proc.kill()

