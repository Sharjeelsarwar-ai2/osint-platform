import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Kill Streamlit deprecation spam BEFORE importing streamlit
logging.getLogger("streamlit.runtime.scriptrunner").setLevel(logging.ERROR)
logging.getLogger("streamlit").setLevel(logging.ERROR)

import streamlit as st
import streamlit.components.v1 as components
import time
from config.settings import AGENT_PROFILES
from utils.groq_client import run_agent_with_tools
from agents.tools import GROQ_TOOL_DEFINITIONS, execute_tool


def _iframe_css():
    return (
        "@import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@700;900"
        "&family=Space+Grotesk:wght@400;600&family=Fira+Code:wght@400;500&display=swap');"
        "html,body{margin:0;padding:0;background:transparent;overflow:hidden;}"
        "@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}"
        "@keyframes afloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}"
        "@keyframes dotp{0%,80%,100%{transform:scale(0.5);opacity:0.3}40%{transform:scale(1.1);opacity:1}}"
        "@keyframes sglow{0%,100%{opacity:1;box-shadow:0 0 6px #10b981}50%{opacity:0.3;box-shadow:0 0 2px #10b981}}"
        "@keyframes scanm{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}"
    )


def _render_html(html, height):
    """Render HTML — tries st.html() first (new API), falls back to components."""
    try:
        st.html(html, height=height, scrolling=False)
    except (AttributeError, TypeError):
        components.html(html, height=height, scrolling=False)


def render_agent_avatar(agent_key):
    a = AGENT_PROFILES[agent_key]
    c = a["color"]
    css = _iframe_css()
    html = (
        '<style>' + css + '</style>'
        '<div style="display:flex;align-items:center;gap:1.2rem;padding:1rem 1.3rem;'
        'background:linear-gradient(160deg,#11182790,' + c + '08,#0f162980);'
        'border:1px solid ' + c + '30;border-radius:16px;position:relative;overflow:hidden;'
        'font-family:Space Grotesk,sans-serif;">'
        '<div style="position:absolute;top:0;left:0;width:100%;height:2px;'
        'background:linear-gradient(90deg,transparent,' + c + ',transparent);'
        'animation:scanm 2.5s linear infinite;"></div>'
        '<div style="position:relative;width:88px;height:88px;flex-shrink:0;">'
        '<div style="position:absolute;top:-6px;left:-6px;width:100px;height:100px;'
        'border:2px solid transparent;border-top-color:' + c + ';border-right-color:' + c + '50;'
        'border-radius:50%;animation:spin 2s linear infinite;"></div>'
        '<img src="' + a["avatar_url"] + '" style="width:88px;height:88px;border-radius:50%;'
        'border:2px solid ' + c + ';background:#0a0e17;box-shadow:0 0 25px ' + c + '30;'
        'animation:afloat 3s ease-in-out infinite;position:relative;z-index:1;"/>'
        '<div style="position:absolute;bottom:3px;right:3px;width:16px;height:16px;'
        'background:#10b981;border:3px solid #030712;border-radius:50%;z-index:3;'
        'animation:sglow 1s ease-in-out infinite;"></div></div>'
        '<div style="flex:1;">'
        '<div style="display:flex;align-items:center;gap:0.5rem;">'
        '<span style="font-size:1.3rem;">' + a["icon"] + '</span><div>'
        '<div style="font-family:Exo 2,sans-serif;font-size:1.15rem;font-weight:900;'
        'color:' + c + ';letter-spacing:3px;text-shadow:0 0 12px ' + c + '40;">'
        + a["name"] + '</div>'
        '<div style="font-size:0.68rem;color:#94a3b8;letter-spacing:2px;'
        'text-transform:uppercase;">' + a["role"] + '</div></div></div>'
        '<div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.5rem;">'
        '<div style="display:flex;gap:3px;">'
        '<span style="width:6px;height:6px;background:' + c + ';border-radius:50%;animation:dotp 1.4s ease-in-out infinite;animation-delay:0s;"></span>'
        '<span style="width:6px;height:6px;background:' + c + ';border-radius:50%;animation:dotp 1.4s ease-in-out infinite;animation-delay:0.2s;"></span>'
        '<span style="width:6px;height:6px;background:' + c + ';border-radius:50%;animation:dotp 1.4s ease-in-out infinite;animation-delay:0.4s;"></span>'
        '</div>'
        '<span style="font-family:Fira Code,monospace;font-size:0.8rem;color:#e2e8f0;'
        'font-style:italic;">' + a["catchphrase"] + '</span></div>'
        '<div style="margin-top:0.4rem;">'
        '<span style="display:inline-block;padding:2px 10px;background:' + c + '15;'
        'border:1px solid ' + c + ';border-radius:10px;font-family:Fira Code,monospace;'
        'font-size:0.58rem;color:' + c + ';letter-spacing:2px;font-weight:600;">'
        '● EXECUTING</span>'
        '<span style="margin-left:0.5rem;font-family:Fira Code,monospace;'
        'font-size:0.62rem;color:#475569;">Real-world tools in progress…</span>'
        '</div></div></div>'
    )
    _render_html(html, 130)


def render_agent_complete(agent_key):
    a = AGENT_PROFILES[agent_key]
    c = a["color"]
    html = (
        '<style>'
        "@import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@700&display=swap');"
        'html,body{margin:0;padding:0;background:transparent;overflow:hidden;}'
        '</style>'
        '<div style="display:inline-flex;align-items:center;gap:0.5rem;'
        'padding:0.3rem 0.8rem;background:' + c + '08;border:1px solid ' + c + '25;'
        'border-radius:20px;font-family:Space Grotesk,sans-serif;">'
        '<img src="' + a["avatar_url"] + '" style="width:24px;height:24px;'
        'border-radius:50%;border:2px solid ' + c + ';background:#0a0e17;"/>'
        '<span style="font-family:Exo 2,sans-serif;font-size:0.65rem;color:' + c + ';'
        'letter-spacing:2px;font-weight:700;">' + a["icon"] + " " + a["name"] + '</span>'
        '<span style="color:#10b981;font-size:0.8rem;">✓</span>'
        '<span style="font-family:Fira Code,monospace;font-size:0.58rem;color:#475569;">'
        'DONE</span></div>'
    )
    _render_html(html, 40)


def run_osint_audit(target, target_type):
    results = {}
    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;margin:1rem 0;">'
        '<span style="font-family:Exo 2,sans-serif;font-size:1.1rem;font-weight:900;'
        'letter-spacing:5px;background:linear-gradient(135deg,#3b82f6,#10b981);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
        'background-clip:text;">⚡ AGENT DEPLOYMENT IN PROGRESS ⚡</span></div>',
        unsafe_allow_html=True,
    )
    active_box = st.empty()
    done_box = st.container()
    st.markdown("---")

    # OPTIMIZED: reduced rounds for 50% faster execution
    # Old: 6+4+4+3+1 = 18 rounds  →  New: 3+2+2+1+1 = 9 rounds
    pipeline = [
        ("aria",   "domain_recon",    3),
        ("raven",  "threat_intel",    2),
        ("vulcan", "attack_surface",  2),
        ("cipher", "email_osint",     1),
        ("oracle", "final_report",    1),
    ]

    for agent_key, task, max_rounds in pipeline:
        agent = AGENT_PROFILES[agent_key]
        with active_box.container():
            render_agent_avatar(agent_key)

        sys_prompt = (
            "You are " + agent["name"] + ", a specialist " + agent["role"]
            + " in an elite OSINT team. " + agent["description"]
            + " Use the provided tools to gather REAL data."
            + " Be concise but thorough. Prioritize the most impactful tools first."
        )

        if task == "final_report":
            ctx = "\n\n".join("### " + k.upper() + "\n" + v for k, v in results.items())
            usr = (
                "Target: " + target + " (" + target_type + ")\n\n"
                "Agent findings:\n\n" + ctx + "\n\n"
                "Produce an executive OSINT report:\n"
                "1. Executive Summary\n2. Risk Score (0-100)\n"
                "3. Key Findings\n4. Vulnerabilities\n"
                "5. Recommendations\n6. Conclusion"
            )
            finding = run_agent_with_tools(sys_prompt, usr, [], execute_tool, 1)
        else:
            usr = (
                "Perform " + task.replace("_", " ") + " on: " + target
                + " (" + target_type + "). Use the most relevant tools."
                + " Return structured findings."
            )
            finding = run_agent_with_tools(
                sys_prompt, usr, GROQ_TOOL_DEFINITIONS, execute_tool, max_rounds
            )

        results[agent_key] = finding
        active_box.empty()
        with done_box:
            render_agent_complete(agent_key)
        time.sleep(0.2)

    return results
