"""
Offline Evaluation Harness for JARVIS.
Evaluates routing accuracy and tool-calling on commands.jsonl without real side effects (dry run).
Target: 90% or higher accuracy across the command set.
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load env
env_path = PROJECT_ROOT / ".env"
load_dotenv(env_path)

from brain.router import router


def classify_command_dry_run(cmd: str, brain=None):
    """
    Determines expected route and tool for a command without executing real macOS commands.
    Returns (route_type, tool_name, args, latency_ms).
    """
    t0 = time.time()
    cleaned = cmd.strip().rstrip(".!?")
    
    # 1. Fast-Path dry-run checks
    for pattern, handler in router.patterns:
        match = pattern.match(cleaned)
        if match:
            # Determine tool name from matched rule
            if "volume" in pattern.pattern:
                if "what" in pattern.pattern:
                    return "FAST-PATH", "get_volume", {}, (time.time() - t0) * 1000
                level = int(match.group(1)) if match.groups() else 0
                return "FAST-PATH", "set_volume", {"level": level}, (time.time() - t0) * 1000
            elif "mute" in pattern.pattern:
                if pattern.pattern.startswith("^(?:unmute"):
                    return "FAST-PATH", "unmute_volume", {}, (time.time() - t0) * 1000
                return "FAST-PATH", "mute_volume", {}, (time.time() - t0) * 1000
            elif "open" in pattern.pattern:
                app_name = match.group(1).strip()
                if not (app_name.lower().startswith("my ") or "." in app_name):
                    return "FAST-PATH", "open_app", {"name": app_name}, (time.time() - t0) * 1000
            elif "quit" in pattern.pattern:
                app_name = match.group(1).strip()
                if not (app_name.lower().startswith("my ") or "." in app_name):
                    return "FAST-PATH", "quit_app", {"name": app_name}, (time.time() - t0) * 1000

    # 2. LLM Brain path (if API key available)
    if brain:
        try:
            # Query Claude for tool use decision only (mocking execution)
            tools = [
                {"name": "open_app", "description": "Open app", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
                {"name": "quit_app", "description": "Quit app", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
                {"name": "open_url", "description": "Open URL", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
                {"name": "find_file", "description": "Find file", "input_schema": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}},
            ]
            response = brain.client.messages.create(
                model=brain.model,
                max_tokens=100,
                system="You are JARVIS. If the user asks for a tool, call it. Otherwise reply.",
                messages=[{"role": "user", "content": cmd}],
                tools=tools
            )
            for block in response.content:
                if block.type == "tool_use":
                    return "CLAUDE", block.name, block.input, (time.time() - t0) * 1000
            return "CLAUDE", None, None, (time.time() - t0) * 1000
        except Exception as e:
            return "ERROR", None, None, (time.time() - t0) * 1000

    # Fallback heuristic for offline testing if no LLM key
    cmd_lower = cmd.lower()
    if ".com" in cmd_lower or "http" in cmd_lower:
        return "HEURISTIC", "open_url", {}, (time.time() - t0) * 1000
    elif "find" in cmd_lower or "search for" in cmd_lower:
        return "HEURISTIC", "find_file", {}, (time.time() - t0) * 1000
    elif any(q in cmd_lower for q in ["what", "who", "explain", "how"]):
        return "CONVERSATION", None, None, (time.time() - t0) * 1000

    return "UNKNOWN", None, None, (time.time() - t0) * 1000


def run_evaluations():
    commands_file = Path(__file__).parent / "commands.jsonl"
    if not commands_file.exists():
        print(f"❌ File not found: {commands_file}")
        return

    test_cases = []
    with open(commands_file, "r") as f:
        for line in f:
            if line.strip():
                test_cases.append(json.loads(line.strip()))

    print("=" * 70)
    print(f"🧪 JARVIS Evaluation Suite: Testing {len(test_cases)} Commands (Dry-Run)")
    print("=" * 70)

    brain = None
    try:
        from brain.llm import ClaudeBrain
        brain = ClaudeBrain()
    except Exception:
        pass

    passed = 0
    total = len(test_cases)
    fast_path_count = 0

    for i, test in enumerate(test_cases, 1):
        cmd = test["command"]
        expected_tool = test["expected_tool"]

        route_label, actual_tool, actual_args, latency = classify_command_dry_run(cmd, brain)

        if route_label == "FAST-PATH":
            fast_path_count += 1

        is_match = (actual_tool == expected_tool)
        status = "✅ PASS" if is_match else "❌ FAIL"
        if is_match:
            passed += 1

        print(f"[{i:02d}/{total}] {status} | {route_label:<12} | \"{cmd}\"")
        if not is_match:
            print(f"       Expected: {expected_tool} | Got: {actual_tool}")

    accuracy = (passed / total) * 100
    print("\n" + "=" * 70)
    print(f"📊 EVALUATION REPORT:")
    print(f"   Accuracy:        {passed}/{total} ({accuracy:.1f}%)")
    print(f"   Fast-Path Hits:  {fast_path_count}/{total} ({fast_path_count/total*100:.1f}%)")
    print(f"   Target:          90.0% or higher")
    print("=" * 70)


if __name__ == "__main__":
    run_evaluations()
