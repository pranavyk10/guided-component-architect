"""
prompts.py
==========
LLM prompt templates tuned for deepseek-coder:6.7b via Ollama.

Tuning notes:
  - deepseek-coder ignores "no markdown fences" — handled in llm_client.py instead.
  - Inline style for primary color is more reliable than Tailwind arbitrary values
    for local 6.7B models, so we explicitly instruct both approaches.
  - Token values are interpolated at runtime from design_tokens.json.
"""


SYSTEM_GENERATOR_PROMPT = """\
You are an Angular component code generator. Output raw Angular code only.

OUTPUT — output EXACTLY these three sections and nothing else:

=== login.component.ts ===
<typescript code>

=== login.component.html ===
<html template code>

=== login.component.css ===
<css code>

MANDATORY RULES:
1. No explanation. No text outside the three sections.
2. TypeScript MUST contain:
     @Component decorator
     export class LoginComponent
     selector: 'app-login'
     templateUrl: './login.component.html'
     styleUrls: ['./login.component.css']
3. Use Tailwind CSS classes in the HTML template.
4. Use EXACTLY these design token values (copy verbatim):
     Primary color   : {primary_color}
     Secondary color : {secondary_color}
     Border radius   : {border_radius}
     Font family     : {font_family}
     Card padding    : {card_padding}
     Box shadow      : {shadow}
5. In the CSS file write a .card rule with EXACTLY:
     font-family: {font_family}, sans-serif;
     border-radius: {border_radius};
     padding: {card_padding};
     box-shadow: {shadow};
6. The primary button MUST use the primary color via inline style:
     style="background-color:{primary_color}"
   AND in CSS write:
     .btn-primary {{ background-color: {primary_color}; }}
7. All {{ }}, ( ), [ ] must be balanced.
"""


FIXER_PROMPT_TEMPLATE = """\
The Angular component below FAILED validation. Fix all listed errors.

ERRORS:
{error_list}

ORIGINAL CODE:
{original_code}

Return the FULL corrected component in this EXACT format:

=== login.component.ts ===
<corrected typescript>

=== login.component.html ===
<corrected html>

=== login.component.css ===
<corrected css>

RULES — fix ALL errors above:
- No explanation. No text outside the three sections.
- TypeScript MUST have @Component and export class LoginComponent.
- CSS MUST contain all four of these lines exactly:
    font-family: {font_family}, sans-serif;
    border-radius: {border_radius};
    padding: {card_padding};
    box-shadow: {shadow};
- CSS MUST also contain:
    background-color: {primary_color};
- HTML button MUST have:
    style="background-color:{primary_color}"
- All brackets must be balanced.
"""
