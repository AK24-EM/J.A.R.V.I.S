#!/usr/bin/env python3
"""
Step 1: Setup and Microphone Test for JARVIS
Records 5 seconds of audio from your microphone and plays it back immediately.
This surfaces macOS microphone permissions and audio device configuration.
"""

import sys
import time
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000  # 16kHz is standard for STT engines
DURATION = 5.0       # 5 seconds recording


def test_microphone():
    print("=" * 60)
    print("🤖 JARVIS - Step 1: Audio Hardware & Microphone Test")
    print("=" * 60)

    # 1. Query audio devices
    try:
        input_dev = sd.query_devices(kind='input')
        output_dev = sd.query_devices(kind='output')
        print(f"🎤 Default Input Device:  {input_dev.get('name', 'Unknown')}")
        print(f"🔊 Default Output Device: {output_dev.get('name', 'Unknown')}")
    except Exception as e:
        print(f"⚠️ Error querying audio devices: {e}")
        return False

    print("\n[!] Prepare to speak into your microphone.")
    for i in range(3, 0, -1):
        print(f"Starting in {i}...", end="\r", flush=True)
        time.sleep(1)

    print("\n🔴 RECORDING for 5 seconds... (Say something like: 'Testing JARVIS microphone!')")

    # 2. Record 5 seconds
    try:
        audio = sd.rec(
            int(DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32'
        )
        
        # Show a live countdown / visual indicator
        start_time = time.time()
        while time.time() - start_time < DURATION:
            elapsed = time.time() - start_time
            remaining = max(0.0, DURATION - elapsed)
            bar = "█" * int((elapsed / DURATION) * 30)
            print(f"  Recording: [{bar:<30}] {remaining:.1f}s remaining", end="\r", flush=True)
            time.sleep(0.1)

        sd.wait()
        print("\n✅ Recording finished!")

    except Exception as e:
        print(f"\n❌ Recording failed: {e}")
        print("\nNOTE for macOS:")
        print("Ensure your terminal / IDE has Microphone permissions enabled:")
        print("  System Settings -> Privacy & Security -> Microphone")
        return False

    # 3. Analyze volume level
    audio_flat = audio.flatten()
    rms = np.sqrt(np.mean(np.square(audio_flat)))
    peak = np.max(np.abs(audio_flat))
    print(f"\n📊 Audio Analysis: Peak Level = {peak:.4f}, RMS Volume = {rms:.4f}")

    if peak < 0.01:
        print("\n⚠️ WARNING: Audio signal is nearly silent!")
        print("Possible causes:")
        print("1. macOS Microphone permission was denied.")
        print("   Go to: System Settings -> Privacy & Security -> Microphone")
        print("   Toggle ON for Terminal / VS Code / Antigravity.")
        print("2. The input microphone is muted or volume is set too low.")
        print("3. Wrong input device is selected.")
    else:
        print("✅ Microphone input detected successfully!")

    # 4. Play back the recording
    print("\n🔊 PLAYING BACK your recording...")
    try:
        sd.play(audio, samplerate=SAMPLE_RATE)
        sd.wait()
        print("✅ Playback finished!")
    except Exception as e:
        print(f"❌ Playback failed: {e}")
        return False

    print("\n" + "=" * 60)
    if peak >= 0.01:
        print("🎉 SUCCESS! If you heard your voice clearly, Step 1 is complete.")
    else:
        print("⚠️ Check your macOS microphone permissions and try running again.")
    print("=" * 60)
    return peak >= 0.01


if __name__ == "__main__":
    test_microphone()
