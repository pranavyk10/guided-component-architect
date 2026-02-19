import re


def validate_ts(code: str) -> list[str]:
    errors = []
    if "@Component" not in code:
        errors.append("[SYNTAX] Missing @Component decorator.")
    if "selector:" not in code:
        errors.append("[SYNTAX] Missing selector in @Component.")
    if "templateUrl:" not in code:
        errors.append("[SYNTAX] Missing templateUrl — must use external HTML file.")
    if "styleUrls:" not in code:
        errors.append("[SYNTAX] Missing styleUrls — must use external CSS file.")
    if "export class" not in code:
        errors.append("[SYNTAX] Missing export class.")
    for open_b, close_b in [("{", "}"), ("(", ")"), ("[", "]")]:
        if code.count(open_b) != code.count(close_b):
            errors.append(f"[SYNTAX] Mismatched '{open_b}{close_b}': {code.count(open_b)} open vs {code.count(close_b)} close.")
    if "```" in code:
        errors.append("[FORMAT] Markdown fences detected in .ts file.")
    return errors


def validate_html(code: str) -> list[str]:
    errors = []
    if "```" in code:
        errors.append("[FORMAT] Markdown fences detected in .html file.")

    void_tags = {
        "input", "br", "hr", "img", "meta", "link",
        "area", "base", "col", "embed", "param",
        "source", "track", "wbr"
    }

    tag_pattern = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)(\s[^>]*)?>")
    stack = []

    for match in tag_pattern.finditer(code):
        is_closing = match.group(1) == "/"
        tag_name = match.group(2).lower()
        if tag_name in void_tags:
            continue
        if not is_closing:
            stack.append(tag_name)
        else:
            if not stack:
                errors.append(f"[HTML] Unexpected closing tag </{tag_name}> with no matching open tag.")
            elif stack[-1] == tag_name:
                stack.pop()
            else:
                errors.append(f"[HTML] Mismatched tag: expected </{stack[-1]}> but found </{tag_name}>.")
                while stack and stack[-1] != tag_name:
                    unclosed = stack.pop()
                    errors.append(f"[HTML] Unclosed <{unclosed}> tag.")
                if stack:
                    stack.pop()

    for unclosed in reversed(stack):
        errors.append(f"[HTML] Unclosed <{unclosed}> tag.")

    return errors


def validate_css(code: str, design_system: dict) -> list[str]:
    errors = []

    if "```" in code:
        errors.append("[FORMAT] Markdown fences detected in .css file.")

    if code.count("{") != code.count("}"):
        errors.append(
            f"[SYNTAX] Mismatched CSS braces: "
            f"{code.count('{')} open vs {code.count('}')} close."
        )

    font = design_system.get("font-family", "Inter")
    font_name = font.replace("'", "").replace('"', "").strip()
    #font_name = font_name.split(",").strip()

    if font_name and font_name.lower() not in code.lower():
        errors.append(
            f"[DESIGN_TOKEN] Missing font-family\n"
            f"  TOKEN: font-family\n"
            f"  EXPECTED: {font_name}\n"
            f"  MESSAGE: font-family token not applied in CSS"
        )

    shadow = design_system.get("card-shadow", "")
    if shadow and shadow not in code:
        errors.append(
            f"[DESIGN_TOKEN] Missing card-shadow\n"
            f"  TOKEN: card-shadow\n"
            f"  EXPECTED: {shadow}\n"
            f"  MESSAGE: card shadow token not used in CSS"
        )

    return errors


def validate_all_files(parsed: dict, design_system: dict) -> dict[str, list[str]]:
    return {
        "ts":     validate_ts(parsed.get("ts", "")),
        "html":   validate_html(parsed.get("html", "")),
        "css":    validate_css(parsed.get("css", ""), design_system),
        "design": validate_design_tokens(parsed, design_system),
    }


def validate_design_tokens(parsed: dict, design_system: dict) -> list[str]:
    errors = []
    combined = parsed.get("html", "") + "\n" + parsed.get("css", "")

    primary = design_system.get("primary-color", "")
    if primary and primary.lower() not in combined.lower():
        errors.append(
            f"[DESIGN_TOKEN] Missing primary_color\n"
            f"  TOKEN: primary-color\n"
            f"  EXPECTED: {primary}\n"
            f"  MESSAGE: primary color token not used in HTML/CSS"
        )

    allowed_colors = set()
    for v in design_system.values():
        if isinstance(v, str) and v.startswith("#"):
            allowed_colors.add(v.lower())

    found_colors = re.findall(r"#[0-9a-fA-F]{6}\b", combined)
    for color in found_colors:
        if color.lower() not in allowed_colors:
            errors.append(
                f"[DESIGN_TOKEN] Unauthorized color '{color}'\n"
                f"  TOKEN: color\n"
                f"  EXPECTED: one of {sorted(allowed_colors)}\n"
                f"  MESSAGE: hex color not in design system"
            )

    border_radius = design_system.get("border-radius", "8px")
    if border_radius and border_radius not in combined:
        errors.append(
            f"[DESIGN_TOKEN] Missing border-radius\n"
            f"  TOKEN: border-radius\n"
            f"  EXPECTED: {border_radius}\n"
            f"  MESSAGE: border radius token not used in HTML/CSS"
        )

    return errors


def flatten_errors(error_dict: dict[str, list[str]]) -> list[str]:
    all_errors = []
    for errs in error_dict.values():
        all_errors.extend(errs)
    return all_errors


def has_errors(error_dict: dict[str, list[str]]) -> bool:
    return any(len(v) > 0 for v in error_dict.values())
