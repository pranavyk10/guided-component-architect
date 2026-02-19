import re


def parse_llm_output(raw: str) -> dict[str, str]:
    """
    Parses LLM output into 3 separate files.
    Expected format:
        === component.ts ===
        <code>
        === component.html ===
        <code>
        === component.css ===
        <code>

    Returns: {"ts": "...", "html": "...", "css": "..."}
    """
    result = {"ts": "", "html": "", "css": ""}

    patterns = {
        "ts":   r"===\s*component\.ts\s*===\s*(.*?)(?====\s*component\.html|$)",
        "html": r"===\s*component\.html\s*===\s*(.*?)(?====\s*component\.css|$)",
        "css":  r"===\s*component\.css\s*===\s*(.*?)$",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            # Strip any accidental markdown fences
            content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
            result[key] = content.strip()

    return result


def validate_parse_result(parsed: dict) -> list[str]:
    """Check that all 3 files were successfully parsed."""
    errors = []
    if not parsed.get("ts"):
        errors.append("[PARSE] component.ts section missing or empty.")
    if not parsed.get("html"):
        errors.append("[PARSE] component.html section missing or empty.")
    if not parsed.get("css"):
        errors.append("[PARSE] component.css section missing or empty.")
    return errors
