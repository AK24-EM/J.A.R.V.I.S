#!/usr/bin/env python3
"""
Step 2: Push-to-talk Voice Loop for JARVIS
- Hold a key to speak, release to send
- Cloud Speech-to-Text (Groq Whisper or OpenAI Whisper)
- Claude Haiku (Anthropic) for the brain
- macOS `say` for instant text-to-speech
- Target: Under 2 seconds round-trip latency
"""

import io
import os
import sys
import time
import wave
import argparse
import subprocess
import threading
import numpy as np
import sounddevice as sd
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"


def get_anthropic_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or "your_" in api_key.lower():
        print("\n❌ Error: ANTHROPIC_API_KEY not found in .env!")
        print("Please edit .env and add your valid Anthropic API key.")
        sys.exit(1)
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def get_stt_client():
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if groq_key and "your_" not in groq_key.lower():
        import groq
        print("⚡ Cloud STT: Groq Whisper (Ultra-low latency ~250ms)")
        return "groq", groq.Groq(api_key=groq_key)
    elif openai_key and "your_" not in openai_key.lower():
        import openai
        print("☁️ Cloud STT: OpenAI Whisper")
        return "openai", openai.OpenAI(api_key=openai_key)
    else:
        print("\n❌ Error: No Cloud STT API key found!")
        print("Please set GROQ_API_KEY (recommended for <2s speed) or OPENAI_API_KEY in .env")
        sys.exit(1)


def transcribe_audio(stt_type, client, wav_bytes: bytes) -> str:
    """Send WAV audio bytes to Cloud STT service."""
    t0 = time.time()
    audio_file = io.BytesIO(wav_bytes)
    audio_file.name = "input.wav"

    if stt_type == "groq":
        res = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            response_format="text",
            language="en"
        )
        text = res.strip() if isinstance(res, str) else res.text.strip()
    else:  # openai
        res = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            response_format="text",
            language="en"
        )
        text = res.strip() if isinstance(res, str) else res.text.strip()

    stt_latency = (time.time() - t0) * 1000
    return text, stt_latency


def query_claude_haiku(client, prompt: str, conversation_history: list) -> tuple[str, float]:
    """Query Claude 3.5 Haiku for a fast, conversational response."""
    t0 = time.time()
    system_prompt = (
        "You are JARVIS, an exceptionally smart, helpful, and concise personal AI assistant. "
        "Keep your answers short and conversational (1 to 2 sentences max) because they are spoken aloud. "
        "Never use markdown formatting, asterisks, bullet points, emojis, or code blocks. "
        "Speak naturally and directly."
    )

    messages = conversation_history + [{"role": "user", "content": prompt}]

    response = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=150,
        system=system_prompt,
        messages=messages
    )
    
    reply = response.content[0].text.strip()
    llm_latency = (time.time() - t0) * 1000
    return reply, llm_latency


def speak_macos(text: str, voice: str = "Samantha"):
    """Speak text using macOS native `say` command."""
    # Clean text of any accidental quotes or formatting
    clean_text = text.replace('"', "").replace("`", "").replace("*", "").strip()
    subprocess.run(["say", "-v", voice, "-r", "195", clean_text])


class AudioRecorder:
    def __init__(self):
        self.frames = []
        self.is_recording = False
        self.stream = None
        self.lock = threading.Lock()

    def _audio_callback(self, indata, frames, time_info, status):
        if self.is_recording:
            with self.lock:
                self.frames.append(indata.copy())

    def start(self):
        with self.lock:
            self.frames = []
            self.is_recording = True
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._audio_callback
        )
        self.stream.start()

    def stop(self) -> bytes:
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        with self.lock:
            if not self.frames:
                return b""
            audio_data = np.concatenate(self.frames, axis=0)

        # Convert to WAV in memory
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())

        return buffer.getvalue()


def process_audio_pipeline(wav_bytes, stt_type, stt_client, anthropic_client, history, voice):
    """Processes audio: STT -> Claude Haiku -> macOS say with latency measurements."""
    overall_start = time.time()
    
    # 1. Speech to Text
    print("\n⏳ Transcribing speech...", flush=True)
    try:
        user_text, stt_ms = transcribe_audio(stt_type, stt_client, wav_bytes)
    except Exception as e:
        print(f"❌ STT Error: {e}")
        return

    if not user_text:
        print("⚠️ No speech recognized. Try speaking louder or closer to the mic.")
        return

    print(f"👤 You: \"{user_text}\" (STT: {stt_ms:.0f}ms)")

    # 2. Claude Haiku
    print("🧠 Thinking with Claude Haiku...", flush=True)
    try:
        reply_text, llm_ms = query_claude_haiku(anthropic_client, user_text, history)
    except Exception as e:
        print(f"❌ Claude Error: {e}")
        return

    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply_text})

    total_latency = (time.time() - overall_start) * 1000
    print(f"🤖 JARVIS: \"{reply_text}\" (LLM: {llm_ms:.0f}ms)")
    
    # Target check (< 2.0s)
    status_icon = "🚀" if total_latency < 2000 else "⏱️"
    print(f"{status_icon} Time to First Speech: {total_latency / 1000:.2f}s (STT: {stt_ms:.0f}ms | Brain: {llm_ms:.0f}ms)")

    # 3. macOS say
    speak_macos(reply_text, voice=voice)
    print("─" * 60)


def run_spacebar_mode(recorder, stt_type, stt_client, anthropic_client, history, voice):
    """Hold SPACE to speak, release SPACE to send (via pynput)."""
    from pynput import keyboard

    recording_active = False
    lock = threading.Lock()

    print("\n" + "=" * 60)
    print("🎙️ JARVIS PUSH-TO-TALK MODE (Hold SPACEBAR)")
    print("• HOLD [SPACEBAR] to speak")
    print("• RELEASE [SPACEBAR] to ask JARVIS")
    print("• Press [Ctrl+C] to exit")
    print("=" * 60 + "\n")

    def on_press(key):
        nonlocal recording_active
        if key == keyboard.Key.space:
            with lock:
                if not recording_active:
                    recording_active = True
                    recorder.start()
                    print("\r🔴 Recording... (release Space to finish)", end="", flush=True)

    def on_release(key):
        nonlocal recording_active
        if key == keyboard.Key.space:
            with lock:
                if recording_active:
                    recording_active = False
                    print("\r⏹️ Recording stopped. Processing...        ", flush=True)
                    wav_bytes = recorder.stop()
                    if wav_bytes:
                        threading.Thread(
                            target=process_audio_pipeline,
                            args=(wav_bytes, stt_type, stt_client, anthropic_client, history, voice),
                            daemon=True
                        ).start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\nExiting JARVIS...")


def run_enter_mode(recorder, stt_type, stt_client, anthropic_client, history, voice):
    """Press ENTER to start recording, press ENTER again to stop and send."""
    print("\n" + "=" * 60)
    print("🎙️ JARVIS PUSH-TO-TALK MODE (Enter Key)")
    print("• Press [ENTER] to start speaking")
    print("• Press [ENTER] again to stop and send")
    print("• Press [Ctrl+C] to exit")
    print("=" * 60 + "\n")

    try:
        while True:
            input("👉 Press [ENTER] to start speaking...")
            recorder.start()
            print("🔴 Recording... Speak now! Press [ENTER] when done: ", end="", flush=True)
            input()
            wav_bytes = recorder.stop()
            print("⏹️ Stopped. Processing...")
            if wav_bytes:
                process_audio_pipeline(wav_bytes, stt_type, stt_client, anthropic_client, history, voice)
    except KeyboardInterrupt:
        print("\nExiting JARVIS...")


def main():
    parser = argparse.ArgumentParser(description="JARVIS Push-to-Talk Voice Loop")
    parser.add_argument(
        "--mode",
        choices=["space", "enter"],
        default="space",
        help="Input mode: 'space' (hold spacebar) or 'enter' (press enter to start/stop)"
    )
    parser.add_argument(
        "--voice",
        default="Samantha",
        help="macOS say voice (e.g., Samantha, Daniel, Alex)"
    )
    args = parser.parse_args()

    # Initialize clients
    anthropic_client = get_anthropic_client()
    stt_type, stt_client = get_stt_client()
    recorder = AudioRecorder()
    history = []

    if args.mode == "space":
        try:
            run_spacebar_mode(recorder, stt_type, stt_client, anthropic_client, history, args.voice)
        except Exception as e:
            print(f"\n⚠️ Spacebar listener could not start: {e}")
            print("Falling back to Enter key mode...\n")
            run_enter_mode(recorder, stt_type, stt_client, anthropic_client, history, args.voice)
    else:
        run_enter_mode(recorder, stt_type, stt_client, anthropic_client, history, args.voice)


if __name__ == "__main__":
    main()

