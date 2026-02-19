# Guided Component Architect — Local Version (deepseek-coder:6.7b via Ollama)

This is the offline branch of Guided Component Architect. It runs the same agentic pipeline as the `main` branch but uses **deepseek-coder:6.7b running locally via Ollama** — no API key, no internet, no cost.

For the Groq cloud version (easier to run, no model download), see the `main` branch.

---

## What it does

Same pipeline as the main version — describe a UI, get back a 3-file Angular component (`.ts`, `.html`, `.css`) with your design system enforced. The difference is everything runs on your machine.

---

## Agentic Loop Architecture

```
User Input
    │
    ▼
[1] Sanitizer      main.py — strips injection patterns, truncates to 500 chars
    │
    ▼
[2] Generator      agents/generator.py — calls deepseek-coder:6.7b via Ollama
    │  raw output (markdown fences stripped automatically)
    ▼
[3] Validator      agents/validator.py — 6 checks, zero LLM involvement
    │
    ├── VALID ─────────────────────────────► Write to output_component/  ✅
    │
    └── INVALID
           │  exact error strings passed to fixer
           ▼
       [4] Fixer   agents/fixer.py — second Ollama call with code + errors
           │
           ▼
       [5] Validator (re-run)
           │
           ├── VALID ──────────────────────► Write to output_component/  ✅
           └── INVALID ────────────────────► Save raw output + exit(2)   ⚠️
```

**Key design decisions:**

- Markdown fences (`\`\`\`typescript`, `\`\`\`css`) are stripped automatically in `llm_client.py` — deepseek-coder adds them even when told not to, so stripping happens as a post-processing step after every LLM call, not in the prompt.
- The validator is pure Python — regex, bracket counter, HTML stack parser. No LLM call, fully deterministic.
- The fixer receives the exact validator error strings verbatim so the correction is surgical, not a full regeneration.
- One retry maximum. Predictable latency.

---

## Setup

**Requirements:** Python 3.10+, Ollama installed

### Step 1 — Install Ollama
Download from [ollama.com/download](https://ollama.com/download) (Windows / Mac / Linux)

### Step 2 — Pull the model (~3.8 GB, one time)
```bash
ollama pull deepseek-coder:6.7b
```

### Step 3 — Start Ollama server
```bash
ollama serve
```
Keep this terminal open. Ollama runs at `http://localhost:11434`.

### Step 4 — Set up the project
```bash
cd guided-component-architect   # this folder

python -m venv .venv
.venv\Scripts\activate          # Windows
# or: source .venv/bin/activate  (Mac/Linux)

pip install -r requirements.txt
```

### Step 5 — Copy env file
```bash
cp .env.example .env
# No edits needed — defaults point to localhost:11434
```

### Step 6 — Run
```bash
python main.py
```

---

## Example session

```
============================================================
   Guided Component Architect
   Model : deepseek-coder:6.7b  (local via Ollama)
   API   : http://localhost:11434/v1  (no internet needed)
============================================================

Describe the component: A login card with glassmorphism effect

[Generator] Calling deepseek-coder:6.7b...
[Generator] Response received.

[Validator] Running checks...
[Validator] ✅  All checks passed on first attempt.

✅  Files written to output_component/:
    output_component/login.component.ts
    output_component/login.component.html
    output_component/login.component.css
```

---

## Project structure

```
agents/
  __init__.py     — package marker
  generator.py    — builds system prompt with design tokens, calls Ollama
  validator.py    — 6-check static linter (Pydantic v2, no LLM)
  fixer.py        — sends failed code + errors back to Ollama for correction

llm_client.py     — OpenAI-SDK client pointed at http://localhost:11434/v1
                    strips markdown fences from every response
prompts.py        — SYSTEM_GENERATOR_PROMPT and FIXER_PROMPT_TEMPLATE
design_tokens.json — immutable design system (primary color, font, shadow, etc.)
main.py           — pipeline entry point
requirements.txt
.env.example
output_component/ — generated Angular files land here (git-ignored)
```

---

## Validation checks

Six checks run on every generated component — none of them use the LLM:

1. All three sections present (`.ts`, `.html`, `.css`)
2. Primary color `#6366f1` appears in CSS or HTML
3. `border-radius: 8px` appears in CSS
4. `font-family: Inter` appears in CSS
5. Balanced `{}`, `()`, `[]` in TypeScript and CSS
6. `@Component` decorator and `export class` present in TypeScript
7. HTML tag balance via stack parser

---

## Design tokens (`design_tokens.json`)

```json
{
  "primary_color": "#6366f1",
  "secondary_color": "#22c55e",
  "border_radius": "8px",
  "font_family": "Inter",
  "card_padding": "24px",
  "shadow": "0 10px 25px rgba(0,0,0,0.15)"
}
```

Loaded by the system at startup. User cannot override these through the prompt.

---

## Prompt injection handling

- All design token values go into the **system role** message, not the user message
- `_sanitize_input()` in `main.py` strips 10 known injection trigger phrases and truncates input at 500 characters
- The validator uses no LLM — it cannot be socially engineered
- Generated code is only written to disk, never executed

---

## Compared to main branch

| | `main` (Groq) | `feat/local-ollama` (this branch) |
|---|---|---|
| Model |  Groq | deepseek-coder:6.7b via Ollama |
| Internet required | Yes (API call) | No |
| API key needed | Yes (free) | No |
| UI | Streamlit web app | Terminal (CLI) |
| Setup time | ~2 minutes | ~10 min + 4GB download |
| Generation speed | Fast (~5s) | Depends on hardware |

---

## Assumptions

- Angular and Tailwind CSS are pre-installed in the project where you use the output files
- Python 3.10+ is available
- Hardware recommendation: 8GB RAM minimum; 16GB preferred for comfortable generation speed
- Generated components are Angular 21 compatible (`standalone: true` required — add it manually if the model omits it)
