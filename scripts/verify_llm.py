"""Verify each free LLM provider works through LiteLLM — including tool calling.

Tool calling is the core skill the agent depends on, so we test it end to end,
not just plain text. A provider with no key is SKIPped, not failed.

Run:
    uv run python scripts/verify_llm.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import litellm
from dotenv import load_dotenv

load_dotenv()

# A tiny tool the model is expected to call.
WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current temperature for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name"}},
            "required": ["city"],
        },
    },
}


@dataclass
class Provider:
    label: str
    model: str
    env_key: str


PROVIDERS = [
    Provider(
        "Groq (gpt-oss-20b)",
        os.getenv("GROQ_MODEL", "groq/openai/gpt-oss-20b"),
        "GROQ_API_KEY",
    ),
    Provider(
        "Gemini Flash",
        os.getenv("GEMINI_MODEL", "gemini/gemini-3.8-flash"),
        "GEMINI_API_KEY",
    ),
    Provider(
        "OpenRouter (free)",
        os.getenv("OPENROUTER_MODEL", "openrouter/nvidia/nemotron-3.5-lightning:free"),
        "OPENROUTER_API_KEY",
    ),
]


def check(p: Provider) -> tuple[str, str]:
    if not os.getenv(p.env_key):
        return "SKIP", f"{p.env_key} not set"
    try:
        resp = litellm.completion(
            model=p.model,
            messages=[{"role": "user", "content": "What is the weather in Mumbai? Use the tool."}],
            tools=[WEATHER_TOOL],
            tool_choice="auto",
            max_tokens=256,
            timeout=30,
            num_retries=0,  # fail fast; a transient 503 is a provider issue, not a key issue
        )
        msg = resp.choices[0].message
        calls = getattr(msg, "tool_calls", None)
        if calls:
            return "OK", f"tool_call -> get_weather({calls[0].function.arguments})"
        return "WARN", f"responded, but made no tool call: {msg.content!r}"
    except Exception as e:  # noqa: BLE001 - report any failure per provider, keep going
        return "FAIL", f"{type(e).__name__}: {e}"


def main() -> int:
    print("Verifying LLM providers through LiteLLM...\n")
    ok = True
    for p in PROVIDERS:
        status, detail = check(p)
        print(f"[{status:4}] {p.label:22} {p.model}")
        print(f"        {detail}\n")
        if status == "FAIL":
            ok = False
    print("All configured providers responded." if ok else "Some providers FAILED — see above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
