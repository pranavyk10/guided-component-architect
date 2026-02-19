"""
agents/validator.py
===================
Validator / Linter Agent — purely deterministic, zero LLM calls.

Six checks performed on the generated Angular component:
  1. Section presence       — ts, html, css sections must exist and be non-empty
  2. Design token regex     — primary_color, border_radius, font_family in output
  3. Bracket balance (TS)   — balanced {}, (), [] in TypeScript
  4. Bracket balance (CSS)  — balanced {}, (), [] in CSS
  5. Angular structure      — @Component decorator + export class present
  6. HTML tag balance       — stack-based open/close tag checker

ROBUSTNESS: _strip_section_fences() strips any residual markdown fences from
section content before running checks, acting as a double safety net on top
of the fence stripping already done in llm_client.py.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from pydantic import BaseModel, Field

_TOKENS_PATH = Path(__file__).resolve().parent.parent / "design_tokens.json"

_SECTION_RE = re.compile(
    r"===\s*login\.component\.(ts|html|css)\s*===\n(.*?)(?=\n===\s*login\.component\.|$)",
    re.DOTALL | re.IGNORECASE,
)

# Strip any leftover fences inside a section (double safety net)
_FENCE_RE = re.compile(r"```[a-zA-Z]*\n?|^```\s*$", re.IGNORECASE | re.MULTILINE)


# ── Pydantic v2 model ─────────────────────────────────────────────────────────

class ValidationResult(BaseModel):
    is_valid: bool = Field(description="True when all checks pass.")
    errors: list[str] = Field(
        default_factory=list,
        description="Human-readable list of all validation errors found.",
    )


# ── HTML tag balance checker ──────────────────────────────────────────────────

class _TagBalanceChecker(HTMLParser):
    VOID_TAGS: frozenset = frozenset({
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    })

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.balance_errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() not in self.VOID_TAGS:
            self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.VOID_TAGS:
            return
        if not self.stack:
            self.balance_errors.append(f"Unexpected closing </{tag}> — stack empty.")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.balance_errors.append(
                f"HTML mismatch: expected </{self.stack[-1]}>, got </{tag}>."
            )

    def finalize(self) -> list[str]:
        if self.stack:
            self.balance_errors.append(
                f"Unclosed tags: {', '.join(f'<{t}>' for t in self.stack)}"
            )
        return self.balance_errors


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_section_fences(code: str) -> str:
    """Strip residual markdown fences from within a code section."""
    return _FENCE_RE.sub("", code).strip()


def _parse_sections(raw_code: str) -> dict[str, str]:
    """Extract and fence-strip ts / html / css sections from raw LLM output."""
    sections: dict[str, str] = {"ts": "", "html": "", "css": ""}
    for match in _SECTION_RE.finditer(raw_code):
        ext  = match.group(1).lower()
        code = _strip_section_fences(match.group(2))
        if ext in sections:
            sections[ext] = code
    return sections


# ── Individual checks ─────────────────────────────────────────────────────────

def _check_sections_present(sections: dict[str, str]) -> list[str]:
    return [
        f"Missing section: === login.component.{ext} === not found or empty."
        for ext in ("ts", "html", "css")
        if not sections[ext]
    ]


def _check_design_tokens(sections: dict[str, str], tokens: dict) -> list[str]:
    """Regex scan — design token values must appear in CSS or HTML."""
    combined = sections["css"] + "\n" + sections["html"]
    checks = [
        (tokens["primary_color"],
         f"Primary color {tokens['primary_color']} must appear in CSS or HTML."),
        (tokens["border_radius"],
         f'border-radius value "{tokens["border_radius"]}" must appear in CSS.'),
        (tokens["font_family"],
         f'font-family "{tokens["font_family"]}" must appear in CSS.'),
    ]
    return [
        f"Design token missing — {msg}"
        for value, msg in checks
        if not re.search(re.escape(value), combined, re.IGNORECASE)
    ]


def _check_bracket_balance(code: str, label: str) -> list[str]:
    errors: list[str] = []
    pairs = {"}": "{", ")": "(", "]": "["}
    stack: list[str] = []
    for i, ch in enumerate(code):
        if ch in ("{", "(", "["):
            stack.append(ch)
        elif ch in ("}", ")", "]"):
            if not stack:
                errors.append(f"[{label}] Unexpected '{ch}' at pos {i} — stack empty.")
            elif stack[-1] != pairs[ch]:
                errors.append(
                    f"[{label}] Mismatch at pos {i}: expected '{pairs[ch]}' got '{ch}'."
                )
            else:
                stack.pop()
    if stack:
        errors.append(f"[{label}] Unclosed: {stack}")
    return errors


def _check_angular_structure(ts_code: str) -> list[str]:
    errors: list[str] = []
    if "@Component" not in ts_code:
        errors.append("TypeScript: @Component decorator is missing.")
    if not re.search(r"export\s+class\s+\w+", ts_code):
        errors.append("TypeScript: 'export class <Name>' is missing.")
    return errors


def _check_html_balance(html_code: str) -> list[str]:
    checker = _TagBalanceChecker()
    try:
        checker.feed(html_code)
        return checker.finalize()
    except Exception as exc:
        return [f"HTML parse error: {exc}"]


# ── Public API ────────────────────────────────────────────────────────────────

def validate_component(raw_code: str) -> ValidationResult:
    """
    Run all 6 checks on the generated component.

    Args:
        raw_code: Full raw LLM output (fences already stripped by llm_client).

    Returns:
        ValidationResult(is_valid=bool, errors=list[str])
    """
    tokens   = json.loads(_TOKENS_PATH.read_text(encoding="utf-8"))
    sections = _parse_sections(raw_code)
    errors: list[str] = []

    section_errors = _check_sections_present(sections)
    if section_errors:
        return ValidationResult(is_valid=False, errors=section_errors)

    errors.extend(_check_design_tokens(sections, tokens))
    errors.extend(_check_bracket_balance(sections["ts"],  label="TS"))
    errors.extend(_check_bracket_balance(sections["css"], label="CSS"))
    errors.extend(_check_angular_structure(sections["ts"]))
    errors.extend(_check_html_balance(sections["html"]))

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)
