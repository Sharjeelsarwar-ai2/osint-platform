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
    "finalizing": "SYNTHESIZING",
    "complete": "COMPLETE",
    "fallback": "PARTIAL OUTPUT",
    "error": "NEEDS ATTENTION",
}

EVENT_LABELS = {
    "system": "SYS",
    "thinking": "LLM",
    "tool_call": "EXEC",
    "tool_result": "DATA",
    "tool_blocked": "BLOCKED",
    "finalizing": "SYNTH",
    "fallback": "FALLBACK",
    "final": "DONE",
    "error": "ERR",
}

# Presentation only: derived from the *real* per-agent activity logs and
# tool counts produced by run_osint_audit. Nothing here runs an agent,
# invents activity, or changes the pipeline. It is pure (no Streamlit
# access) so it can be unit-tested.
FINISHED_STATUSES = ("complete", "fallback", "error")


def summarize_operation(activity, global_activity, operation):
    """Summarise real operation state for the mission-control panel."""
    activity = activity or {}
    global_activity = global_activity or []
    operation = operation or {}
    tool_counts = operation.get("tool_counts", {}) or {}
    statuses = {}
    for agent_key, _, _ in PIPELINE:
        statuses[agent_key] = (activity.get(agent_key, {}) or {}).get("status", "queued")
    finished = [key for key, status in statuses.items() if status in FINISHED_STATUSES]
    succeeded = [key for key, status in statuses.items() if status == "complete"]
    total_tools = sum(int(tool_counts.get(key, 0) or 0) for key, _, _ in PIPELINE)
    progress = round(100 * len(finished) / len(PIPELINE)) if PIPELINE else 0
    return {
        "target": operation.get("target", ""),
        "status": operation.get("status", "idle"),
        "current_agent": operation.get("current_agent"),
        "statuses": statuses,
        "finished": finished,
        "succeeded": succeeded,
        "progress": progress,
        "total_tools": total_tools,
        "tool_counts": tool_counts,
        "event_count": len(global_activity),
        "elapsed": operation.get("elapsed"),
    }


def _timeline_markup(summary):
    nodes = []
    for index, (agent_key, _, _) in enumerate(PIPELINE):
        agent = AGENT_PROFILES[agent_key]
        status = summary["statuses"][agent_key]
        if status in FINISHED_STATUSES:
            node_class = "node-error" if status == "error" else "node-done"
            mark = "✕" if status == "error" else "✓"
        elif agent_key == summary["current_agent"] and summary["status"] == "running":
            node_class = "node-current"
            mark = "●"
        else:
            node_class = "node-queued"
            mark = str(index + 1)
        tools = summary["tool_counts"].get(agent_key, 0)
        try:
            from ui.avatars import avatar_html as _avatar_html

            _mini = _avatar_html(agent_key, status, size=30)
        except Exception:
            _mini = ""
        nodes.append(
            '<div class="tl-node ' + node_class + '">'
            + _mini
            + '<span class="tl-mark" style="--agent-accent:' + _escape(agent.get("color", "#FF2E88")) + '">' + mark + "</span>"
            '<span class="tl-name">' + _escape(agent.get("name", agent_key)) + "</span>"
            '<span class="tl-meta">' + _escape(STATUS_LABELS.get(status, status).title()) + " · " + str(tools) + " tools</span>"
            "</div>"
            + ('<span class="tl-connector"></span>' if index < len(PIPELINE) - 1 else "")
        )
    return "".join(nodes)


def render_global_feed_html(global_activity, limit=40):
    """Chronological feed of real events only (newest last, scrollable)."""
    events = list(global_activity or [])[-limit:]
    if not events:
        return (
            '<div class="mission-feed-empty">No live operation yet. '
            "Activity will appear here — event by event, as agents actually run — "
            "when a scan starts. Nothing here is simulated.</div>"
        )
    rows = []
    for event in events:
        agent = AGENT_PROFILES.get(event.get("agent", ""), {})
        rows.append(
            '<div class="feed-row">'
            "<time>" + _escape(event.get("time", "")) + "</time>"
            '<span class="feed-agent" style="--agent-accent:' + _escape(agent.get("color", "#FF2E88")) + '">'
            + _escape(agent.get("name", event.get("agent", ""))) + "</span>"
            '<span class="event-tag event-' + _escape(event.get("type", "system")) + '">'
            + _escape(EVENT_LABELS.get(event.get("type", "system"), "LOG")) + "</span>"
            '<span class="feed-text">' + _escape(event.get("text", "")) + "</span>"
            "</div>"
        )
    return "".join(rows)


def render_mission_control():
    """Mission-control panel: pipeline timeline + live stats + global feed.

    Reads only session state written by run_osint_audit from real
    activity callbacks. When idle it honestly shows 0% / queued / empty.
    """
    activity = st.session_state.get("nexus_latest_activity", {})
    global_activity = st.session_state.get("nexus_global_activity", [])
    operation = st.session_state.get("nexus_operation", {})
    summary = summarize_operation(activity, global_activity, operation)
    running = summary["status"] == "running"
    elapsed = summary["elapsed"]
    if elapsed is None and operation.get("started_at"):
        elapsed = time.time() - operation["started_at"]
    elapsed_text = f"{elapsed:.1f}s" if elapsed is not None else "—"
    live_class = " mission-live" if running else ""
    live_label = "● LIVE — AGENTS WORKING" if running else "STANDBY — NO OPERATION RUNNING"
    target_text = summary["target"] or "No target yet"
    return (
        '<section class="mission-control' + live_class + '">'
        '<div class="mission-head"><div><span class="section-kicker">MISSION CONTROL</span>'
        '<h2>Live operation</h2></div>'
        '<span class="mission-live-label">' + live_label + "</span></div>"
        '<div class="mission-target">TARGET · <strong>' + _escape(target_text) + "</strong>"
        '<span>' + str(len(summary["succeeded"])) + "/" + str(len(PIPELINE)) + " agents complete · "
        + str(summary["total_tools"]) + " tools executed · "
        + str(summary["event_count"]) + " events · " + elapsed_text + "</span></div>"
        '<div class="mission-progress"><div class="mission-progress-track">'
        '<div class="mission-progress-fill" style="width:' + str(summary["progress"]) + '%"></div></div>'
        '<span class="mission-progress-pct">' + str(summary["progress"]) + "%</span></div>"
        '<div class="mission-timeline">' + _timeline_markup(summary) + "</div>"
        '<div class="mission-feed-heading"><span>GLOBAL ACTIVITY FEED — ALL AGENTS, IN REAL TIME</span>'
        "<span>" + str(summary["event_count"]) + " EVENTS</span></div>"
        '<div class="mission-feed">' + render_global_feed_html(global_activity) + "</div>"
        "</section>"
    )


def _escape(value):
    return html.escape(str(value), quote=True)


def _save_agent_state(agent_key, status, activity_log, elapsed=None):
    saved = dict(st.session_state.get("nexus_latest_activity", {}))
    saved[agent_key] = {
        "status": status,
        "activity_log": list(activity_log),
        "elapsed": elapsed,
    }
    st.session_state["nexus_latest_activity"] = saved


def _avatar_markup(agent_key="aria", status="queued"):
    """v3: the agent's committed SVG character portrait, not an abstract dot.

    Status drives the CSS animation class only; the portrait file itself
    is static art in ui/avatars/<agent>.svg.
    """
    try:
        from ui.avatars import avatar_html

        return '<div class="agent-avatar">' + avatar_html(agent_key, status, size=64) + "</div>"
    except Exception:
        # Never let a portrait failure break a workstation render.
        return '<div class="agent-avatar" aria-hidden="true"></div>'


def render_agent_workstation(agent_key, status="queued", activity_log=None, elapsed=None):
    """Render one animated, persistent specialist console and its complete event history."""
    agent = AGENT_PROFILES[agent_key]
    accent = agent.get("color", "#FF2E88")
    activity_log = activity_log or []
    status_label = STATUS_LABELS.get(status, "INITIALIZING")
    latest_activity = activity_log[-1]["text"] if activity_log else "Waiting for the orchestration queue."
    elapsed_text = f"{elapsed:.1f}s" if elapsed is not None else "—"

    events = []
    for event in activity_log:
        event_type = event.get("type", "system")
        event_label = EVENT_LABELS.get(event_type, "LOG")
        tool_name = event.get("tool_name", "")
        tool_prefix = (
            '<code class="event-tool-name">' + _escape(tool_name) + '</code>'
            if tool_name else ""
        )
        events.append(
            '<div class="agent-event">'
            '<time>' + _escape(event.get("time", "")) + '</time>'
            '<span class="event-tag event-' + _escape(event_type) + '">' + _escape(event_label) + '</span>'
            '<span class="event-message">' + tool_prefix + _escape(event.get("text", "")) + '</span>'
            '</div>'
        )

    if not events:
        events.append('<div class="agent-empty">No activity yet. This specialist is standing by.</div>')

    return (
        '<article class="agent-console status-' + _escape(status) + '" style="--agent-accent:' + _escape(accent) + '">'
        '<div class="agent-console-topline"></div>'
        '<header class="agent-console-header">'
        + _avatar_markup(agent_key, status) +
        '<div class="agent-heading">'
        '<div class="agent-name-row"><h3>' + _escape(agent.get("name", agent_key)) + '</h3>'
        '<span class="agent-status"><i></i>' + _escape(status_label) + '</span></div>'
        '<p>' + _escape(agent.get("role", "Specialist agent")) + '</p>'
        '</div>'
        '<div class="agent-duration">' + _escape(elapsed_text) + '</div>'
        '</header>'
        '<div class="agent-current"><span class="current-label">CURRENT OPERATION</span>'
        '<span class="current-text">' + _escape(latest_activity) + '</span></div>'
        '<div class="agent-feed-heading"><span>LIVE ACTIVITY</span>'
        '<span>' + str(len(activity_log)) + ' EVENTS</span></div>'
        '<div class="agent-feed">' + ''.join(events) + '</div>'
        '</article>'
    )


def render_saved_agent_workstations():
    """Re-display the last run's agent windows after ordinary Streamlit reruns."""
    saved = st.session_state.get("nexus_latest_activity", {})
    if not saved:
        return
    # Mission control first: pipeline state + the real global feed,
    # so a saved run still shows what actually happened, in order.
    st.markdown(render_mission_control(), unsafe_allow_html=True)
    st.markdown(
        '<div class="section-heading"><div><span class="section-kicker">01 / LAST OPERATION</span>'
        '<h2>Agent workstations</h2></div><span>Animated status · full tool and activity history retained</span></div>',
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


def _format_tool_call(name, args):
    args = args if isinstance(args, dict) else {}
    if not args:
        return f"{name}()"
    compact_args = ", ".join(f"{key}={value}" for key, value in args.items())
    return f"{name}({compact_args[:110]})"


def _render(slot, agent_key, status, activity_log, elapsed=None):
    slot.markdown(
        render_agent_workstation(agent_key, status, activity_log, elapsed),
        unsafe_allow_html=True,
    )


def run_osint_audit(target, target_type):
    """Run specialists and stream each agent's tools, evidence, and final status to its own console."""
    results = {}
    tool_counts = {agent_key: 0 for agent_key, _, _ in PIPELINE}
    started_at = time.time()
    st.session_state["nexus_latest_activity"] = {}
    st.session_state["nexus_global_activity"] = []
    st.session_state["nexus_activity_target"] = str(target)
    st.session_state["nexus_operation"] = {
        "target": str(target),
        "status": "running",
        "current_agent": None,
        "tool_counts": tool_counts,
        "started_at": started_at,
        "elapsed": None,
    }

    st.markdown(
        '<div class="operation-banner"><span class="operation-indicator"></span>'
        '<div><strong>INTELLIGENCE OPERATION IN PROGRESS</strong>'
        '<span>Authorized passive reconnaissance · ' + _escape(target) + '</span></div>'
        '<span class="operation-count">05 SPECIALISTS</span></div>',
        unsafe_allow_html=True,
    )
    # Live mission control, updated on every real activity event below.
    mission_slot = st.empty()
    mission_slot.markdown(render_mission_control(), unsafe_allow_html=True)
    st.markdown(
        '<div class="section-heading"><div><span>01 / LIVE OPERATIONS</span>'
        '<h2>Agent workstations</h2></div><span>Watch each animated specialist and see exactly which tools run</span></div>',
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

        def append_event(event_type, text, **details):
            event = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": event_type,
                "text": str(text),
            }
            event.update(details)
            activity_log.append(event)
            # Global feed: the same real event, tagged with its agent.
            # This is the only source of the mission-control feed — no
            # simulated or timer-driven events are ever added.
            global_log = list(st.session_state.get("nexus_global_activity", []))
            global_log.append({**event, "agent": agent_key})
            st.session_state["nexus_global_activity"] = global_log
            operation_state = dict(st.session_state.get("nexus_operation", {}))
            operation_state["current_agent"] = agent_key
            operation_state["tool_counts"] = tool_counts
            st.session_state["nexus_operation"] = operation_state
            if event_type == "error":
                state["status"] = "error"
            elif event_type == "fallback":
                state["status"] = "fallback"
            _render(
                slots[agent_key],
                agent_key,
                state["status"],
                activity_log,
                time.time() - agent_start,
            )
            _save_agent_state(agent_key, state["status"], activity_log, time.time() - agent_start)
            mission_slot.markdown(render_mission_control(), unsafe_allow_html=True)

        append_event("system", f"{agent['name']} initialized for {task.replace('_', ' ')}.")

        def activity_callback(event_type, payload):
            if event_type == "thinking":
                state["status"] = "thinking"
                append_event("thinking", f"Reasoning pass {payload}: selecting the next evidence step.")
            elif event_type == "tool_call":
                payload = payload if isinstance(payload, dict) else {}
                name = str(payload.get("name", "unknown_tool"))
                args = payload.get("args", {})
                tool_counts[agent_key] += 1
                state["status"] = "executing"
                append_event(
                    "tool_call",
                    "Executing " + _format_tool_call(name, args),
                    tool_name=name,
                    tool_args=args if isinstance(args, dict) else {},
                )
            elif event_type == "tool_result":
                payload = payload if isinstance(payload, dict) else {}
                preview = str(payload.get("preview", "No preview returned.")).replace("\n", " ").strip()
                append_event(
                    "tool_result",
                    f"Returned: {preview[:200]}",
                    tool_name=str(payload.get("name", "")),
                )
            elif event_type == "tool_blocked":
                payload = payload if isinstance(payload, dict) else {}
                append_event("tool_blocked", str(payload.get("message", "Tool was not enabled.")),
                             tool_name=str(payload.get("name", "")))
            elif event_type == "finalizing":
                state["status"] = "finalizing"
                attempt = payload.get("attempt", 1) if isinstance(payload, dict) else 1
                append_event("finalizing", f"Tool window closed; synthesizing evidence (attempt {attempt}).")
            elif event_type == "fallback":
                payload = payload if isinstance(payload, dict) else {}
                append_event(
                    "fallback",
                    f"Using evidence-backed fallback; {payload.get('tool_count', 0)} tool result(s) retained.",
                )
            elif event_type == "final":
                response = str(payload or "").strip()
                append_event("final", f"Final answer ready ({len(response)} characters).")
            elif event_type == "error":
                append_event("error", str(payload)[:260])

        system_prompt = (
            f"You are {agent['name']}, a specialist {agent['role']} in an OSINT team. "
            f"{agent['description']} Gather only real, publicly available evidence using the enabled tools. "
            "Assess only targets the user is authorized to investigate. Never invent observations, "
            "and clearly separate verified evidence, interpretation, and uncertainty. Return useful "
            "Markdown, not a status message or a promise to continue."
        )

        try:
            if task == "final_report":
                context = "\n\n".join(
                    f"### {AGENT_PROFILES[key]['name']} FINDINGS\n{value}"
                    for key, value in results.items()
                ) or "No specialist findings were returned. State this limitation; do not invent evidence."
                user_prompt = (
                    f"Target: {target} ({target_type})\n\n"
                    f"Specialist findings:\n\n{context}\n\n"
                    "Write a concise executive OSINT report with these Markdown sections: Executive Summary; "
                    "Risk Score (0-100) with rationale; Key Findings with evidence/source attribution; "
                    "Vulnerabilities (severity-tagged, if evidence supports them); prioritized Recommendations; "
                    "and Limitations. Do not claim a vulnerability from missing data alone."
                )
                finding = run_agent_with_tools(
                    system_prompt, user_prompt, [], execute_tool, 1,
                    activity_callback=activity_callback,
                    fallback_context=context,
                )
            else:
                user_prompt = (
                    f"Perform {task.replace('_', ' ')} for target {target} ({target_type}). "
                    "Use the enabled tools selectively and explain their observations. Return a complete "
                    "Markdown deliverable with these sections: Executive Summary; Findings; Evidence and "
                    "Sources (include tool names and observed values); Risk Assessment; Recommended Actions; "
                    "and Limitations. Explicitly say when no result was found. Do not invent data, and do not "
                    "leave the answer as a tool-call/status update. Only perform passive public checks."
                )
                finding = run_agent_with_tools(
                    system_prompt, user_prompt, GROQ_TOOL_DEFINITIONS, execute_tool,
                    max_rounds, activity_callback=activity_callback,
                )
            finding = str(finding).strip() if finding is not None else ""
            if not finding:
                finding = "# Agent result unavailable\n\nNo final text was returned. Review the activity log and retry the analysis."
            results[agent_key] = finding
            if state["status"] not in ("error", "fallback"):
                state["status"] = "complete"
            append_event("system", f"Agent finished. {tool_counts[agent_key]} tool call(s) recorded.")
        except Exception as exc:
            logging.exception("Agent %s failed", agent_key)
            finding = (
                "# Agent execution failed\n\n"
                f"The {agent['name']} agent could not complete its analysis ({type(exc).__name__}: {exc}). "
                "Review the activity log and verify the API configuration before retrying."
            )
            results[agent_key] = finding
            state["status"] = "error"
            append_event("error", finding[:260])

    completed = sum(1 for value in results.values() if value.strip())
    operation_state = dict(st.session_state.get("nexus_operation", {}))
    operation_state["status"] = "complete"
    operation_state["current_agent"] = None
    operation_state["tool_counts"] = tool_counts
    operation_state["elapsed"] = time.time() - started_at
    st.session_state["nexus_operation"] = operation_state
    mission_slot.markdown(render_mission_control(), unsafe_allow_html=True)
    st.markdown(
        '<div class="operation-complete"><span class="complete-mark">✓</span>'
        '<div><strong>OPERATION COMPLETE</strong><span>'
        + str(completed) + ' of ' + str(len(PIPELINE)) + ' specialists returned a final result · '
        + f'{time.time() - started_at:.1f}s elapsed</span></div></div>',
        unsafe_allow_html=True,
    )
    return results
