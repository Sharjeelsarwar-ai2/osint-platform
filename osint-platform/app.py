"""NEXUS OSINT Intelligence — v3 thin composition entry point.

v3 layout (NOT the old single-column scroll):
  1. Persistent AGENT DOCK in the Streamlit sidebar — 5 large SVG character
     portraits, each with name/role/catchphrase and REAL status/tools.
  2. Top COMMAND BAR (full width) — brand, section labels, live status.
  3. Dashboard hero strip + operation-status bento (2-column Streamlit grid).
  4. Metrics bento row.
  5. Dashboard split: left = Launch form + Mission Control (idle) ;
     right = Live Activity panel (real events only, or honest standby).
  6. Workstations (during/after a run) and Report (full width, below).

Presentation lives in ui/ (styles, components, avatars, report).
Backend is unchanged: agents/orchestrator.py pipeline, Groq tools, PDF/JSON.
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

st.set_page_config(
    page_title="NEXUS | OSINT Intelligence",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

from agents.orchestrator import render_mission_control, render_saved_agent_workstations, run_osint_audit
from agents.tools import TOOL_REGISTRY
from config.settings import AGENT_PROFILES, GROQ_API_KEY, MODEL_NAME
from ui.components import (
    activity_panel_html,
    hero_html,
    metrics_html,
    render_agent_dock,
    render_command_bar,
    render_idle_state as _ui_render_idle_state,
    status_bento_html,
)
from ui.styles import get_css

AGENT_ORDER = ["aria", "raven", "vulcan", "cipher", "oracle"]


# Backwards-compatible names used by older tests / callers.
def get_css():
    from ui.styles import get_css as _get_css

    return _get_css()


def render_header():
    """Render the hero: 'Track the invisible. / Expose the truth.' via ui.components.hero_html."""
    import streamlit as _st

    _st.markdown(hero_html(MODEL_NAME, "STANDBY"), unsafe_allow_html=True)


def render_idle_state():
    """Render the idle panel: 'TEAM ON STANDBY' — nothing is simulated."""
    _ui_render_idle_state()


def render_live_team_board():
    """v3: the team board IS the sidebar dock (nexus_latest_activity /
    nexus_operation drive real status; on idle agents show STANDBY).
    This alias keeps old callers rendering the dock instead of silently
    rendering nothing."""
    activity = st.session_state.get("nexus_latest_activity", {})
    operation = st.session_state.get("nexus_operation", {})
    render_agent_dock(AGENT_PROFILES, activity, operation)


def render_metrics():
    import streamlit as _st

    _st.markdown(metrics_html(AGENT_PROFILES, len(TOOL_REGISTRY), MODEL_NAME), unsafe_allow_html=True)


def get_api_key():
    key = GROQ_API_KEY or __import__("os").environ.get("GROQ_API_KEY", "")
    if key:
        return key
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        return ""


def main():
    st.markdown(get_css(), unsafe_allow_html=True)

    # 1. Persistent agent dock (sidebar) — characters first, always visible.
    activity0 = st.session_state.get("nexus_latest_activity", {})
    operation0 = st.session_state.get("nexus_operation", {})
    board_status = "● LIVE — AGENTS WORKING" if operation0.get("status") == "running" else "STANDBY"
    render_agent_dock(AGENT_PROFILES, activity0, operation0)

    # 2. Top command bar.
    render_command_bar(board_status)

    # 3. Dashboard hero + operation-status bento (not a full-page hero scroll).
    hero_col, status_col = st.columns([2, 1], gap="medium")
    with hero_col:
        st.markdown(hero_html(MODEL_NAME, board_status), unsafe_allow_html=True)
    with status_col:
        st.markdown(
            status_bento_html(activity0, operation0, AGENT_PROFILES),
            unsafe_allow_html=True,
        )

    # 4. Metrics bento row.
    st.markdown(metrics_html(AGENT_PROFILES, len(TOOL_REGISTRY), MODEL_NAME), unsafe_allow_html=True)

    # 5. Dashboard split: Operations (left) + Live Activity (right).
    ops_col, activity_col = st.columns([2, 1], gap="medium")
    with activity_col:
        st.markdown(
            activity_panel_html(
                st.session_state.get("nexus_global_activity", []),
                operation0,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="dash-card"><span class="section-kicker">HOW TO READ THIS BOARD</span>'
            "<h3>Characters = real agents</h3>"
            "<p>Dock characters pulse while their agent works, glow when it "
            "finishes, and bob gently on standby. Their status and tool counts "
            "come from the actual scan — never from a simulation.</p></div>",
            unsafe_allow_html=True,
        )

    launch = False
    target = ""
    target_type = "Domain"
    with ops_col:
        st.markdown(
            '<div class="section-heading"><div><span class="section-kicker">OPERATIONS</span>'
            '<h2>Launch a real scan</h2></div><span>Use only targets you are authorized to assess.</span></div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            with st.form("nexus_target_form"):
                col_target, col_type, col_button = st.columns([5, 1.6, 1.7])
                with col_target:
                    target = st.text_input("Target", placeholder="example.com, 203.0.113.10, or Acme Corp")
                with col_type:
                    target_type = st.selectbox("Target type", ["Domain", "IP Address", "Company"])
                with col_button:
                    launch = st.form_submit_button("▶ RUN INTELLIGENCE SCAN", use_container_width=True)
        if not get_api_key():
            st.warning("Groq API key required. Set GROQ_API_KEY in the environment or in Streamlit secrets to enable agent runs.")
        # Always-visible Mission Control on idle (left column). During a
        # scan the orchestrator renders the live slot itself; after a scan
        # render_saved_agent_workstations renders it again below.
        if not st.session_state.get("nexus_latest_activity"):
            st.markdown(
                '<div class="section-heading"><div><span class="section-kicker">MISSION CONTROL</span>'
                '<h2>Operation board — always visible</h2></div><span>0% on standby · lights up during a real scan</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(render_mission_control(), unsafe_allow_html=True)

    activity_rendered = False
    if launch:
        if not target.strip():
            st.error("Enter a domain, IP address, or company name before starting the scan.")
        elif not get_api_key():
            st.error("The scan was not started because no Groq API key is configured.")
        else:
            activity_rendered = True
            started = time.time()
            st.session_state["nexus_latest_report"] = None
            try:
                results = run_osint_audit(target.strip(), target_type.lower())
                st.session_state["nexus_latest_report"] = {
                    "target": target.strip(),
                    "target_type": target_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "elapsed": time.time() - started,
                    "results": results,
                }
            except Exception as exc:
                st.error(f"The scan could not be completed: {type(exc).__name__}: {exc}")

    if not activity_rendered:
        render_saved_agent_workstations()

    if (
        not activity_rendered
        and not st.session_state.get("nexus_latest_activity")
        and not st.session_state.get("nexus_latest_report")
    ):
        render_idle_state()

    latest_report = st.session_state.get("nexus_latest_report")
    if latest_report:
        from ui.report import render_report

        render_report(latest_report, AGENT_PROFILES, MODEL_NAME)

    st.markdown(
        '<div class="nx-footer"><span>NEXUS · LIVE INTELLIGENCE BOARD</span>'
        '<span>PASSIVE OSINT · REAL AGENTS · VERIFY SOURCES BEFORE ACTION</span></div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
