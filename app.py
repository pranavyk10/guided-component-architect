import streamlit as st
import json
from src.agent_loop import run_agent

st.set_page_config(
    page_title="Guided Component Architect",
    page_icon="🧩",
    layout="wide"
)

st.title("🧩 Guided Component Architect")
st.caption("Natural language → Angular component (TS + HTML + CSS) with design system enforcement.")

with st.sidebar:
    st.header("🎨 Active Design System")
    with open("design_system.json") as f:
        design_system = json.load(f)
    st.json(design_system)
    st.divider()
    st.caption("Generated code strictly enforces these tokens.")

# ── Session state init ──────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "last_files" not in st.session_state:
    st.session_state.last_files = {}
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "gen_id" not in st.session_state:
    st.session_state.gen_id = 0

# ── Chat history display ────────────────────────────────────────────────────
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ── Chat input ──────────────────────────────────────────────────────────────
user_input = st.chat_input("Describe your component — e.g. 'A login card with glassmorphism effect'")

if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})

    # Multi-turn: include last files as context
    full_prompt = user_input
    if st.session_state.last_files:
        ts_snippet = st.session_state.last_files.get("ts", "")[:400]
        full_prompt = (
            f"{user_input}. "
            f"Extend or modify this existing component:\n\n{ts_snippet}"
        )

    with st.spinner("🔄 Running agentic pipeline..."):
        result = run_agent(full_prompt)

    # Save result and increment gen_id in session state
    st.session_state.last_result = result
    st.session_state.last_files = result["code"]
    st.session_state.gen_id += 1

    status_msg = (
        "✅ Valid 3-file component!" if result["is_valid"]
        else f"⚠️ Generated with errors after {result['attempts']} attempt(s)."
    )
    st.session_state.history.append({"role": "assistant", "content": status_msg})
    st.rerun()

# ── Result display (persists across reruns) ─────────────────────────────────
if st.session_state.last_result:
    result = st.session_state.last_result
    gen_id = st.session_state.gen_id
    files  = result["code"]
    kebab  = result.get("kebab_name", "component")

    # ── Injection warnings ──────────────────────────────────────────────
    if result["injection_warnings"]:
        st.warning("⚠️ Prompt injection attempt detected and neutralized.")
        for w in result["injection_warnings"]:
            st.code(w)

    # ── Metrics row ─────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Attempts",  result["attempts"])
    col2.metric("Status",    "✅ Valid" if result["is_valid"] else "⚠️ Invalid")
    col3.metric("Component", kebab)
    col4.metric("Class",     result.get("class_name", "—"))

    # ── Agentic loop log ────────────────────────────────────────────────
    with st.expander("🔍 Agentic Loop Log", expanded=False):
        for log in result["attempt_log"]:
            status = "✅ Passed" if log["is_valid"] else "❌ Failed"
            st.markdown(f"**Attempt {log['attempt']} ({log['phase']})** — {status}")
            if log["errors"]:
                for e in log["errors"]:
                    st.error(e)
            st.divider()

    # ── Remaining errors ────────────────────────────────────────────────
    if not result["is_valid"] and result["errors"]:
        st.error("⛔ Unresolved validation errors after fixer agent:")
        for e in result["errors"]:
            st.code(e)

    # ── 3-tab file output ────────────────────────────────────────────────
    if any(files.values()):
        st.subheader("📄 Generated Component Files")
        tab_ts, tab_html, tab_css = st.tabs([
            f"📘 {kebab}.component.ts",
            f"📄 {kebab}.component.html",
            f"🎨 {kebab}.component.css"
        ])

        with tab_ts:
            st.code(files.get("ts", ""), language="typescript")
            st.download_button(
                label="⬇️ Download .ts",
                data=files.get("ts", ""),
                file_name=f"{kebab}.component.ts",
                mime="text/plain",
                key=f"download_ts_{gen_id}"
            )

        with tab_html:
            st.code(files.get("html", ""), language="html")
            st.download_button(
                label="⬇️ Download .html",
                data=files.get("html", ""),
                file_name=f"{kebab}.component.html",
                mime="text/plain",
                key=f"download_html_{gen_id}"
            )

        with tab_css:
            st.code(files.get("css", ""), language="css")
            st.download_button(
                label="⬇️ Download .css",
                data=files.get("css", ""),
                file_name=f"{kebab}.component.css",
                mime="text/plain",
                key=f"download_css_{gen_id}"
            )

        # ── Saved paths ──────────────────────────────────────────────────
        if result.get("saved_paths"):
            with st.expander("💾 Saved to output_component/", expanded=False):
                for k, path in result["saved_paths"].items():
                    st.code(path)
