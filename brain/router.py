"""
Fast-path rule-based router for JARVIS.
Bypasses the LLM for high-frequency, deterministic system commands (volume, app launches, mute),
providing instant sub-millisecond execution at zero API cost.
"""

import re
from typing import Optional, Tuple
from tools.registry import registry


class FastPathRouter:
    def __init__(self):
        # Precompile common command patterns
        self.patterns = [
            # Volume control: "volume 50", "set volume to 80%", "turn volume up to 40"
            (
                re.compile(r"^(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})%?$", re.IGNORECASE),
                self._handle_volume
            ),
            # Mute / Unmute
            (
                re.compile(r"^(?:mute|mute\s+audio|mute\s+volume|silence)$", re.IGNORECASE),
                lambda m: registry.execute("mute_volume", {})[0]
            ),
            (
                re.compile(r"^(?:unmute|unmute\s+audio|unmute\s+volume)$", re.IGNORECASE),
                lambda m: registry.execute("unmute_volume", {})[0]
            ),
            # Check volume
            (
                re.compile(r"^(?:what\s+is\s+the\s+volume|check\s+volume|current\s+volume)$", re.IGNORECASE),
                lambda m: registry.execute("get_volume", {})[0]
            ),
            # Open application: "open Spotify", "launch Safari", "open Google Chrome"
            (
                re.compile(r"^(?:open|launch)\s+([a-zA-Z0-9\s]+)$", re.IGNORECASE),
                self._handle_open_app
            ),
            # Quit application: "quit Spotify", "close Safari"
            (
                re.compile(r"^(?:quit|close|exit)\s+([a-zA-Z0-9\s]+)$", re.IGNORECASE),
                self._handle_quit_app
            ),
        ]

    def _handle_volume(self, match: re.Match) -> str:
        level = int(match.group(1))
        return registry.execute("set_volume", {"level": level})[0]

    def _handle_open_app(self, match: re.Match) -> Optional[str]:
        app_name = match.group(1).strip()
        # Exclude web URLs or ambiguous phrases like "open my resume"
        if app_name.lower().startswith("my ") or "." in app_name or app_name.lower() in ["file", "document", "tab"]:
            return None
        return registry.execute("open_app", {"name": app_name})[0]

    def _handle_quit_app(self, match: re.Match) -> Optional[str]:
        app_name = match.group(1).strip()
        if app_name.lower().startswith("my ") or "." in app_name:
            return None
        return registry.execute("quit_app", {"name": app_name})[0]

    def route(self, user_text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if the command matches a fast-path rule.
        Returns (is_handled, response_text).
        """
        cleaned = user_text.strip().rstrip(".!?")
        for pattern, handler in self.patterns:
            match = pattern.match(cleaned)
            if match:
                res = handler(match)
                if res is not None:
                    return True, res
        return False, None


# Global router instance
router = FastPathRouter()

