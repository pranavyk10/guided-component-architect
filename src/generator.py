import json
import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


import streamlit as st
import os

api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)
MODEL_NAME = "llama-3.3-70b-versatile"


def load_design_system(path: str = "design_system.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _call_llm(system_msg: str, user_msg: str) -> str:
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg}
        ],
        model=MODEL_NAME,
        temperature=0.2,
        max_tokens=3000,
        top_p=0.9
    )
    return response.choices[0].message.content.strip()


# ── GENERATOR PROMPT ────────────────────────────────────────────────────────

GENERATOR_SYSTEM = """You are an Angular component code generator.
Output ONLY raw code in EXACTLY this format — no markdown, no backticks, no explanations:

=== component.ts ===
<raw TypeScript code here>

=== component.html ===
<raw HTML template here>

=== component.css ===
<raw CSS styles here>

Rules:
- component.ts must import Component from @angular/core
- component.ts must use @Component with selector, templateUrl, styleUrls
- component.ts must have export class
- component.html must be valid HTML with all tags closed
- component.css must reference font-family and use design tokens
- NO inline templates or inline styles in .ts file
- NO markdown fences anywhere"""


def build_generator_prompt(user_prompt: str, design_system: dict, class_name: str, kebab_name: str) -> str:
    tokens = json.dumps(design_system, indent=2)
    return f"""Design System Tokens — use ONLY these values, no other hex colors or fonts:
{tokens}

Component naming:
- selector: app-{kebab_name}
- class name: {class_name}
- templateUrl: ./{kebab_name}.component.html
- styleUrls: ['./{kebab_name}.component.css']

Generate the Angular component for: "{user_prompt}"

Apply glassmorphism, spacing, and shadows from the design tokens above.
The .html must use only colors and font from the design system.
The .css must set font-family to {design_system.get('font-family', 'Inter')}.
"""


# ── FIXER PROMPT ─────────────────────────────────────────────────────────────

FIXER_SYSTEM = """You are an Angular component repair agent.
You receive broken Angular component code and a list of validation errors.
Your ONLY job is to fix the listed errors.
Do NOT redesign the UI. Do NOT change component behavior.
Do NOT change the component name or selector.
Return the corrected files in EXACTLY this format — no markdown, no backticks:

=== component.ts ===
<corrected TypeScript code>

=== component.html ===
<corrected HTML template>

=== component.css ===
<corrected CSS styles>"""


def build_fixer_prompt(
    previous_files: dict,
    errors: list[str],
    design_system: dict,
    class_name: str,
    kebab_name: str
) -> str:
    tokens = json.dumps(design_system, indent=2)
    error_block = "\n".join(errors)
    return f"""Design System Tokens (enforced — do not deviate):
{tokens}

Component naming:
- selector: app-{kebab_name}
- class name: {class_name}

=== PREVIOUS component.ts ===
{previous_files.get('ts', '')}

=== PREVIOUS component.html ===
{previous_files.get('html', '')}

=== PREVIOUS component.css ===
{previous_files.get('css', '')}

=== VALIDATION ERRORS TO FIX ===
{error_block}

Fix ONLY the above errors. Keep all UI structure and behavior intact.
"""


def generate_component(user_prompt: str, design_system: dict, class_name: str, kebab_name: str) -> str:
    user_msg = build_generator_prompt(user_prompt, design_system, class_name, kebab_name)
    return _call_llm(GENERATOR_SYSTEM, user_msg)


def fix_component(previous_files: dict, errors: list[str], design_system: dict, class_name: str, kebab_name: str) -> str:
    user_msg = build_fixer_prompt(previous_files, errors, design_system, class_name, kebab_name)
    return _call_llm(FIXER_SYSTEM, user_msg)
