"""v3 layout components — pure HTML builders + thin Streamlit wrappers.

The pure builders (ending _html) are unit-testable without a Streamlit
runtime. They read ONLY session-state-shaped dicts passed in, never
invent activity: status/tools come from real activity/operation dicts,
or honest standby when those dicts are empty.
"""
import html
from datetime import datetime, timezone

from ui.avatars import character_card_html

AGENT_ORDER = ("aria", "raven", "vulcan", "cipher", "oracle")


def _esc(v):
    return html.escape(str(v))


def _agent_status(activity, operation, key):
    """(status_text, status_key, tools_text) for one agent, real or standby."""
    record = (activity or {}).get(key, {}) or {}
    raw = record.get("status", "queued")
    tool_counts = (operation or {}).get("tool_counts", {}) or {}
    tools = int(tool_counts.get(key, 0) or 0)
    running = (operation or {}).get("status") == "running"
    current = (operation or {}).get("current_agent")
    if running and key == current:
        text = "● WORKING NOW"
    elif raw == "complete":
        text = "✓ COMPLETE"
    elif raw == "error":
        text = "✕ NEEDS ATTENTION"
    elif raw in ("thinking", "executing", "finalizing"):
        text = "● WORKING"
    elif raw == "fallback":
        text = "◐ PARTIAL OUTPUT"
    elif activity:
        text = raw.replace("_", " ").upper()
    else:
        text = "● STANDBY — READY"
    tools_text = f"{tools} tool(s) this run" if activity else "No scan yet — 0 tools"
    return text, raw, tools_text


def command_bar_html(status_text="STANDBY"):
    return (
        '<div class="cmd-bar"><div class="cmd-brand"><div class="cmd-mark">N</div>'
        '<div><div class="cmd-name">NEXUS</div>'
        '<div class="cmd-sub">LIVE INTELLIGENCE BOARD · NEON NOIR</div></div></div>'
        '<div class="cmd-nav"><span class="hot">◆ DOCK</span>'
        "<span>OPERATIONS</span><span>ACTIVITY</span><span>REPORT</span></div>"
        f'<div class="cmd-live"><span class="cmd-dot"></span>{_esc(status_text)}</div></div>'
    )


def hero_html(model_name, status_text="STANDBY"):
    return (
        '<div class="hero-strip"><span class="hero-orb hero-orb-a"></span>'
        '<span class="hero-orb hero-orb-b"></span><span class="hero-orb hero-orb-c"></span>'
        '<div class="hero-eyebrow">● AGENT DOCK · COMMAND BAR · DASHBOARD · REAL ACTIVITY ONLY · NO SIMULATION</div>'
        '<h1 class="hero-title"><span class="line-a">Track the invisible.</span><br>'
        '<span class="line-b">Expose the truth.</span></h1>'
        '<p class="hero-sub">Five character agents hunt, trace and verify in real time — '
        "domain, threat, attack-surface and email evidence, on one dashboard. "
        "Pick an agent in the dock, launch a scan, and watch its character work.</p>"
        '<div class="hero-badges"><span class="hero-badge hot">REAL AGENTS · NO SIMULATION</span>'
        '<span class="hero-badge lime">5 CHARACTER SPECIALISTS</span>'
        f'<span class="hero-badge">GROQ · {_esc(model_name)}</span>'
        f'<span class="hero-badge">BOARD STATUS · {_esc(status_text)}</span></div></div>'
    )


def metrics_html(profiles, tool_count, model_name):
    cards = [
        ("SPECIALIST AGENTS", str(len(profiles)), "character agents"),
        ("AVAILABLE OSINT TOOLS", str(tool_count), "passive checks"),
        ("REPORT FORMAT", "Evidence-led", "source-aware findings"),
        ("MODEL", str(model_name).split("/")[-1], "Groq inference"),
    ]
    out = ['<div class="metric-row">']
    for label, value, detail in cards:
        out.append(
            f'<div class="metric-card"><div class="metric-label">{_esc(label)}</div>'
            f'<div class="metric-value">{_esc(value)} <small>{_esc(detail)}</small></div></div>'
        )
    out.append("</div>")
    return "".join(out)


def dock_html(profiles, activity=None, operation=None):
    """Persistent agent dock HTML: one large character card per agent."""
    activity = activity or {}
    operation = operation or {}
    out = [
        '<div class="dock-title">◆ AGENT DOCK</div>',
        '<p class="dock-sub">Your five specialists. Characters animate with their '
        "real status — standby bobs gently, a working agent pulses, a finished "
        "agent glows. Nothing here is a fake run.</p>",
    ]
    for key in AGENT_ORDER:
        profile = profiles[key]
        text, raw, tools_text = _agent_status(activity, operation, key)
        out.append(character_card_html(key, profile, text, tools_text, status=raw))
    return "".join(out)


def activity_panel_html(global_activity, operation=None):
    """Right-column live activity panel: real events only, newest last."""
    events = list(global_activity or [])[-12:]
    if not events:
        body = (
            '<div class="mission-feed-empty">No live operation yet. Activity will '
            "appear here — event by event, as agents actually run — when a scan "
            "starts. Nothing here is simulated.</div>"
        )
    else:
        rows = []
        for event in events:
            rows.append(
                '<div class="feed-row"><time>' + _esc(event.get("time", "")) + "</time>"
                '<span class="feed-agent">' + _esc(event.get("agent", "")) + "</span>"
                '<span class="feed-text">' + _esc(event.get("text", "")) + "</span></div>"
            )
        body = "".join(rows)
    target = (operation or {}).get("target") or "No target yet"
    return (
        '<div class="dash-card"><span class="section-kicker">LIVE ACTIVITY</span>'
        "<h3>What the team is doing</h3>"
        f'<p>Target: <strong>{_esc(target)}</strong></p>'
        f'<div class="mission-feed">{body}</div></div>'
    )


def status_bento_html(activity, operation, profiles):
    """Compact operation-status card for the hero dashboard row."""
    operation = operation or {}
    finished = sum(
        1
        for key in AGENT_ORDER
        if (activity or {}).get(key, {}).get("status") in ("complete", "fallback", "error")
    )
    tool_counts = operation.get("tool_counts", {}) or {}
    total_tools = sum(int(tool_counts.get(k, 0) or 0) for k in AGENT_ORDER)
    status = operation.get("status", "idle")
    label = "● LIVE — AGENTS WORKING" if status == "running" else "STANDBY — NO OPERATION RUNNING"
    progress = round(100 * finished / len(AGENT_ORDER)) if AGENT_ORDER else 0
    return (
        '<div class="dash-card"><span class="section-kicker">OPERATION STATUS</span>'
        f"<h3>{_esc(label)}</h3>"
        f'<p>{finished}/5 agents finished · {total_tools} tools executed · '
        f"{progress}% complete</p>"
        '<div class="mission-progress"><div class="mission-progress-track">'
        f'<div class="mission-progress-fill" style="width:{progress}%"></div></div>'
        f'<span class="mission-progress-pct">{progress}%</span></div></div>'
    )


def idle_html():
    return (
        '<div class="idle-panel"><strong>● TEAM ON STANDBY — DASHBOARD IS LIVE, NO SCAN RUNNING</strong>'
        "<span>This dashboard is animated (moving aurora, bobbing characters, pulsing dots), "
        "but no agent is working yet and nothing is simulated. Pick a target and launch a scan — "
        "Mission Control and the dock characters will then show real status, real tools and "
        "the chronological activity feed as each specialist actually works.</span></div>"
    )


# ---- Streamlit wrappers (thin; logic lives in the builders above) ----

def render_command_bar(status_text="STANDBY"):
    import streamlit as st

    st.markdown(command_bar_html(status_text), unsafe_allow_html=True)


def render_hero(model_name, status_text="STANDBY"):
    import streamlit as st

    st.markdown(hero_html(model_name, status_text), unsafe_allow_html=True)


def render_agent_dock(profiles, activity=None, operation=None):
    """Persistent sidebar dock. Call before main content."""
    import streamlit as st

    with st.sidebar:
        st.markdown(dock_html(profiles, activity, operation), unsafe_allow_html=True)
        st.caption(
            "Dock characters animate with real agent status. "
            "Idle = gentle bobbing only; no fake scans."
        )


def render_idle_state():
    import streamlit as st

    st.markdown(idle_html(), unsafe_allow_html=True)


def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
