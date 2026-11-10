#!/usr/bin/env python3
"""
JARVIS: Personal Voice Assistant for macOS
Main Orchestrator and State Machine based on the official blueprint architecture.
"""

import sys
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load configuration
load_dotenv(PROJECT_ROOT / ".env")

from audio.stt import get_stt_engine, transcribe
from audio.tts import speak
from brain.router import router
from brain.llm import ClaudeBrain
from tools.registry import registry
from push_to_talk import AudioRecorder, run_spacebar_mode, run_enter_mode


def execute_cycle(wav_bytes, stt_engine_name, stt_client, brain, history, voice):
    """Executes a full voice turn from audio input to spoken output."""
    cycle_start = time.time()

    # 1. Speech-to-Text
    print("\n⏳ Transcribing speech...", flush=True)
    try:
        user_text, stt_ms = transcribe(stt_engine_name, stt_client, wav_bytes)
    except Exception as e:
        print(f"❌ STT Failure: {e}")
        return

    if not user_text:
        print("⚠️ No speech recognized.")
        return

    print(f"👤 You: \"{user_text}\" (STT: {stt_ms:.0f}ms)")

    # 2. Fast-Path Router Check
    is_fast_path, fast_reply = router.route(user_text)

    if is_fast_path:
        reply_text = fast_reply
        llm_ms = 0.5
        routing_label = "⚡ Fast-Path (0.5ms)"
    else:
        # 3. Brain (Claude Haiku + Tool Loop)
        print("🧠 Thinking with Claude Haiku...", flush=True)
        try:
            reply_text, llm_ms, tool_used = brain.query(user_text, history, tools_enabled=True)
            tool_note = f" [Tool: {tool_used}]" if tool_used else ""
            routing_label = f"🧠 Claude Haiku ({llm_ms:.0f}ms){tool_note}"
        except Exception as e:
            print(f"❌ Brain Failure: {e}")
            reply_text = "I encountered an error processing that request, sir."
            llm_ms = 0.0
            routing_label = "Error"

    # Maintain conversation memory
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply_text})

    # Keep short-term memory trimmed to last 8 turns (Section 8)
    if len(history) > 16:
        del history[:4]

    total_time_ms = (time.time() - cycle_start) * 1000
    print(f"🤖 JARVIS: \"{reply_text}\"")
    
    speed_tag = "🚀 FAST (<1.5s)" if total_time_ms < 1500 else "⏱️"
    print(f"{speed_tag} Latency: {total_time_ms/1000:.2f}s | {routing_label}")

    # 4. Text-to-Speech
    speak(reply_text, voice=voice, rate=195, wait=True)
    print("─" * 60)


def main():
    parser = argparse.ArgumentParser(description="JARVIS: Personal Voice Assistant for macOS")
    parser.add_argument("--mode", choices=["space", "enter"], default="space", help="Input mode: spacebar or enter key")
    parser.add_argument("--voice", default="Samantha", help="macOS say voice name (Samantha, Daniel, Karen, Alex)")
    args = parser.parse_args()

    print("=" * 65)
    print("🤖 JARVIS: Personal Voice Assistant for macOS")
    print("=" * 65)

    # Initialize STT
    try:
        stt_name, stt_client = get_stt_engine()
        print(f"🎤 Audio Engine: {stt_name.upper()} Speech-to-Text")
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Initialize Brain
    try:
        brain = ClaudeBrain()
        print("🧠 Brain Engine: Claude 3.5 Haiku + Tool Calling")
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)

    recorder = AudioRecorder()
    history = []

    print(f"🔊 Spoken Voice: macOS '{args.voice}'")
    print(f"🛠️ Registered Tools: {len(registry._tools)} system tools active")

    # Launch loop
    def on_audio_ready(wav_bytes):
        execute_cycle(wav_bytes, stt_name, stt_client, brain, history, args.voice)

    if args.mode == "space":
        print("\n[Controls: HOLD SPACEBAR to talk, RELEASE to send]")
        try:
            from pynput import keyboard
            import threading

            active = False
            lock = threading.Lock()

            def on_press(key):
                nonlocal active
                if key == keyboard.Key.space:
                    with lock:
                        if not active:
                            active = True
                            recorder.start()
                            print("\r🔴 Listening... (Release Space when done)", end="", flush=True)

            def on_release(key):
                nonlocal active
                if key == keyboard.Key.space:
                    with lock:
                        if active:
                            active = False
                            print("\r⏹️ Processing speech...                    ", flush=True)
                            wav = recorder.stop()
                            if wav:
                                threading.Thread(target=on_audio_ready, args=(wav,), daemon=True).start()

            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()

        except Exception as e:
            print(f"⚠️ Spacebar listener could not start ({e}). Using Enter key mode.")
            args.mode = "enter"

    if args.mode == "enter":
        print("\n[Controls: Press ENTER to start, ENTER again to stop]")
        try:
            while True:
                input("👉 Press [ENTER] to record...")
                recorder.start()
                print("🔴 Recording... Speak now! Press [ENTER] when done: ", end="", flush=True)
                input()
                wav = recorder.stop()
                if wav:
                    on_audio_ready(wav)
        except KeyboardInterrupt:
            print("\nShutting down JARVIS.")


if __name__ == "__main__":
    main()
