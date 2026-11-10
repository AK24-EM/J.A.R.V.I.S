"""
JARVIS Configuration
Loads settings from config.yaml and environment variables.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent / ".env")

# ─── Default Configuration ───────────────────────────────────────────

DEFAULT_CONFIG = {
    "assistant": {
        "name": "JARVIS",
        "wake_word": "jarvis",
        "voice": "Samantha",  # macOS voice: Samantha, Daniel, Karen, etc.
        "greeting": "JARVIS online. How can I assist you, sir?",
    },
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "record_duration": 5,  # seconds per recording chunk
        "silence_threshold": 0.01,  # RMS threshold for silence detection
        "silence_duration": 1.5,  # seconds of silence before stopping
    },
    "stt": {
        "engine": "whisper",  # "whisper" (local) or "google"
        "whisper_model": "base",  # tiny, base, small, medium, large
    },
    "llm": {
        "provider": "gemini",  # "gemini", "openai", or "anthropic"
        "model": "gemini-2.0-flash",
        "system_prompt": (
            "You are JARVIS, a highly intelligent and witty personal voice assistant "
            "inspired by the AI from Iron Man. You are running on macOS. "
            "You are helpful, precise, and occasionally charming. "
            "Keep responses concise and conversational — they will be spoken aloud. "
            "If the user asks you to do something on their Mac (open apps, control volume, "
            "search the web, etc.), respond with the action confirmation. "
            "Never use markdown formatting, code blocks, or special characters in your responses "
            "since they will be read aloud via text-to-speech."
        ),
        "max_tokens": 300,
    },
    "tts": {
        "engine": "macos",  # "macos" (say command), "pyttsx3", "edge-tts"
        "rate": 190,  # Words per minute for pyttsx3
    },
}


def load_config() -> dict:
    """Load configuration from config.yaml, falling back to defaults."""
    config_path = Path(__file__).parent / "config.yaml"

    config = DEFAULT_CONFIG.copy()

    if config_path.exists():
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, user_config)

    return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_api_key(provider: str) -> str:
    """Get API key for the specified provider from environment variables."""
    key_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "picovoice": "PICOVOICE_ACCESS_KEY",
    }
    env_var = key_map.get(provider, "")
    key = os.getenv(env_var, "")
    if not key:
        raise ValueError(
            f"API key not found for '{provider}'. "
            f"Set the {env_var} environment variable in your .env file."
        )
    return key

