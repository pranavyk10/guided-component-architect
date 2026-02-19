"""
llm_client.py
=============
OpenAI-SDK client pointed at local Ollama (http://localhost:11434/v1).

KEY FIX: deepseek-coder:6.7b often wraps code sections in markdown fences
(```typescript ... ```) even when instructed not to. _strip_markdown_fences()
removes all fences BEFORE returning the text, so the validator always
receives clean code without needing to handle fences itself.
"""

from __future__ import annotations

import re
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

_BASE_URL: str   = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
_API_KEY: str    = os.getenv("OPENAI_API_KEY",  "ollama")
_MODEL_NAME: str = os.getenv("MODEL_NAME",      "deepseek-coder:6.7b")

_client = OpenAI(api_key=_API_KEY, base_url=_BASE_URL)

# Matches opening fences: ```typescript  ```html  ```css  ```ts  ``` (bare)
_OPEN_FENCE_RE  = re.compile(r"```[a-zA-Z]*\n?", re.IGNORECASE)
# Matches closing fences: standalone ``` on its own line
_CLOSE_FENCE_RE = re.compile(r"^```\s*$", re.MULTILINE)


def _strip_markdown_fences(text: str) -> str:
    """
    Remove markdown code fences that deepseek-coder adds to output.

    Before fix:
        === login.component.css ===
        ```css
        .card { font-family: Inter, sans-serif; }
        ```

    After fix:
        === login.component.css ===
        .card { font-family: Inter, sans-serif; }
    """
    text = _OPEN_FENCE_RE.sub("", text)
    text = _CLOSE_FENCE_RE.sub("", text)
    return text


def check_ollama_reachable() -> None:
    """Verify Ollama is running. Exit with friendly instructions if not."""
    try:
        _client.models.list()
    except Exception:
        print(
            "\n[Error] Cannot reach Ollama at:", _BASE_URL,
            "\n\nTo fix:",
            "\n  1. Install Ollama  : https://ollama.com/download",
            "\n  2. Pull the model  : ollama pull deepseek-coder:6.7b",
            "\n  3. Start server    : ollama serve",
            "\n  4. Test connection : curl http://localhost:11434/api/tags\n"
        )
        sys.exit(1)


def generate_completion(system_prompt: str, user_prompt: str) -> str:
    """
    Send system + user message to Ollama and return clean text.

    Always strips markdown fences from the response before returning,
    since deepseek-coder:6.7b adds them regardless of instructions.
    """
    try:
        response = _client.chat.completions.create(
            model=_MODEL_NAME,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        return _strip_markdown_fences(content).strip()
    except OpenAIError as e:
        if "connection" in str(e).lower() or "refused" in str(e).lower():
            check_ollama_reachable()
        raise
