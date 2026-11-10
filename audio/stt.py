"""
Audio Speech-to-Text (STT) module for JARVIS.
Supports Deepgram, Groq Whisper (ultra-fast <250ms), and OpenAI Whisper.
"""

import io
import os
import time
from typing import Tuple


def get_stt_engine() -> Tuple[str, any]:
    """
    Selects and initializes the best available cloud STT engine.
    Priority order: Deepgram -> Groq -> OpenAI
    """
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if deepgram_key and "your_" not in deepgram_key.lower():
        from deepgram import DeepgramClient
        return "deepgram", DeepgramClient(deepgram_key)
    elif groq_key and "your_" not in groq_key.lower():
        from groq import Groq
        return "groq", Groq(api_key=groq_key)
    elif openai_key and "your_" not in openai_key.lower():
        from openai import OpenAI
        return "openai", OpenAI(api_key=openai_key)
    else:
        raise ValueError(
            "No STT API key configured. Please set DEEPGRAM_API_KEY, GROQ_API_KEY, "
            "or OPENAI_API_KEY in your .env file."
        )


def transcribe(engine_name: str, client: any, wav_bytes: bytes) -> Tuple[str, float]:
    """
    Transcribe WAV audio bytes to text.
    Returns (transcript_text, latency_in_ms).
    """
    start_time = time.time()
    text = ""

    if engine_name == "deepgram":
        from deepgram import PrerecordedOptions
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            language="en"
        )
        response = client.listen.rest.v("1").transcribe_file(
            {"buffer": wav_bytes, "mimetype": "audio/wav"},
            options
        )
        try:
            text = response.results.channels[0].alternatives[0].transcript.strip()
        except (AttributeError, IndexError):
            text = ""

    elif engine_name == "groq":
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "input.wav"
        res = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            response_format="text",
            language="en"
        )
        text = res.strip() if isinstance(res, str) else res.text.strip()

    elif engine_name == "openai":
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "input.wav"
        res = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            response_format="text",
            language="en"
        )
        text = res.strip() if isinstance(res, str) else res.text.strip()

    latency_ms = (time.time() - start_time) * 1000
    return text, latency_ms

