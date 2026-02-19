"""
agents/generator.py
===================
Generator Agent.

Loads design_tokens.json, builds a strict system prompt with all token values
embedded in the SYSTEM role, then calls deepseek-coder:6.7b via Ollama.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from llm_client import generate_completion, check_ollama_reachable
from prompts import SYSTEM_GENERATOR_PROMPT

_TOKENS_PATH = Path(__file__).resolve().parent.parent / "design_tokens.json"
_MODEL = os.getenv("MODEL_NAME", "deepseek-coder:6.7b")


def load_design_tokens() -> dict:
    """Load design tokens from design_tokens.json."""
    with open(_TOKENS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(tokens: dict) -> str:
    """
    Inject design token values into the system prompt.

    SECURITY: Token values are placed in the SYSTEM role (not user role)
    so they act as authoritative constraints the model cannot override.
    """
    return SYSTEM_GENERATOR_PROMPT.format(
        primary_color=tokens["primary_color"],
        secondary_color=tokens["secondary_color"],
        border_radius=tokens["border_radius"],
        font_family=tokens["font_family"],
        card_padding=tokens["card_padding"],
        shadow=tokens["shadow"],
    )


def generate_component(user_description: str) -> str:
    """
    Generate an Angular component from a natural language description.

    Args:
        user_description: Sanitized UI description from the user.

    Returns:
        Raw LLM output containing the 3-section Angular component.
    """
    # Fail fast with a friendly message if Ollama is not running
    check_ollama_reachable()

    tokens = load_design_tokens()
    system_prompt = build_system_prompt(tokens)

    user_prompt = (
        "Generate an Angular component for the following UI:\n\n"
        f"{user_description}\n\n"
        "Output raw code only. Exactly 3 sections. No markdown. No explanation."
    )

    print(f"[Generator] Model : {_MODEL}  (local Ollama)")
    print("[Generator] Calling deepseek-coder:6.7b...")
    raw_output = generate_completion(system_prompt, user_prompt)
    print("[Generator] Response received.")
    return raw_output
