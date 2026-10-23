"""
Multi-Agent Orchestrator — OSINT & Threat Intelligence Platform
Each agent runs sequentially with real Groq tool-calling.
Avatars rendered via st.components.v1.html() for guaranteed display.
"""

import streamlit as st
import streamlit.components.v1 as components
import time
from config.settings import AGENT_PROFILES, MODEL_NAME
from utils.groq_client import run_agent_with_tools
from agents.tools import GROQ_TOOL_DEFINITIONS, execute_tool


# ──────────────────────────────────────────────
#  KEYFRAME CSS (embedded in every iframe)
# ──────────────────────────────────────────────
_SHARED_KEYFRAMES = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@400;600&family=JetBrains+Mono:ital,wght@0,400;0,500;1,400&display=swap');
html, body { margin:0; padding:0; background:transparent; overflow:hidden; }

@keyframes spin {
    0%   { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes innerPulse {
    0%, 100% { opacity: 0.15; transform: scale(1); }
    50%      { opacity: 0.35; transform: scale(1.06); }
}
@keyframes avatarFloat {
    0%, 100% { transform: translateY(0px); }
    50%      { transform: translateY(-6px); }
}
@keyframes typingDot {
    0%, 80%, 100% { transform: scale(0.5); opacity: 0.3; }
    40%           { transform: scale(1.1); opacity: 1; }
}
@keyframes statusBlink {
    0%, 100% { opacity: 1; box-shadow: 0 0 8px #00ff00; }
    50%      { opacity: 0.3; box-shadow: 0 0 2px #00ff00; }
}
@keyframes scanLine {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
"""


# ──────────────────────────────────────────────
#  RENDER: ACTIVE AGENT (working)
# ──────────────────────────────────────────────
def render_agent_avatar(agent_key: str, status: str = "working"):
    """Show a full animated agent card while the agent is running."""
    a = AGENT_PROFILES[agent_key]
    c = a["color"]

    html = f"""
    <style>{_SHARED_KEYFRAMES}</style>
    <div style="
        display:flex; align-items:center; gap:1.4rem;
        padding:1.2rem 1.5rem;
        background: linear-gradient(135deg, {c}12, {c}06, #0a0e1780);
        border:1px solid {c}40;
        border-radius:16px;
        position:relative; overflow:hidden;
    ">
        <!-- scanner line -->
        <div style="
            position:absolute; top:0; left:0;
            width:100%; height:2px;
            background:linear-gradient(90deg, transparent, {c}, transparent);
            animation: scanLine 2.5s linear infinite;
        "></div>

        <!-- avatar block -->
        <div style="position:relative; width:96px; height:96px; flex-shrink:0;">
            <!-- rotating ring -->
            <div style="
                position:absolute; top:-7px; left:-7px;
                width:110px; height:110px;
                border:3px solid transparent;
                border-top-color:{c}; border-right-color:{c}70;
                border-radius:50%;
                animation: spin 2s linear infinite;
            "></div>
            <!-- inner glow -->
            <div style="
                position:absolute; top:0; left:0;
                width:96px; height:96px;
                border-radius:50%; background:{c};
                opacity:0.15;
                animation: innerPulse 1.5s ease-in-out infinite;
            "></div>
            <!-- avatar img -->
            <img src="{a['avatar_url']}" style="
                width:96px; height:96px;
                border-radius:50%;
                border:3px solid {c};
                background:#0a0e17;
                box-shadow: 0 0 20px {c}60;
                animation: avatarFloat 3s ease-in-out infinite;
                position:relative; z-index:1;
            " alt="{a['name']}"/>
            <!-- status dot -->
            <div style="
                position:absolute; bottom:4px; right:4px;
                width:18px; height:18px;
                background:#00ff00;
                border:3px solid #0a0e17;
                border-radius:50%;
                animation: statusBlink 1s ease-in-out infinite;
                z-index:3;
            "></div>
        </div>

        <!-- info block -->
        <div style="flex:1;">
            <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.2rem;">
                <span style="font-size:1.5rem;">{a['icon']}</span>
                <div>
                    <div style="
                        font-family:'Orbitron',monospace;
                        font-size:1.2rem; font-weight:900;
                        color:{c}; letter-spacing:3px;
                        text-shadow: 0 0 10px {c}60;
                    ">{a['name']}</div>
                    <div style="
                        font-family:'Rajdhani',sans-serif;
                        font-size:0.72rem; color:#94a3b8;
                        letter-spacing:2px; text-transform:uppercase;
                    ">{a['role']}</div>
                </div>
            </div>

            <div style="display:flex; align-items:center; gap:0.5rem; margin-top:0.5rem;">
                <div style="display:flex; gap:4px;">
                    <span style="width:7px;height:7px;background:{c};border-radius:50%;animation:typingDot 1.4s ease-in-out infinite;animation-delay:0s;"></span>
                    <span style="width:7px;height:7px;background:{c};border-radius:50%;animation:typingDot 1.4s ease-in-out infinite;animation-delay:0.2s;"></span>
                    <span style="width:7px;height:7px;background:{c};border-radius:50%;animation:typingDot 1.4s ease-in-out infinite;animation-delay:0.4s;"></span>
                </div>
                <p style="
                    margin:0;
                    font-family:'JetBrains Mono',monospace;
                    font-size:0.85rem; color:#e2e8f0;
                    font-style:italic;
                ">{a['catchphrase']}</p>
            </div>

            <div style="margin-top:0.5rem;">
                <span style="
                    display:inline-block; padding:2px 10px;
                    background:{c}18; border:1px solid {c};
                    border-radius:12px;
                    font-family:'Orbitron',monospace;
                    font-size:0.6rem; color:{c};
                    letter-spacing:2px; font-weight:700;
                ">● WORKING</span>
                <span style="
                    margin-left:0.5rem;
                    font-family:'JetBrains Mono',monospace;
                    font-size:0.65rem; color:#64748b;
                ">Executing real-world tools…</span>
            </div>
        </div>
    </div>
    """
    components.html(html, height=145, scrolling=False)


# ──────────────────────────────────────────────
#  RENDER: COMPLETED AGENT (badge)
# ──────────────────────────────────────────────
def render_agent_complete(agent_key: str):
    """Show a compact 'done' badge after agent finishes."""
    a = AGENT_PROFILES[agent_key]
    c = a["color"]

    html = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&display=swap');
    html, body {{ margin:0; padding:0; background:transparent; overflow:hidden; }}
    </style>
    <div style="
        display:inline-flex; align-items:center; gap:0.5rem;
        padding:0.35rem 0.9rem;
        background:{c}10; border:1px solid {c}30;
        border-radius:20px;
    ">
        <img src="{a['avatar_url']}" style="
            width:26px; height:26px;
            border-radius:50%; border:2px solid {c};
        " alt="{a['name']}"/>
        <span style="
            font-family:'Orbitron',monospace;
            font-size:0.7rem; color:{c};
            letter-spacing:2px; font-weight:700;
        ">{a['icon']} {a['name']}</span>
        <span style="color:#00ff00; font-size:0.85rem;">✓</span>
    </div>
    """
    components.html(html, height=42, scrolling=False)


# ──────────────────────────────────────────────
#  MAIN ORCHESTRATOR
# ──────────────────────────────────────────────
def run_osint_audit(target: str, target_type: str):
    """
    Run all 5 OSINT agents sequentially.
    Each agent uses real Groq tool-calling with live OSINT tools.
    """
    results = {}

    # ── Layout placeholders ──
    st.markdown("---")
    st.markdown(
        '<h3 style="font-family:Orbitron;color:#00f5d4;text-align:center;'
        'letter-spacing:4px;">⚡ AGENT DEPLOYMENT IN PROGRESS ⚡</h3>',
        unsafe_allow_html=True,
    )

    active_box = st.empty()          # shows current working agent
    completed_col = st.container()   # accumulates finished badges
    st.markdown("---")

    # ── Agent pipeline ──
    pipeline = [
        ("aria",   "domain_recon",    6),
        ("raven",  "threat_intel",    4),
        ("vulcan", "attack_surface",  4),
        ("cipher", "email_osint",     3),
        ("oracle", "final_report",    1),
    ]

    for agent_key, task, max_rounds in pipeline:
        agent = AGENT_PROFILES[agent_key]

        # 1 ▸ Show active avatar
        with active_box.container():
            render_agent_avatar(agent_key)

        # 2 ▸ Build prompts
        system_prompt = (
            f"You are {agent['name']}, a specialist {agent['role']} agent "
            f"in an elite OSINT team. {agent['description']} "
            f"Always use the provided tools to gather REAL data. "
            f"Never fabricate information. Be thorough and technical."
        )

        if task == "final_report":
            # Oracle synthesises everything — no tools
            context = "\n\n".join(
                f"### {k.upper()} FINDINGS\n{v}" for k, v in results.items()
            )
            user_prompt = (
                f"Target: {target} ({target_type})\n\n"
                f"Below are the findings from all reconnaissance agents:\n\n"
                f"{context}\n\n"
                f"Produce a comprehensive, executive-grade OSINT report with:\n"
                f"1. Executive Summary\n"
                f"2. Risk Score (0-100) with justification\n"
                f"3. Key Findings by category\n"
                f"4. Identified Vulnerabilities (severity-tagged)\n"
                f"5. Recommendations\n"
                f"6. Conclusion"
            )
            finding = run_agent_with_tools(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=[],
                tool_executor=execute_tool,
                max_rounds=1,
            )
        else:
            user_prompt = (
                f"Perform {task.replace('_', ' ')} on target: {target} "
                f"(type: {target_type}). Use every relevant tool available "
                f"to you. Return detailed, structured findings."
            )
            finding = run_agent_with_tools(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=GROQ_TOOL_DEFINITIONS,
                tool_executor=execute_tool,
                max_rounds=max_rounds,
            )

        results[agent_key] = finding

        # 3 ▸ Mark complete — swap active → completed badge
        active_box.empty()
        with completed_col:
            render_agent_complete(agent_key)

        time.sleep(0.4)   # brief visual pause between agents

    return results
