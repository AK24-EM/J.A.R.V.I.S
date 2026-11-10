"""
LLM Brain for JARVIS using Anthropic Claude 3.5 Haiku.
Handles reasoning, conversational responses, and tool-calling loop.
"""

import os
import time
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from anthropic import Anthropic
from brain.prompts import JARVIS_SYSTEM_PROMPT
from tools.registry import registry

logger = logging.getLogger("jarvis.brain")


class ClaudeBrain:
    def __init__(self, model: str = "claude-3-5-haiku-latest"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or "your_" in api_key.lower():
            raise ValueError("ANTHROPIC_API_KEY is missing or invalid in .env")
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def query(
        self,
        user_text: str,
        history: List[Dict[str, Any]],
        tools_enabled: bool = True
    ) -> Tuple[str, float, Optional[str]]:
        """
        Send a user prompt to Claude, execute any tool calls, and return:
        (assistant_reply, latency_in_ms, tool_called_name)
        """
        start_time = time.time()
        messages = list(history) + [{"role": "user", "content": user_text}]
        tool_called_name = None

        tools = registry.get_claude_tools() if tools_enabled else None

        # First request to Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=250,
            system=JARVIS_SYSTEM_PROMPT,
            messages=messages,
            tools=tools if tools else None,
        )

        reply_text = ""
        # Inspect response content blocks
        tool_use_block = None
        for block in response.content:
            if block.type == "text":
                reply_text += block.text
            elif block.type == "tool_use":
                tool_use_block = block

        # Handle tool calling loop if Claude decided to invoke a tool
        if tool_use_block:
            tool_name = tool_use_block.name
            tool_args = tool_use_block.input
            tool_id = tool_use_block.id
            tool_called_name = tool_name

            logger.info(f"Executing tool {tool_name} with args: {tool_args}")
            tool_result, status = registry.execute(tool_name, tool_args)

            # Append assistant message with tool call and user message with tool output
            tool_call_message = {
                "role": "assistant",
                "content": response.content
            }
            tool_result_message = {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": tool_result
                    }
                ]
            }

            second_response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                system=JARVIS_SYSTEM_PROMPT,
                messages=messages + [tool_call_message, tool_result_message]
            )

            reply_text = ""
            for block in second_response.content:
                if block.type == "text":
                    reply_text += block.text

        latency_ms = (time.time() - start_time) * 1000
        return reply_text.strip(), latency_ms, tool_called_name

