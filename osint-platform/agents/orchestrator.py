"""
Multi-Agent Orchestrator — NEXUS COMMAND
Each agent runs sequentially with real Groq tool-calling.
"""

import streamlit as st
import streamlit.components.v1 as components
import time
from config.settings import AGENT_PROFILES, MODEL_NAME
from utils.groq_client import run_agent_with_tools
from agents.tools import GROQ_TOOL_DEFINITIONS, execute_tool


# ──────────────────────────────────────────────
#  KEYFRAMES (embedded in each iframe)
# ──────────────────────────────────────────────
_IFRAME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@700;900&family=Space+Grotesk:wght@400;600&family=Fira+Code:wght@400;500&display=swap');
html, body { margin:0; padding:0; background:transparent; overflow:hidden; }

@keyframes spin {
    0%   { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes agentFloat {
    0%, 100% { transform: translateY(0); }
    50%      { transform: translateY(-5px); }
}
@keyframes dotPulse {
    0%, 80%, 100% { transform: scale(0.5); opacity: 0.3; }
    40%           { transform: scale(1.1); opacity: 1; }
}
@keyframes statusGlow {
    0%, 100% { opacity: 1; box-shadow: 0 0 6px #10b981; }
    50%      { opacity: 0.3; box-shadow: 0 0 2px #10b981; }
}
@keyframes scanMove {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
@keyframes borderGlow {
    0%, 100% { opacity: 0.3; }
    50%      { opacity: 0.8; }
}
"""


# ──────────────────────────────────────────────
#  RENDER: Active Agent Card
# ──────────────────────────────────────────────
def render_agent_avatar(agent_key: str, status: str = "working"):
    """Full animated card shown while agent is running."""
    a = AGENT_PROFILES[agent_key]
    c = a["color"]

    html = f"""
    <style>{_IFRAME_CSS}</style>
    <div style="
        display:flex; align-items:center; gap:1.2rem;
        padding:1rem 1.3rem;
        background: linear-gradient(160deg, #11182790, {c}08, #0f162980);
        border:1px solid {c}30;
        border-radius:16px;
        position:relative; overflow:hidden;
        font-family:'Space Grotesk',sans-serif;
    ">
        <!-- Top scanner -->
        <div style="
            position:absolute;top:0;left:0;width:100%;height:2px;
            background:linear-gradient(90deg,transparent,{c},transparent);
            animation:scanMove 2.5s linear infinite;
        "></div>

        <!-- Bottom glow bar -->
        <div style="
            position:absolute;bottom:0;left:10%;width:80%;height:1px;
            background:linear-gradient(90deg,transparent,{c}60,transparent);
            animation:borderGlow 2s ease-in-out infinite;
        "></div>

        <!-- Avatar block -->
        <div style="position:relative;width:88px;height:88px;flex-shrink:0;">
            <!-- Rotating ring -->
            <div style="
                position:absolute;top:-6px;left:-6px;width:100px;height:100px;
                border:2px solid transparent;
                border-top-color:{c};border-right-color:{c}50;
                border-radius:50%;
                animation:spin 2s linear infinite;
            "></div>
            <!-- Avatar -->
            <img src="{a['avatar_url']}" style="
                width:88px;height:88px;border-radius:50%;
                border:2px solid {c};background:#0a0e17;
                box-shadow:0 0 25px {c}30;
                animation:agentFloat 3s ease-in-out infinite;
                position:relative;z-index:1;
            " alt="{a['name']}"/>
            <!-- Status dot -->
            <div style="
                position:absolute;bottom:3px;right:3px;
                width:16px;height:16px;
                background:#10b981;border:3px solid #030712;
                border-radius:50%;z-index:3;
                animation:statusGlow 1s ease-in-out infinite;
            "></div>
        </div>

        <!-- Info block -->
        <div style="flex:1;">
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <span style="font-size:1.3rem;">{a['icon']}</span>
                <div>
                    <div style="
                        font-family:'Exo 2',sans-serif;
                        font-size:1.15rem;font-weight:900;
                        color:{c};letter-spacing:3px;
                        text-shadow:0 0 12px {c}40;
                    ">{a['name']}</div>
                    <div style="
                        font-size:0.68rem;color:#94a3b8;
                        letter-spacing:2px;text-transform:uppercase;
                    ">{a['role']}</div>
                </div>
            </div>

            <!-- Typing indicator -->
            <div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.5rem;">
                <div style="display:flex;gap:3px;">
                    <span style="width:6px;height:6px;background:{c};border-radius:50%;animation:dotPulse 1.4s ease-in-out infinite;animation-delay:0s;"></span>
                    <span style="width:6px;height:6px;background:{c};border-radius:50%;animation:dotPulse 1.4s ease-in-out infinite;animation-delay:0.2s;"></span>
                    <span style="width:6px;height:6px;background:{c};border-radius:50%;animation:dotPulse 1.4s ease-in-out infinite;animation-delay:0.4s;"></span>
                </div>
                <span style="
                    font-family:'Fira Code',monospace;
                    font-size:0.8rem;color:#e2e8f0;
                    font-style:italic;
                ">{a['catchphrase']}</span>
            </div>

            <!-- Status badge -->
            <div style="margin-top:0.4rem;">
                <span style="
                    display:inline-block;padding:2px 10px;
                    background:{c}15;border:1px solid {c};
                    border-radius:10px;
                    font-family:'Fira Code',monospace;
                    font-size:0.58rem;color:{c};
                    letter-spacing:2px;font-weight:600;
                ">● EXECUTING</span>
                <span style="
                    margin-left:0.5rem;
                    font-family:'Fira Code',monospace;
                    font-size:0.62rem;color:#475569;
                ">Real-world tools in progress…</span>
            </div>
        </div>
    </div>
    """
    components.html(html, height=130, scrolling=False)


# ──────────────────────────────────────────────
#  RENDER: Completed Agent Badge
# ──────────────────────────────────────────────
def render_agent_complete(agent_key: str):
    """Compact badge shown after agent finishes."""
    a = AGENT_PROFILES[agent_key]
    c = a["color"]

    html = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@700&family=Fira+Code:wght@400&display=swap');
    html, body {{ margin:0; padding:0; background:transparent; overflow:hidden; }}
    </style>
    <div style="
        display:inline-flex;align-items:center;gap:0.5rem;
        padding:0.3rem 0.8rem;
        background:{c}08;border:1px solid {c}25;
        border-radius:20px;
        font-family:'Space Grotesk',sans-serif;
    ">
        <img src="{a['avatar_url']}" style="
            width:24px;height:24px;border-radius:50%;
            border:2px solid {c};background:#0a0e17;
        " alt="{a['name']}"/>
        <span style="
            font-family:'Exo 2',sans-serif;
            font-size:0.65rem;color:{c};
            letter-spacing:2px;font-weight:700;
        ">{a['icon']} {a['name']}</span>
        <span style="color:#10b981;font-size:0.8rem;">✓</span>
        <span style="
            font-family:'Fira Code',monospace;
            font-size:0.58rem;color:#475569;
        ">DONE</span>
    </div>
    """
    components.html(html, height=40, scrolling=False)


# ──────────────────────────────────────────────
#  MAIN ORCHESTRATOR
# ──────────────────────────────────────────────
def run_osint_audit(target: str, target_type: str):
    """Run all 5 OSINT agents sequentially with live UI feedback."""
    results = {}

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;margin:1rem 0;">
        <span style="
            font-family:'Exo 2',sans-serif;font-size:1.1rem;
            font-weight:900;letter-spacing:5px;
            background:linear-gradient(135deg,#3b82f6,#10b981);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;
        ">⚡ AGENT DEPLOYMENT IN PROGRESS ⚡</span>
    </div>
    """, unsafe_allow_html=True)

    active_box = st.empty()
    completed_container = st.container()
    st.markdown("---")

    pipeline = [
        ("aria",   "domain_recon",    6),
        ("raven",  "threat_intel",    4),
        ("vulcan", "attack_surface",  4),
        ("cipher", "email_osint",     3),
        ("oracle", "final_report",    1),
    ]

    for agent_key, task, max_rounds in pipeline:
        agent = AGENT_PROFILES[agent_key]

        # Show active agent
        with active_box.container():
            render_agent_avatar(agent_key)

        # Build prompts
        system_prompt = (
            f"You are {agent['name']}, a specialist {agent['role']} "
            f"in an elite OSINT team. {agent['description']} "
            f"Always use the provided tools to gather REAL data. "
            f"Never fabricate information. Be thorough and technical."
        )

        if task == "final_report":
            context = "\n\n".join(
                f"### {k.upper()} FINDINGS\n{v}" for k, v in results.items()
            )
            user_prompt = (
                f"Target: {target} ({target_type})\n\n"
                f"Below are the findings from all reconnaissance agents:\n\n"
                f"{context}\n\n"
                f"Produce a comprehensive executive-grade OSINT report with:\n"
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

        # Swap to completed
        active_box.empty()
        with completed_container:
            render_agent_complete(agent_key)

        time.sleep(0.3)

    return results
