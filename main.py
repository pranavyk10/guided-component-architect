"""
main.py
=======
Entry point and Pipeline Orchestrator for Guided Component Architect.
Uses deepseek-coder:6.7b running LOCALLY via Ollama.

Agentic Loop:
    User Input (sanitized)
        |
        v
    [1] Generator  -->  deepseek-coder:6.7b (Ollama)
        |
        v
    [2] Validator  -->  Pure Python static checks (NO LLM)
        |
        |-- VALID ------->  Write output files  ✅
        |
        |-- INVALID ----->  [3] Fixer  -->  deepseek-coder:6.7b
                                |
                                v
                           [4] Validator (retry)
                                |
                                |-- VALID -->  Write files  ✅
                                |-- INVALID -> Save + exit(2)

Usage:
    python main.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from agents.generator import generate_component
    from agents.validator import validate_component
    from agents.fixer     import fix_component
except EnvironmentError as env_err:
    print(f"\n{env_err}")
    sys.exit(1)

OUTPUT_DIR = Path(__file__).resolve().parent / "output_component"

_SECTION_RE = re.compile(
    r"===\s*login\.component\.(ts|html|css)\s*===\n(.*?)(?=\n===\s*login\.component\.|$)",
    re.DOTALL | re.IGNORECASE,
)

# Strip residual fences during file writing (third safety net)
_FENCE_RE = re.compile(r"```[a-zA-Z]*\n?|^```\s*$", re.IGNORECASE | re.MULTILINE)

_INJECTION_PATTERNS: list[str] = [
    "ignore previous",
    "disregard all",
    "forget your instructions",
    "you are now",
    "act as",
    "system:",
    "assistant:",
    "new instruction",
    "override",
    "jailbreak",
]


def _sanitize_input(text: str) -> str:
    """
    Prompt-injection mitigation on raw user input.
      1. Strip whitespace.
      2. Truncate to 500 chars.
      3. Truncate at known injection trigger phrases.
    """
    text = text.strip()[:500]
    lower = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in lower:
            idx = lower.find(pattern)
            print(
                f"[Security] Suspicious phrase: \"{pattern}\" — "
                f"truncating input at position {idx}."
            )
            text = text[:idx].strip()
            break
    return text


def _write_output(raw_code: str) -> None:
    """Parse 3-section LLM output and write files to output_component/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for match in _SECTION_RE.finditer(raw_code):
        ext  = match.group(1).lower()
        code = _FENCE_RE.sub("", match.group(2)).strip()
        filepath = OUTPUT_DIR / f"login.component.{ext}"
        filepath.write_text(code, encoding="utf-8")
        written.append(str(filepath))

    if written:
        print("\n✅  Files written to output_component/:")
        for path in written:
            print(f"    {path}")
    else:
        fallback = OUTPUT_DIR / "raw_output.txt"
        fallback.write_text(raw_code, encoding="utf-8")
        print(f"\n⚠️  Could not parse sections. Raw saved: {fallback}")


def _print_banner() -> None:
    print("=" * 60)
    print("   Guided Component Architect")
    print("   Pythrust Technologies  —  Gen AI Engineer Assignment")
    print("   Model : deepseek-coder:6.7b  (local via Ollama)")
    print("   API   : http://localhost:11434/v1  (no internet needed)")
    print("=" * 60)


def _print_errors(errors: list[str]) -> None:
    for err in errors:
        print(f"    • {err}")


def main() -> None:
    _print_banner()

    raw_input = input("\nDescribe the component: ").strip()
    if not raw_input:
        print("\n[Error] No description provided. Exiting.")
        sys.exit(1)

    user_description = _sanitize_input(raw_input)
    if not user_description:
        print("\n[Error] Input empty after sanitization. Exiting.")
        sys.exit(1)

    print(f'\n[Main] Description accepted: "{user_description}"\n')

    # ── Step 1: Generate ───────────────────────────────────────────────────
    try:
        raw_code = generate_component(user_description)
    except Exception as exc:
        print(f"\n[Error] Generator failed: {exc}")
        sys.exit(1)

    # ── Step 2: Validate ───────────────────────────────────────────────────
    print("\n[Validator] Running checks on generated component...")
    result = validate_component(raw_code)

    if result.is_valid:
        print("[Validator] ✅  All checks passed on first attempt.")
        _write_output(raw_code)
        return

    # ── Step 3: Self-correction ────────────────────────────────────────────
    print(f"\n[Validator] ❌  {len(result.errors)} error(s) found:")
    _print_errors(result.errors)

    try:
        fixed_code = fix_component(raw_code, result.errors)
    except Exception as exc:
        print(f"\n[Error] Fixer failed: {exc}")
        sys.exit(1)

    # ── Step 4: Re-validate ────────────────────────────────────────────────
    print("\n[Validator] Re-checking fixed component...")
    final_result = validate_component(fixed_code)

    if final_result.is_valid:
        print("[Validator] ✅  All checks passed after self-correction.")
        _write_output(fixed_code)
        return

    # ── Pipeline failure ───────────────────────────────────────────────────
    print(f"\n[Validator] ❌  Still {len(final_result.errors)} error(s) after fix:")
    _print_errors(final_result.errors)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failed_path = OUTPUT_DIR / "raw_output_failed.txt"
    failed_path.write_text(fixed_code, encoding="utf-8")
    print(f"\n[Main] Pipeline failed. Saved for review: {failed_path}")
    sys.exit(2)


if __name__ == "__main__":
    main()
