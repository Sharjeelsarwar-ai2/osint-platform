import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.scriptrunner").setLevel(logging.ERROR)

import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime
from config.settings import AGENT_PROFILES
from utils.groq_client import run_agent_with_tools
from agents.tools import GROQ_TOOL_DEFINITIONS, execute_tool


# ─────────────────────────────────────────────────────────
#  CSS shared across all iframe components
# ─────────────────────────────────────────────────────────
def _base_css():
    return (
        "@import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@600;700;900"
        "&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600"
        "&display=swap');"
        "*{box-sizing:border-box;margin:0;padding:0;}"
        "html,body{background:transparent;overflow:hidden;color:#f1f5f9;}"
        "@keyframes spin{to{transform:rotate(360deg)}}"
        "@keyframes afloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}"
        "@keyframes dotp{0%,80%,100%{transform:scale(0.4);opacity:0.3}40%{transform:scale(1.2);opacity:1}}"
        "@keyframes sglow{0%,100%{opacity:1;box-shadow:0 0 8px #10b981}50%{opacity:0.4;box-shadow:0 0 2px #10b981}}"
        "@keyframes scanm{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}"
        "@keyframes slideIn{from{opacity:0;transform:translateX(-20px)}to{opacity:1;transform:translateX(0)}}"
        "@keyframes gradientShift{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}"
        "@keyframes hologram{0%,100%{opacity:0.7}50%{opacity:1}}"
        "@keyframes pulse3d{0%,100%{transform:translateZ(0) scale(1)}50%{transform:translateZ(20px) scale(1.03)}}"
    )


def _render(html, height):
    try:
        st.html(html, height=height, scrolling=False)
    except (AttributeError, TypeError):
        components.html(html, height=height, scrolling=False)


# ─────────────────────────────────────────────────────────
#  AGENT WORKSTATION — Live activity window (3D card)
# ─────────────────────────────────────────────────────────
def render_agent_workstation(agent_key, status="deploying", activity_log=None, elapsed=None):
    """
    Full agent workstation with live activity feed.
    status: 'deploying' | 'thinking' | 'executing' | 'complete'
    activity_log: list of dicts {time, type, text, color}
    """
    a = AGENT_PROFILES[agent_key]
    c = a["color"]
    activity_log = activity_log or []

    # Status badge config
    status_cfg = {
        "deploying":  ("🚀 DEPLOYING",  c,          "spin 2s linear infinite"),
        "thinking":   ("🧠 THINKING",   "#8b5cf6",  "pulse3d 1.5s ease-in-out infinite"),
        "executing":  ("⚙ EXECUTING",   c,          "spin 1.5s linear infinite"),
        "complete":   ("✓ COMPLETE",    "#10b981",  "none"),
    }
    status_text, status_color, ring_anim = status_cfg.get(status, status_cfg["deploying"])

    # Build activity feed HTML (last 10 events)
    feed_html = ""
    for i, e in enumerate(activity_log[-10:]):
        feed_html += (
            '<div style="display:flex;align-items:flex-start;gap:0.6rem;'
            'padding:0.4rem 0.6rem;margin-bottom:0.25rem;'
            'background:linear-gradient(90deg,' + e["color"] + '12,transparent);'
            'border-left:2px solid ' + e["color"] + ';'
            'border-radius:0 6px 6px 0;'
            'animation:slideIn 0.4s ease-out;">'
            '<span style="font-family:JetBrains Mono,monospace;font-size:0.6rem;'
            'color:#64748b;flex-shrink:0;min-width:52px;">' + e["time"] + '</span>'
            '<span style="font-size:0.9rem;flex-shrink:0;">' + e["icon"] + '</span>'
            '<span style="font-family:Space Grotesk,sans-serif;font-size:0.72rem;'
            'color:#cbd5e1;line-height:1.4;word-break:break-word;">' + e["text"] + '</span>'
            '</div>'
        )

    if not feed_html:
        feed_html = (
            '<div style="text-align:center;padding:1.5rem;'
            'font-family:JetBrains Mono,monospace;font-size:0.7rem;'
            'color:#475569;font-style:italic;">'
            '> Initializing agent environment…</div>'
        )

    elapsed_html = ""
    if elapsed is not None:
        elapsed_html = (
            '<span style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            'color:#64748b;margin-left:auto;">⏱ ' + str(round(elapsed, 1)) + 's</span>'
        )

    css = _base_css()
    html = (
        '<style>' + css + '</style>'

        # OUTER 3D CARD
        '<div style="'
        'background:linear-gradient(135deg,rgba(17,24,39,0.95),rgba(15,22,41,0.85));'
        'border:1px solid ' + c + '35;'
        'border-radius:20px;'
        'padding:1.3rem;'
        'position:relative;'
        'overflow:hidden;'
        'box-shadow:'
        '0 20px 60px rgba(0,0,0,0.5),'
        '0 0 40px ' + c + '15,'
        'inset 0 1px 0 rgba(255,255,255,0.06),'
        'inset 0 -1px 0 rgba(0,0,0,0.3);'
        'transform:perspective(1000px) rotateX(0.5deg);'
        'font-family:Space Grotesk,sans-serif;">'

        # Scanner line
        '<div style="position:absolute;top:0;left:0;width:100%;height:2px;'
        'background:linear-gradient(90deg,transparent,' + c + ',' + c + ',transparent);'
        'background-size:200% 100%;'
        'animation:scanm 3s linear infinite,gradientShift 3s ease infinite;'
        'box-shadow:0 0 10px ' + c + ';"></div>'

        # Holographic corner accents
        '<div style="position:absolute;top:8px;right:8px;width:30px;height:30px;'
        'border-top:2px solid ' + c + '60;border-right:2px solid ' + c + '60;'
        'border-radius:0 8px 0 0;animation:hologram 2s ease-in-out infinite;"></div>'
        '<div style="position:absolute;bottom:8px;left:8px;width:30px;height:30px;'
        'border-bottom:2px solid ' + c + '60;border-left:2px solid ' + c + '60;'
        'border-radius:0 0 0 8px;animation:hologram 2s ease-in-out infinite;"></div>'

        # ─ HEADER ─
        '<div style="display:flex;align-items:center;gap:1.2rem;margin-bottom:1rem;'
        'padding-bottom:0.8rem;border-bottom:1px solid ' + c + '20;">'

        # Avatar with rotating ring
        '<div style="position:relative;width:76px;height:76px;flex-shrink:0;">'
        '<div style="position:absolute;top:-6px;left:-6px;width:88px;height:88px;'
        'border:2px solid transparent;'
        'border-top-color:' + c + ';border-right-color:' + c + '70;'
        'border-radius:50%;animation:' + ring_anim + ';"></div>'
        '<div style="position:absolute;top:0;left:0;width:76px;height:76px;'
        'border-radius:50%;background:radial-gradient(circle,' + c + '30,transparent);'
        'filter:blur(8px);"></div>'
        '<img src="' + a["avatar_url"] + '" style="position:relative;z-index:1;'
        'width:76px;height:76px;border-radius:50%;'
        'border:2px solid ' + c + ';background:#0a0e17;'
        'box-shadow:0 0 25px ' + c + '50,inset 0 0 20px rgba(0,0,0,0.5);'
        'animation:afloat 3s ease-in-out infinite;"/>'
        '<div style="position:absolute;bottom:0;right:0;width:16px;height:16px;'
        'background:' + status_color + ';border:3px solid #030712;border-radius:50%;'
        'z-index:3;animation:sglow 1s ease-in-out infinite;"></div></div>'

        # Agent name + status
        '<div style="flex:1;min-width:0;">'
        '<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;">'
        '<span style="font-size:1.2rem;">' + a["icon"] + '</span>'
        '<span style="font-family:Exo 2,sans-serif;font-size:1.1rem;font-weight:900;'
        'color:' + c + ';letter-spacing:4px;'
        'text-shadow:0 0 15px ' + c + '60,0 2px 4px rgba(0,0,0,0.5);">'
        + a["name"] + '</span>'
        + elapsed_html +
        '</div>'
        '<div style="font-family:Space Grotesk,sans-serif;font-size:0.7rem;'
        'color:#94a3b8;letter-spacing:2px;text-transform:uppercase;margin-bottom:0.4rem;">'
        + a["role"] + '</div>'
        '<div style="display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;">'
        '<span style="display:inline-flex;align-items:center;gap:0.3rem;'
        'padding:3px 10px;background:' + status_color + '18;'
        'border:1px solid ' + status_color + ';border-radius:10px;'
        'font-family:JetBrains Mono,monospace;font-size:0.6rem;'
        'color:' + status_color + ';letter-spacing:2px;font-weight:700;'
        'box-shadow:0 0 10px ' + status_color + '30;">'
        + status_text + '</span>'
        '<span style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        'color:#64748b;font-style:italic;">' + a["catchphrase"] + '</span>'
        '</div></div></div>'

        # ─ LIVE ACTIVITY FEED ─
        '<div style="background:rgba(3,7,18,0.7);border:1px solid ' + c + '15;'
        'border-radius:12px;padding:0.6rem;max-height:220px;overflow-y:auto;'
        'box-shadow:inset 0 2px 8px rgba(0,0,0,0.4);">'

        # Feed header
        '<div style="display:flex;align-items:center;gap:0.4rem;'
        'padding:0 0.3rem 0.5rem;margin-bottom:0.5rem;'
        'border-bottom:1px dashed ' + c + '20;">'
        '<span style="width:6px;height:6px;background:#10b981;border-radius:50%;'
        'animation:sglow 1.5s ease-in-out infinite;"></span>'
        '<span style="font-family:JetBrains Mono,monospace;font-size:0.6rem;'
        'color:#64748b;letter-spacing:2px;text-transform:uppercase;">'
        'LIVE ACTIVITY STREAM</span>'
        '<span style="margin-left:auto;font-family:JetBrains Mono,monospace;'
        'font-size:0.58rem;color:#475569;">' + str(len(activity_log)) + ' events</span>'
        '</div>'

        + feed_html +

        '</div></div>'
    )

    _render(html, 420)


# ─────────────────────────────────────────────────────────
#  COMPLETED AGENT — compact badge
# ─────────────────────────────────────────────────────────
def render_agent_complete_badge(agent_key, tool_count=0, elapsed=0):
    a = AGENT_PROFILES[agent_key]
    c = a["color"]
    css = _base_css()
    html = (
        '<style>' + css + '</style>'
        '<div style="display:flex;align-items:center;gap:1rem;'
        'padding:0.7rem 1.1rem;margin-bottom:0.5rem;'
        'background:linear-gradient(135deg,' + c + '10,rgba(17,24,39,0.9));'
        'border:1px solid ' + c + '30;border-radius:14px;'
        'box-shadow:0 4px 15px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.05);'
        'position:relative;overflow:hidden;">'
        '<div style="position:absolute;left:0;top:0;bottom:0;width:3px;'
        'background:linear-gradient(180deg,' + c + ',transparent);"></div>'
        '<img src="' + a["avatar_url"] + '" style="width:38px;height:38px;'
        'border-radius:50%;border:2px solid ' + c + ';background:#0a0e17;'
        'box-shadow:0 0 12px ' + c + '40;"/>'
        '<div style="flex:1;">'
        '<div style="display:flex;align-items:center;gap:0.5rem;">'
        '<span style="font-family:Exo 2,sans-serif;font-size:0.85rem;'
        'font-weight:900;color:' + c + ';letter-spacing:3px;">'
        + a["icon"] + ' ' + a["name"] + '</span>'
        '<span style="color:#10b981;font-size:1rem;">✓</span></div>'
        '<div style="font-family:Space Grotesk,sans-serif;font-size:0.65rem;'
        'color:#94a3b8;letter-spacing:1px;">' + a["role"] + '</div></div>'
        '<div style="text-align:right;">'
        '<div style="font-family:JetBrains Mono,monospace;font-size:0.75rem;'
        'color:#10b981;font-weight:600;">⏱ ' + str(round(elapsed, 1)) + 's</div>'
        '<div style="font-family:JetBrains Mono,monospace;font-size:0.6rem;'
        'color:#64748b;">' + str(tool_count) + ' tools</div></div>'
        '</div>'
    )
    _render(html, 75)


# ─────────────────────────────────────────────────────────
#  Helper: format tool call for activity log
# ─────────────────────────────────────────────────────────
def _format_tool_call(name, args):
    key_arg = ""
    for k in ("domain", "url", "ip_address", "query", "company"):
        if k in args:
            key_arg = str(args[k])[:40]
            break
    if not key_arg and args:
        key_arg = str(list(args.values())[0])[:40]
    return name + "(" + key_arg + ")" if key_arg else name + "()"


# ─────────────────────────────────────────────────────────
#  MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────
def run_osint_audit(target, target_type):
    results = {}

    # Header
    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;margin:1.5rem 0;">'
        '<div style="display:inline-block;padding:0.5rem 1.5rem;'
        'background:linear-gradient(135deg,rgba(59,130,246,0.1),rgba(16,185,129,0.1));'
        'border:1px solid rgba(59,130,246,0.3);border-radius:30px;">'
        '<span style="font-family:Exo 2,sans-serif;font-size:1.1rem;font-weight:900;'
        'letter-spacing:5px;'
        'background:linear-gradient(135deg,#3b82f6,#10b981,#f59e0b);'
        'background-size:200% auto;'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
        'background-clip:text;animation:gradientShift 3s ease infinite;">'
        '⚡ MULTI-AGENT RECONNAISSANCE ACTIVE ⚡</span></div></div>',
        unsafe_allow_html=True,
    )

    # Status zones
    workstation_zone = st.empty()
    st.markdown(
        '<div style="margin-top:1.5rem;font-family:Exo 2,sans-serif;font-size:0.75rem;'
        'font-weight:700;letter-spacing:3px;color:#64748b;text-transform:uppercase;">'
        '✓ COMPLETED AGENTS</div>',
        unsafe_allow_html=True,
    )
    completed_zone = st.container()
    st.markdown("---")

    pipeline = [
        ("aria",   "domain_recon",    3),
        ("raven",  "threat_intel",    2),
        ("vulcan", "attack_surface",  2),
        ("cipher", "email_osint",     1),
        ("oracle", "final_report",    1),
    ]

    for agent_key, task, max_rounds in pipeline:
        agent = AGENT_PROFILES[agent_key]
        activity_log = []
        tool_count = 0
        agent_start = time.time()

        def now_str():
            return datetime.now().strftime("%H:%M:%S")

        # Initial render
        with workstation_zone.container():
            activity_log.append({
                "time": now_str(),
                "icon": "🚀",
                "text": "Agent " + agent["name"] + " deployed — " + agent["role"],
                "color": agent["color"],
            })
            render_agent_workstation(agent_key, "deploying", activity_log)

        # Callback that updates the live feed
        def activity_callback(event_type, payload):
            nonlocal tool_count
            if event_type == "thinking":
                activity_log.append({
                    "time": now_str(),
                    "icon": "🧠",
                    "text": "Reasoning round " + str(payload) + " — analyzing context",
                    "color": "#8b5cf6",
                })
                with workstation_zone.container():
                    render_agent_workstation(
                        agent_key, "thinking", activity_log,
                        elapsed=time.time() - agent_start,
                    )
            elif event_type == "tool_call":
                tool_count += 1
                activity_log.append({
                    "time": now_str(),
                    "icon": "⚙",
                    "text": "Executing: " + _format_tool_call(payload["name"], payload["args"]),
                    "color": agent["color"],
                })
                with workstation_zone.container():
                    render_agent_workstation(
                        agent_key, "executing", activity_log,
                        elapsed=time.time() - agent_start,
                    )
            elif event_type == "tool_result":
                preview = payload["preview"].replace("\n", " ")[:80]
                activity_log.append({
                    "time": now_str(),
                    "icon": "📥",
                    "text": "Received: " + preview + "…",
                    "color": "#10b981",
                })
                with workstation_zone.container():
                    render_agent_workstation(
                        agent_key, "executing", activity_log,
                        elapsed=time.time() - agent_start,
                    )
            elif event_type == "final":
                activity_log.append({
                    "time": now_str(),
                    "icon": "✓",
                    "text": "Analysis complete — synthesizing findings",
                    "color": "#10b981",
                })
            elif event_type == "error":
                activity_log.append({
                    "time": now_str(),
                    "icon": "⚠",
                    "text": str(payload)[:120],
                    "color": "#f43f5e",
                })

        # Build prompts
        sys_prompt = (
            "You are " + agent["name"] + ", a specialist " + agent["role"]
            + " in an elite OSINT team. " + agent["description"]
            + " Use the provided tools to gather REAL data."
            + " Be concise but thorough. Prioritize impactful tools first."
        )

        if task == "final_report":
            ctx = "\n\n".join("### " + k.upper() + "\n" + v for k, v in results.items())
            usr = (
                "Target: " + target + " (" + target_type + ")\n\n"
                "Agent findings:\n\n" + ctx + "\n\n"
                "Produce an executive OSINT report:\n"
                "1. Executive Summary\n2. Risk Score (0-100)\n"
                "3. Key Findings\n4. Vulnerabilities (severity-tagged)\n"
                "5. Recommendations\n6. Conclusion"
            )
            finding = run_agent_with_tools(
                sys_prompt, usr, [], execute_tool, 1,
                activity_callback=activity_callback,
            )
        else:
            usr = (
                "Perform " + task.replace("_", " ") + " on: " + target
                + " (" + target_type + "). Use the most relevant tools."
                + " Return structured findings."
            )
            finding = run_agent_with_tools(
                sys_prompt, usr, GROQ_TOOL_DEFINITIONS, execute_tool, max_rounds,
                activity_callback=activity_callback,
            )

        results[agent_key] = finding
        elapsed = time.time() - agent_start

        # Final render in workstation with "complete" status, then move to completed zone
        with workstation_zone.container():
            render_agent_workstation(agent_key, "complete", activity_log, elapsed=elapsed)
        time.sleep(0.5)
        workstation_zone.empty()

        with completed_zone:
            render_agent_complete_badge(agent_key, tool_count, elapsed)

        time.sleep(0.2)

    return results
