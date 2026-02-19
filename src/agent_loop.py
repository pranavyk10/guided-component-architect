from src.generator import generate_component, fix_component, load_design_system
from src.validator import validate_all_files, flatten_errors, has_errors
from src.parser import parse_llm_output, validate_parse_result
from src.utils import sanitize_prompt, prompt_to_kebab, kebab_to_class_name, save_component


def run_agent(user_prompt: str) -> dict:
    """
    Agentic pipeline:
      1. Sanitize input
      2. Generate (3-file output)
      3. Parse into ts/html/css
      4. Validate each file + design tokens
      5. If invalid → Fixer Agent (once)
      6. Re-validate
      7. Save and return

    Returns full result dict for UI consumption.
    """

    # ── Step 1: Sanitize ────────────────────────────────────────────────
    clean_prompt, injection_warnings = sanitize_prompt(user_prompt)
    kebab_name  = prompt_to_kebab(clean_prompt)
    class_name  = kebab_to_class_name(kebab_name)
    design_system = load_design_system()

    attempt_log = []

    # ── Step 2: Generate ────────────────────────────────────────────────
    raw_output = generate_component(clean_prompt, design_system, class_name, kebab_name)
    parsed     = parse_llm_output(raw_output)
    parse_errs = validate_parse_result(parsed)

    if parse_errs:
        return _failure_result(
            injection_warnings, attempt_log,
            parse_errs, kebab_name, class_name
        )

    # ── Step 3: Validate attempt 1 ──────────────────────────────────────
    error_dict = validate_all_files(parsed, design_system)
    all_errors = flatten_errors(error_dict)

    attempt_log.append({
        "attempt": 1,
        "phase": "generate",
        "is_valid": not has_errors(error_dict),
        "errors": all_errors,
        "files": parsed,
    })

    if not has_errors(error_dict):
        # Valid on first attempt
        saved_paths = save_component(parsed, kebab_name)
        return _success_result(parsed, saved_paths, 1, attempt_log, injection_warnings, kebab_name, class_name)

    # ── Step 4: Fixer Agent (single retry) ──────────────────────────────
    fixed_raw    = fix_component(parsed, all_errors, design_system, class_name, kebab_name)
    fixed_parsed = parse_llm_output(fixed_raw)
    fix_parse_errs = validate_parse_result(fixed_parsed)

    if fix_parse_errs:
        return _failure_result(
            injection_warnings, attempt_log,
            fix_parse_errs, kebab_name, class_name
        )

    # ── Step 5: Re-validate ─────────────────────────────────────────────
    error_dict2  = validate_all_files(fixed_parsed, design_system)
    all_errors2  = flatten_errors(error_dict2)

    attempt_log.append({
        "attempt": 2,
        "phase": "fix",
        "is_valid": not has_errors(error_dict2),
        "errors": all_errors2,
        "files": fixed_parsed,
    })

    # ── Step 6: Save and return ──────────────────────────────────────────
    saved_paths = save_component(fixed_parsed, kebab_name)

    if not has_errors(error_dict2):
        return _success_result(fixed_parsed, saved_paths, 2, attempt_log, injection_warnings, kebab_name, class_name)
    else:
        # Still invalid after fix — output with warnings
        return {
            "code": fixed_parsed,
            "is_valid": False,
            "attempts": 2,
            "errors": all_errors2,
            "injection_warnings": injection_warnings,
            "saved_paths": saved_paths,
            "attempt_log": attempt_log,
            "kebab_name": kebab_name,
            "class_name": class_name,
        }


def _success_result(parsed, saved_paths, attempts, log, warnings, kebab_name, class_name):
    return {
        "code": parsed,
        "is_valid": True,
        "attempts": attempts,
        "errors": [],
        "injection_warnings": warnings,
        "saved_paths": saved_paths,
        "attempt_log": log,
        "kebab_name": kebab_name,
        "class_name": class_name,
    }


def _failure_result(warnings, log, errors, kebab_name, class_name):
    return {
        "code": {"ts": "", "html": "", "css": ""},
        "is_valid": False,
        "attempts": len(log),
        "errors": errors,
        "injection_warnings": warnings,
        "saved_paths": {},
        "attempt_log": log,
        "kebab_name": kebab_name,
        "class_name": class_name,
    }
