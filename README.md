# Guided Component Architect

Describe a UI in plain English. Get a ready-to-use Angular component back — TypeScript, HTML, and CSS — with your design system automatically enforced.


---

## What it does

You type something like *"a login card with glassmorphism effect"* and the pipeline:

1. Sends it to an LLM (via Groq) with your design tokens baked into the prompt
2. Parses the output into three separate files (`.ts`, `.html`, `.css`)
3. Runs a validator that checks syntax, HTML tag balance, bracket matching, and whether your design tokens actually appear in the code
4. If anything fails, a second LLM call fixes only the broken parts and the validator runs again
5. Saves the final files to `output_component/`

The whole thing runs in a Streamlit UI with a chat interface, so you can also do follow-up edits like *"now make the button full width"* and it carries the previous component as context.

---

## Agentic Loop Architecture

The pipeline is built as an agentic loop — a sequence of steps where the output of one stage feeds into the next, with a built-in self-correction cycle if something goes wrong.

```
User Input
    │
    ▼
[1] Sanitizer          utils.py — strips injection patterns, truncates to 500 chars
    │
    ▼
[2] Generator          generator.py — sends prompt + design tokens to Llama 3.3 70B via Groq
    │  raw LLM output
    ▼
[3] Parser             parser.py — extracts .ts / .html / .css sections from raw text
    │  parsed files
    ▼
[4] Validator          validator.py — 4 checks: TS syntax, HTML tags, CSS tokens, design system
    │
    ├── VALID ──────────────────────────────────────► Save to output_component/  ✅
    │
    └── INVALID
           │  errors passed verbatim
           ▼
       [5] Fixer        generator.py — second LLM call with original code + error list
           │  fixed output
           ▼
       [6] Parser + Validator (re-run)
           │
           ├── VALID ──────────────────────────────► Save to output_component/  ✅
           │
           └── INVALID ────────────────────────────► Save with warning, show errors in UI  ⚠️
```

**Why this structure matters:**

- The validator is completely separate from the LLM — it's pure Python with no AI calls. This means validation results are deterministic and can't be influenced by a model that's been given bad instructions.
- The fixer receives the *exact* error strings from the validator, not a vague "something went wrong" message. This makes the correction targeted — it doesn't redesign the component, it fixes only what failed.
- The loop runs at most twice (one generate + one fix). This keeps latency predictable and avoids infinite retry loops.
- Every attempt is logged to `attempt_log` in the result dict, which the Streamlit UI exposes in an expandable section so you can see what failed and what was corrected.


---
## Setup

**Requirements:** Python 3.10+, a free Groq API key from [console.groq.com](https://console.groq.com)

```bash
git clone https://github.com/YOUR_USERNAME/guided-component-architect
cd guided-component-architect

python -m venv .venv
.venv\Scripts\activate        # Windows
# or: source .venv/bin/activate  (Mac/Linux)

pip install -r requirements.txt
```

Copy the env file and add your key:
```bash
cp .env.example .env
# Open .env and paste your GROQ_API_KEY
```

Run it:
```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

---

## Project structure

```
src/
  agent_loop.py   — orchestrates the full pipeline end to end
  generator.py    — LLM calls for generation and fixing (Groq)
  validator.py    — checks syntax, HTML tags, brackets, and design token usage
  parser.py       — extracts ts/html/css sections from raw LLM output
  utils.py        — input sanitization, kebab-case naming, file saving

app.py            — Streamlit UI with chat input, tab view, download buttons
design_system.json — the token file the validator enforces against
output_component/ — generated files land here
```

---

## Design system

Defined in `design_system.json`. The validator checks that every generated component actually uses the tokens — not just mentions them in the prompt. If a component uses an unauthorized hex color or skips the font-family, it fails and gets sent back for correction.

Current tokens include primary color `#6366f1`, Inter font, glassmorphism values, card shadow, border radius, and spacing units.

---

## How the validation works

The validator runs four separate checks on each generated component:

- **TypeScript** — checks for `@Component`, `selector`, `templateUrl`, `styleUrls`, `export class`, and balanced brackets
- **HTML** — stack-based tag balance checker, catches unclosed and mismatched tags
- **CSS** — checks brace balance, font-family token, card shadow token
- **Design tokens** — scans combined HTML+CSS for primary color, border radius, and flags any hex color that isn't in the design system

If any check fails, the exact error messages (e.g. `[DESIGN_TOKEN] Missing primary-color — expected #6366f1`) get passed to a second LLM call that fixes only those issues without changing the rest of the component.

---

## Multi-turn editing

The chat interface supports follow-up prompts. When you send a second message, the pipeline appends the first 400 characters of the previously generated `.ts` file as context so the model knows what it's modifying. 

---

## Prompt injection handling

User input goes through `sanitize_prompt()` in `utils.py` before hitting the LLM. It scans for patterns like "ignore previous instructions", "act as", "you are now", and replaces them with `[REDACTED]`. Input is also truncated at 500 characters. Design token values are injected from the server-side JSON file, not from user input, so they can't be overridden through the chat.

The Streamlit UI also surfaces a warning banner if an injection attempt is detected and neutralized, so it's visible in the interface — not just silently handled in the backend.

---

## Two versions

| Branch | Model | How to run |
|---|---|---|
| `main` |  Groq (cloud) | Add `GROQ_API_KEY` to `.env`, run `streamlit run app.py` |
| `feat/local-ollama` | deepseek-coder:6.7b via Ollama (local) | Install Ollama, `ollama pull deepseek-coder:6.7b`, run `python main.py` |

The local version runs fully offline — no API key, no internet. Tradeoff is a ~4GB model download and slower generation. Both versions use the same design system enforcement and agentic loop logic.

---

## Assumptions

- Angular and Tailwind CSS are pre-installed in whatever project you copy the output files into
- The Groq free tier is sufficient — handles the structured output format reliably
- Generated components use `standalone: true` (Angular 14+); `FormsModule` and `CommonModule` need to be in the `imports` array if using reactive forms
- The pipeline performs one automatic fix attempt; if it still fails after that, the output is saved with a warning and the errors are shown in the UI
