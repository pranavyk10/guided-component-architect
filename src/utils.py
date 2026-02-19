import os
import re

INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore above",
    r"disregard.*instructions",
    r"you are now",
    r"act as",
    r"pretend.*you",
    r"forget.*instructions",
    r"new instruction",
    r"system:",
    r"<\|.*\|>",
    r"\[INST\]",
    r"###\s*instruction",
    r"you are a senior",
    r"your job is to",
    r"return only",
    r"do not produce explanations",
]

def sanitize_prompt(user_input: str) -> tuple[str, list[str]]:
    warnings = []
    cleaned = user_input
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, user_input, re.IGNORECASE):
            warnings.append(f"Blocked suspicious pattern: '{pattern}'")
            cleaned = re.sub(pattern, "[REDACTED]", cleaned, flags=re.IGNORECASE)
    if len(cleaned) > 500:
        cleaned = cleaned[:500]
        warnings.append("Prompt truncated to 500 characters.")
    return cleaned.strip(), warnings


def prompt_to_kebab(user_prompt: str) -> str:
    """Convert natural language prompt to kebab-case component name."""
    stop_words = {"a", "an", "the", "with", "and", "for", "of", "in", "on", "at", "to"}
    words = re.sub(r"[^a-zA-Z0-9\s]", "", user_prompt).lower().split()
    filtered = [w for w in words if w not in stop_words][:4]
    return "-".join(filtered) if filtered else "app-component"


def kebab_to_class_name(kebab: str) -> str:
    """Convert kebab-case to PascalCase Angular class name."""
    return "".join(word.capitalize() for word in kebab.split("-")) + "Component"


def save_component(files: dict, kebab_name: str) -> dict[str, str]:
    """
    Save multi-file component output.
    files = {"ts": "...", "html": "...", "css": "..."}
    Returns dict of saved paths.
    """
    out_dir = "output_component"
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    ext_map = {"ts": "ts", "html": "html", "css": "css"}
    for key, ext in ext_map.items():
        filename = f"{kebab_name}.component.{ext}"
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(files.get(key, ""))
        paths[key] = filepath
    return paths
