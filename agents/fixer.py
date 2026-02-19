"""
agents/fixer.py
===============
Fixer / Self-Correction Agent.

Sends the original failed code + exact Validator error list back to
deepseek-coder:6.7b (via Ollama) and asks it to fix every issue.
The pipeline allows exactly ONE automatic retry.
"""

from __future__ import annotations

import json
from pathlib import Path

from llm_client import generate_completion
from prompts import FIXER_PROMPT_TEMPLATE

_TOKENS_PATH = Path(__file__).resolve().parent.parent / "design_tokens.json"

_FIXER_SYSTEM = (
    "You are a strict Angular code fixer. "
    "Output ONLY the corrected code in the required 3-section format. "
    "No explanation. No markdown fences. No text outside the three sections."
)


def fix_component(original_code: str, errors: list[str]) -> str:
    """
    Ask deepseek-coder:6.7b to fix a component that failed validation.

    Args:
        original_code: The full raw LLM output that failed validation.
        errors:        Exact error strings from the Validator.

    Returns:
        Corrected raw LLM output in the same 3-section format.
    """
    tokens = json.loads(_TOKENS_PATH.read_text(encoding="utf-8"))
    error_list = "\n".join(f"  - {e}" for e in errors)

    user_prompt = FIXER_PROMPT_TEMPLATE.format(
        error_list=error_list,
        original_code=original_code,
        primary_color=tokens["primary_color"],
        border_radius=tokens["border_radius"],
        card_padding=tokens["card_padding"],
        shadow=tokens["shadow"],
        font_family=tokens["font_family"],
    )

    print("[Fixer] Sending error report to deepseek-coder:6.7b for self-correction...")
    fixed_output = generate_completion(_FIXER_SYSTEM, user_prompt)
    print("[Fixer] Corrected component received.")
    return fixed_output
