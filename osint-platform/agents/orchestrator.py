import html
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.tools import GROQ_TOOL_DEFINITIONS, execute_tool
from config.settings import AGENT_PROFILES
from utils.groq_client import run_agent_with_tools


PIPELINE = [
    ("aria", "domain_recon", 3),
    ("raven", "threat_intel", 2),
    ("vulcan", "attack_surface", 2),
    ("cipher", "email_osint", 1),
    ("oracle", "final_report", 1),
]

STATUS_LABELS = {
    "queued": "QUEUED",
    "deploying": "INITIALIZING",
    "thinking": "ANALYZING",
    "executing": "RUNNING TOOL",
    "complete": "COMPLETE",
    "error": "NEEDS ATTENTION",
}

EVENT_LABELS = {
    "system": "SYS",
    "thinking": "LLM",
    "tool_call": "EXEC",
    "tool_result": "DATA",
    "final": "DONE",
    "error": "ERR",
}


def _save_agent_state(agent_key, status, activity_log, elapsed=None):
    saved = dict(st.session_state.get("nexus_latest_activity", {}))
    saved[agent_key] = {
        "status": status,
        "activity_log": list(activity_log),
        "elapsed": elapsed,
    }
    st.session_state["nexus_latest_activity"] = saved


def render_saved_agent_workstations():
    """Re-display the last run's agent windows after ordinary Streamlit reruns."""
    saved = st.session_state.get("nexus_latest_activity", {})
    if not saved:
        return
    st.markdown(
        '<div class="section-heading"><div><span>01 / LAST OPERATION</span>'
        '<h2>Agent workstations</h2></div><span>Activity history is retained for this session</span></div>',
        unsafe_allow_html=True,
    )
    left_column, right_column = st.columns(2, gap="medium")
    for index, (agent_key, _, _) in enumerate(PIPELINE):
        record = saved.get(agent_key, {})
        column = left_column if index % 2 == 0 else right_column
        column.markdown(
            render_agent_workstation(
                agent_key,
                record.get("status", "queued"),
                record.get("activity_log", []),
                record.get("elapsed"),
            ),
            unsafe_allow_html=True,
        )


def _escape(value):
    return html.escape(str(value), quote=True)


def _format_tool_call(name, args):
    args = args if isinstance(args, dict) else {}
    for key in ("domain", "url", "ip_address", "query", "company"):
        if args.get(key):
            return f"{name} · {str(args[key])[:72]}"
    if args:
        first_key, first_value = next(iter(args.items()))
        return f"{name} · {first_key}: {str(first_value)[:60]}"
    return f"{name} · no arguments"


def render_agent_workstation(agent_key, status="queued", activity_log=None, elapsed=None):
    """Render one persistent agent console and its complete scrollable event history."""
    agent = AGENT_PROFILES[agent_key]
    accent = agent.get("color", "#43c6e8")
    activity_log = activity_log or []
    status_label = STATUS_LABELS.get(status, "INITIALIZING")
    latest_activity = activity_log[-1]["text"] if activity_log else "Waiting for the orchestration queue."
    elapsed_text = f"{elapsed:.1f}s" if elapsed is not None else "—"

    events = []
    for event in activity_log:
        event_type = event.get("type", "system")
        event_label = EVENT_LABELS.get(event_type, "LOG")
        events.append(
            '<div class="agent-event">'
            '<time>' + _escape(event.get("time", "")) + '</time>'
            '<span class="event-tag event-' + _escape(event_type) + '">' + _escape(event_label) + '</span>'
            '<span class="event-message">' + _escape(event.get("text", "")) + '</span>'
            '</div>'
        )

    if not events:
        events.append(
            '<div class="agent-empty">No activity yet. This specialist is standing by.</div>'
        )

    return (
        '<article class="agent-console status-' + _escape(status) + '" style="--agent-accent:' + _escape(accent) + '">'
        '<div class="agent-console-topline"></div>'
        '<header class="agent-console-header">'
        '<div class="agent-monogram">' + _escape(agent.get("name", agent_key)[:2]) + '</div>'
        '<div class="agent-heading">'
        '<div class="agent-name-row"><h3>' + _escape(agent.get("name", agent_key)) + '</h3>'
        '<span class="agent-status"><i></i>' + _escape(status_label) + '</span></div>'
        '<p>' + _escape(agent.get("role", "Specialist agent")) + '</p>'
        '</div>'
        '<div class="agent-duration">' + _escape(elapsed_text) + '</div>'
        '</header>'
        '<div class="agent-current"><span class="current-label">CURRENT OPERATION</span>'
        '<span class="current-text">' + _escape(latest_activity) + '</span></div>'
        '<div class="agent-feed-heading"><span>ACTIVITY LOG</span>'
        '<span>' + str(len(activity_log)) + ' EVENTS</span></div>'
        '<div class="agent-feed">' + ''.join(events) + '</div>'
        '</article>'
    )


def _render(slot, agent_key, status, activity_log, elapsed=None):
    slot.markdown(
        render_agent_workstation(agent_key, status, activity_log, elapsed),
        unsafe_allow_html=True,
    )


def run_osint_audit(target, target_type):
    """Run specialists sequentially while keeping a dedicated live console for each one."""
    results = {}
    tool_counts = {agent_key: 0 for agent_key, _, _ in PIPELINE}
    started_at = time.time()
    st.session_state["nexus_latest_activity"] = {}
    st.session_state["nexus_activity_target"] = str(target)

    st.markdown(
        '<div class="operation-banner"><span class="operation-indicator"></span>'
        '<div><strong>INTELLIGENCE OPERATION IN PROGRESS</strong>'
        '<span>Authorized passive reconnaissance · ' + _escape(target) + '</span></div>'
        '<span class="operation-count">05 SPECIALISTS</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-heading"><div><span>01 / LIVE OPERATIONS</span>'
        '<h2>Agent workstations</h2></div><span>Each console retains its full activity history</span></div>',
        unsafe_allow_html=True,
    )

    left_column, right_column = st.columns(2, gap="medium")
    slots = {}
    for index, (agent_key, _, _) in enumerate(PIPELINE):
        column = left_column if index % 2 == 0 else right_column
        slots[agent_key] = column.empty()
        _render(slots[agent_key], agent_key, "queued", [])
        _save_agent_state(agent_key, "queued", [])

    for agent_key, task, max_rounds in PIPELINE:
        agent = AGENT_PROFILES[agent_key]
        activity_log = []
        agent_start = time.time()
        state = {"status": "deploying"}

        def append_event(event_type, text):
            activity_log.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": event_type,
                "text": str(text),
            })
            if event_type == "error":
                state["status"] = "error"
            _render(
                slots[agent_key],
                agent_key,
                state["status"],
                activity_log,
                time.time() - agent_start,
            )
            _save_agent_state(
                agent_key,
                state["status"],
                activity_log,
                time.time() - agent_start,
            )

        append_event("system", f"{agent['name']} initialized for {task.replace('_', ' ')}.")

        def activity_callback(event_type, payload):
            if event_type == "thinking":
                state["status"] = "thinking"
                append_event("thinking", f"Reasoning pass {payload}: evaluating available context.")
            elif event_type == "tool_call":
                tool_counts[agent_key] += 1
                state["status"] = "executing"
                payload = payload if isinstance(payload, dict) else {}
                append_event(
                    "tool_call",
                    "Executing " + _format_tool_call(payload.get("name", "tool"), payload.get("args", {})),
                )
            elif event_type == "tool_result":
                payload = payload if isinstance(payload, dict) else {}
                preview = str(payload.get("preview", "No preview returned.")).replace("\n", " ").strip()
                append_event("tool_result", f"{payload.get('name', 'Tool')} returned: {preview[:180]}")
            elif event_type == "final":
                response = str(payload or "").strip()
                append_event("final", f"Final response received ({len(response)} characters).")
            elif event_type == "error":
                append_event("error", str(payload)[:240])

        system_prompt = (
            f"You are {agent['name']}, a specialist {agent['role']} in an OSINT team. "
            f"{agent['description']} Use the provided tools to gather real, publicly available data. "
            "Only assess targets the user is authorized to investigate. Be concise but thorough, "
            "distinguish observed facts from inference, and cite URLs when available."
        )

        try:
            if task == "final_report":
                context = "\n\n".join(
                    f"### {AGENT_PROFILES[key]['name']} FINDINGS\n{value}"
                    for key, value in results.items()
                ) or "No specialist findings were returned. Explain this limitation clearly."
                user_prompt = (
                    f"Target: {target} ({target_type})\n\n"
                    f"Specialist findings:\n\n{context}\n\n"
                    "Produce an executive OSINT report with: Executive Summary, Risk Score (0-100), "
                    "Key Findings, Vulnerabilities (severity-tagged), Recommendations, and Conclusion. "
                    "Do not invent evidence; clearly note missing or failed data sources."
                )
                finding = run_agent_with_tools(
                    system_prompt, user_prompt, [], execute_tool, 1,
                    activity_callback=activity_callback,
                )
            else:
                user_prompt = (
                    f"Perform {task.replace('_', ' ')} on {target} ({target_type}). "
                    "Use the most relevant available tools and return structured findings. "
                    "Only perform passive, publicly accessible checks."
                )
                finding = run_agent_with_tools(
                    system_prompt, user_prompt, GROQ_TOOL_DEFINITIONS, execute_tool,
                    max_rounds, activity_callback=activity_callback,
                )
            finding = str(finding).strip() if finding is not None else ""
            if not finding:
                finding = "The agent completed without a text response."
            results[agent_key] = finding
            if state["status"] != "error":
                state["status"] = "complete"
            append_event("system", f"Analysis finished. {tool_counts[agent_key]} tool call(s) recorded.")
        except Exception as exc:
            logging.exception("Agent %s failed", agent_key)
            finding = f"Agent execution failed: {type(exc).__name__}: {exc}"
            results[agent_key] = finding
            state["status"] = "error"
            append_event("error", finding[:240])

    completed = sum(1 for value in results.values() if value.strip())
    st.markdown(
        '<div class="operation-complete"><span class="complete-mark">✓</span>'
        '<div><strong>OPERATION COMPLETE</strong><span>'
        + str(completed) + ' of ' + str(len(PIPELINE)) + ' specialists returned a result · '
        + f'{time.time() - started_at:.1f}s elapsed</span></div></div>',
        unsafe_allow_html=True,
    )
    return results
