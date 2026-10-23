import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import time
import json
import re
from datetime import datetime

st.set_page_config(
    page_title="NEXUS • OSINT Intelligence",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from config.settings import GROQ_API_KEY, AGENT_PROFILES, SEVERITY_COLORS, MODEL_NAME
from agents.orchestrator import run_osint_audit


def get_css():
    c = []
    c.append("<style>")
    c.append("@import url('https://fonts.googleapis.com/css2?family=Exo+2:ital,wght@0,300;0,400;0,600;0,700;0,900&family=Space+Grotesk:wght@400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap');")
    c.append(":root{--nx-bg:#030712;--nx-bg2:#0f1629;--nx-card:#111827;--nx-blue:#3b82f6;--nx-emerald:#10b981;--nx-amber:#f59e0b;--nx-rose:#f43f5e;--nx-violet:#8b5cf6;--nx-cyan:#06b6d4;--nx-t1:#f1f5f9;--nx-t2:#94a3b8;--nx-t3:#475569;--nx-border:#1e293b;}")
    c.append(".stApp{background:var(--nx-bg)!important;color:var(--nx-t1)!important;font-family:'Space Grotesk',sans-serif!important;}")
    c.append(".stApp::before{content:'';position:fixed;top:0;left:0;width:100vw;height:100vh;background:radial-gradient(ellipse 80% 50% at 50% -20%,rgba(59,130,246,0.12),transparent),radial-gradient(ellipse 60% 40% at 80% 110%,rgba(16,185,129,0.08),transparent),radial-gradient(ellipse 50% 50% at 10% 50%,rgba(139,92,246,0.06),transparent);pointer-events:none;z-index:0;}")
    c.append(".stApp::after{content:'';position:fixed;top:0;left:0;width:100vw;height:100vh;background-image:linear-gradient(rgba(59,130,246,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(59,130,246,0.03) 1px,transparent 1px);background-size:50px 50px;pointer-events:none;z-index:0;animation:gridDrift 20s linear infinite;}")
    c.append("@keyframes gridDrift{0%{transform:translate(0,0)}100%{transform:translate(50px,50px)}}")
    c.append("header[data-testid='stHeader']{display:none!important}#MainMenu{visibility:hidden!important}footer{visibility:hidden!important}div[data-testid='stDecoration']{display:none!important}.stDeployButton{display:none!important}section[data-testid='stSidebar']{display:none!important}")
    c.append("::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--nx-bg)}::-webkit-scrollbar-thumb{background:linear-gradient(180deg,var(--nx-blue),var(--nx-emerald));border-radius:3px}")
    c.append(".metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:2rem}")
    c.append(".metric-card{background:linear-gradient(145deg,#111827,#0f1629);border:1px solid var(--nx-border);border-radius:16px;padding:1.2rem;position:relative;overflow:hidden;transition:all 0.4s cubic-bezier(0.4,0,0.2,1)}")
    c.append(".metric-card:hover{transform:translateY(-4px);border-color:rgba(59,130,246,0.4);box-shadow:0 20px 40px rgba(0,0,0,0.4),0 0 30px rgba(59,130,246,0.1)}")
    c.append(".agent-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:1rem;margin:1.5rem 0}")
    c.append(".agent-mini{background:linear-gradient(160deg,#111827,#0f1629);border:1px solid var(--nx-border);border-radius:16px;padding:1.2rem 0.8rem;text-align:center;transition:all 0.4s ease;position:relative;overflow:hidden}")
    c.append(".agent-mini:hover{transform:translateY(-6px) scale(1.02);box-shadow:0 15px 40px rgba(0,0,0,0.4)}")
    c.append(".nx-card{background:linear-gradient(160deg,rgba(17,24,39,0.9),rgba(15,22,41,0.7));backdrop-filter:blur(20px);border:1px solid var(--nx-border);border-radius:20px;padding:1.8rem;margin-bottom:1.5rem;position:relative;overflow:hidden;transition:all 0.4s ease}")
    c.append(".nx-card:hover{border-color:rgba(59,130,246,0.3);box-shadow:0 8px 32px rgba(0,0,0,0.3)}")
    c.append(".stTextInput>div>div{background:rgba(15,22,41,0.8)!important;border:1px solid var(--nx-border)!important;border-radius:12px!important;color:var(--nx-t1)!important;font-family:'Fira Code',monospace!important;font-size:1rem!important;padding:0.6rem 1rem!important;transition:all 0.3s ease!important}")
    c.append(".stTextInput>div>div:focus-within{border-color:var(--nx-blue)!important;box-shadow:0 0 20px rgba(59,130,246,0.15)!important}")
    c.append(".stTextInput label,.stSelectbox label{font-family:'Space Grotesk',sans-serif!important;color:var(--nx-t2)!important;font-size:0.8rem!important;letter-spacing:2px!important;text-transform:uppercase!important}")
    c.append(".stSelectbox>div>div{background:rgba(15,22,41,0.8)!important;border:1px solid var(--nx-border)!important;border-radius:12px!important;color:var(--nx-t1)!important;font-family:'Space Grotesk',sans-serif!important}")
    c.append("div.stButton>button{background:linear-gradient(135deg,#3b82f6,#2563eb)!important;color:white!important;font-family:'Exo 2',sans-serif!important;font-size:1.05rem!important;font-weight:700!important;letter-spacing:4px!important;text-transform:uppercase!important;padding:0.85rem 3rem!important;border:none!important;border-radius:14px!important;cursor:pointer!important;transition:all 0.4s cubic-bezier(0.4,0,0.2,1)!important;width:100%!important}")
    c.append("div.stButton>button:hover{background:linear-gradient(135deg,#2563eb,#1d4ed8)!important;transform:translateY(-2px)!important;box-shadow:0 12px 35px rgba(59,130,246,0.35)!important}")
    c.append(".stTabs [data-baseweb='tab-list']{gap:0.5rem;background:transparent;border-bottom:1px solid var(--nx-border)}")
    c.append(".stTabs [data-baseweb='tab']{background:transparent!important;border:1px solid transparent!important;border-radius:10px 10px 0 0!important;color:var(--nx-t3)!important;font-family:'Space Grotesk',sans-serif!important;font-weight:600!important;font-size:0.8rem!important;letter-spacing:1.5px!important;padding:0.7rem 1.4rem!important;transition:all 0.3s ease!important}")
    c.append(".stTabs [data-baseweb='tab']:hover{color:var(--nx-t1)!important;background:rgba(59,130,246,0.08)!important}")
    c.append(".stTabs [aria-selected='true']{background:rgba(59,130,246,0.12)!important;border-color:var(--nx-border)!important;border-bottom-color:var(--nx-bg)!important;color:var(--nx-blue)!important}")
    c.append(".stTabs [data-baseweb='tab-highlight']{background-color:var(--nx-blue)!important}")
    c.append(".streamlit-expanderHeader{background:var(--nx-card)!important;border:1px solid var(--nx-border)!important;border-radius:12px!important;color:var(--nx-t1)!important;font-family:'Space Grotesk',sans-serif!important;font-weight:600!important}")
    c.append(".streamlit-expanderContent{background:var(--nx-bg2)!important;border:1px solid var(--nx-border)!important;border-top:none!important;border-radius:0 0 12px 12px!important}")
    c.append("@media(max-width:768px){.metric-grid{grid-template-columns:repeat(2,1fr)}.agent-grid{grid-template-columns:repeat(2,1fr)}}")
    c.append("</style>")
    return "\n".join(c)


def render_header():
    st.markdown(
        '<div style="position:relative;text-align:center;padding:2rem 1rem 1.5rem;margin-bottom:0.5rem;">'
        '<div style="position:absolute;top:50%;left:50%;width:500px;height:500px;'
        'transform:translate(-50%,-50%);'
        'background:radial-gradient(circle,rgba(59,130,246,0.06),transparent 65%);'
        'pointer-events:none;"></div>'
        '<div style="font-family:Exo 2,sans-serif;font-size:3.2rem;font-weight:900;'
        'letter-spacing:12px;'
        'background:linear-gradient(135deg,#3b82f6,#10b981,#f59e0b);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
        'background-clip:text;position:relative;">'
        '🔮 NEXUS'
        '<div style="position:absolute;bottom:-2px;left:15%;width:70%;height:2px;'
        'background:linear-gradient(90deg,transparent,#3b82f6,#10b981,transparent);">'
        '</div></div>'
        '<div style="font-family:Space Grotesk,sans-serif;font-size:0.8rem;'
        'color:#94a3b8;letter-spacing:6px;text-transform:uppercase;margin-top:0.6rem;">'
        'AI-Powered OSINT &amp; Threat Intelligence Platform</div>'
        '<div style="display:inline-block;margin-top:0.7rem;padding:3px 14px;'
        'background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.25);'
        'border-radius:20px;font-family:Fira Code,monospace;font-size:0.6rem;'
        'color:#3b82f6;letter-spacing:2px;">'
        '<span style="display:inline-block;width:6px;height:6px;background:#10b981;'
        'border-radius:50%;margin-right:6px;box-shadow:0 0 6px #10b981;"></span>'
        'v2.0 • MULTI-AGENT • LIVE RECON</div></div>',
        unsafe_allow_html=True,
    )


def render_metrics():
    now = datetime.now().strftime("%H:%M:%S")
    st.markdown(
        '<div class="metric-grid">'
        '<div class="metric-card" style="border-top:3px solid #3b82f6;">'
        '<div style="font-size:1.8rem;">🤖</div>'
        '<div style="font-family:Exo 2,sans-serif;font-size:1.8rem;font-weight:900;">5</div>'
        '<div style="font-size:0.72rem;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;">Active Agents</div></div>'
        '<div class="metric-card" style="border-top:3px solid #10b981;">'
        '<div style="font-size:1.8rem;">🔧</div>'
        '<div style="font-family:Exo 2,sans-serif;font-size:1.8rem;font-weight:900;">12</div>'
        '<div style="font-size:0.72rem;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;">OSINT Tools</div></div>'
        '<div class="metric-card" style="border-top:3px solid #f59e0b;">'
        '<div style="font-size:1.8rem;">⚡</div>'
        '<div style="font-family:Exo 2,sans-serif;font-size:1rem;font-weight:900;">LLAMA 3.3</div>'
        '<div style="font-size:0.72rem;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;">LLM Engine</div></div>'
        '<div class="metric-card" style="border-top:3px solid #8b5cf6;">'
        '<div style="font-size:1.8rem;">🕐</div>'
        '<div style="font-family:Exo 2,sans-serif;font-size:1.1rem;font-weight:900;">' + now + '</div>'
        '<div style="font-size:0.72rem;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;">Session Time</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_agent_showcase():
    cards = ""
    for key, a in AGENT_PROFILES.items():
        c = a["color"]
        cards += (
            '<div class="agent-mini" style="border-color:' + c + '20;">'
            '<div style="position:absolute;bottom:0;left:0;width:100%;height:3px;'
            'background:linear-gradient(90deg,transparent,' + c + ',transparent);"></div>'
            '<img src="' + a["avatar_url"] + '" style="width:56px;height:56px;'
            'border-radius:50%;border:2px solid ' + c + ';box-shadow:0 0 15px ' + c + '30;'
            'background:#0f1629;margin:0 auto 0.6rem;display:block;"/>'
            '<div style="font-family:Exo 2,sans-serif;font-size:0.8rem;font-weight:700;'
            'letter-spacing:2px;color:' + c + ';">' + a["icon"] + " " + a["name"] + '</div>'
            '<div style="font-family:Space Grotesk,sans-serif;font-size:0.6rem;'
            'color:#94a3b8;letter-spacing:1px;">' + a["role"] + '</div></div>'
        )
    st.markdown('<div class="agent-grid">' + cards + '</div>', unsafe_allow_html=True)


def render_risk_gauge(score):
    if score >= 80:
        color, label = "#f43f5e", "CRITICAL"
    elif score >= 60:
        color, label = "#f59e0b", "HIGH"
    elif score >= 40:
        color, label = "#3b82f6", "MEDIUM"
    elif score >= 20:
        color, label = "#10b981", "LOW"
    else:
        color, label = "#94a3b8", "MINIMAL"
    deg = score * 3.6
    st.markdown(
        '<div style="display:flex;justify-content:center;align-items:center;padding:2rem;">'
        '<div style="width:200px;height:200px;border-radius:50%;position:relative;'
        'display:flex;align-items:center;justify-content:center;'
        'background:conic-gradient(' + color + ' 0deg,' + color + '80 ' + str(deg) + 'deg,'
        '#1e293b ' + str(deg) + 'deg,#1e293b 360deg);'
        'box-shadow:0 0 40px ' + color + '30,inset 0 0 40px rgba(3,7,18,0.8);">'
        '<div style="position:absolute;width:160px;height:160px;'
        'background:#030712;border-radius:50%;"></div>'
        '<div style="font-family:Exo 2,sans-serif;font-size:3.2rem;font-weight:900;'
        'color:' + color + ';position:relative;z-index:2;">' + str(score) + '</div>'
        '<div style="font-family:Space Grotesk,sans-serif;font-size:0.7rem;'
        'color:#94a3b8;letter-spacing:3px;text-transform:uppercase;'
        'position:absolute;bottom:45px;z-index:2;">' + label + ' RISK</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def extract_risk_score(text):
    for p in [r'[Rr]isk\s*[Ss]core[:\s]*(\d{1,3})', r'(\d{1,3})\s*/\s*100',
              r'(\d{1,3})\s*out\s*of\s*100', r'[Ss]core[:\s]*(\d{1,3})']:
        m = re.search(p, text)
        if m and 0 <= int(m.group(1)) <= 100:
            return int(m.group(1))
    return 45


def render_agent_findings(agent_key, content):
    a = AGENT_PROFILES[agent_key]
    c = a["color"]
    st.markdown(
        '<div class="nx-card" style="border-left:4px solid ' + c + ';">'
        '<div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.5rem;">'
        '<img src="' + a["avatar_url"] + '" style="width:36px;height:36px;border-radius:50%;'
        'border:2px solid ' + c + ';background:#0f1629;"/>'
        '<span style="font-family:Exo 2,sans-serif;font-size:1.1rem;font-weight:700;'
        'letter-spacing:3px;color:' + c + ';">' + a["icon"] + " " + a["name"]
        + ' — ' + a["role"] + '</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(content)


def main():
    st.markdown(get_css(), unsafe_allow_html=True)
    render_header()
    render_metrics()

    st.markdown(
        '<div style="font-family:Exo 2,sans-serif;font-size:0.85rem;font-weight:700;'
        'letter-spacing:3px;color:#94a3b8;text-transform:uppercase;'
        'margin-bottom:0.5rem;text-align:center;">'
        '<span style="display:inline-block;width:6px;height:6px;background:#3b82f6;'
        'border-radius:50%;margin-right:8px;box-shadow:0 0 6px #3b82f6;"></span>'
        'AGENT SQUAD — READY FOR DEPLOYMENT</div>',
        unsafe_allow_html=True,
    )
    render_agent_showcase()

    st.markdown(
        '<div style="font-family:Exo 2,sans-serif;font-size:1rem;font-weight:700;'
        'letter-spacing:3px;color:#3b82f6;margin:1.5rem 0 0.8rem;">'
        '🎯 TARGET ACQUISITION</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        target = st.text_input("T", placeholder="e.g. example.com, 192.168.1.1, Acme Corp", label_visibility="collapsed")
    with col2:
        target_type = st.selectbox("Y", ["Domain", "IP Address", "Company"], label_visibility="collapsed")

    launch = st.button("🚀  DEPLOY AGENTS  —  BEGIN RECONNAISSANCE", use_container_width=True)

    api_key = GROQ_API_KEY or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.markdown(
            '<div style="background:rgba(244,63,94,0.08);border:1px solid rgba(244,63,94,0.25);'
            'border-radius:12px;padding:1rem 1.2rem;margin-top:1rem;'
            'font-family:Space Grotesk,sans-serif;color:#f1f5f9;">'
            '<span style="color:#f43f5e;font-weight:700;">⚠ GROQ API KEY REQUIRED</span><br/>'
            '<span style="font-size:0.82rem;color:#94a3b8;">Add your key in Streamlit Cloud → '
            'Settings → Secrets: <code style="background:#1e293b;padding:2px 8px;'
            'border-radius:4px;font-family:Fira Code,monospace;font-size:0.75rem;">'
            'GROQ_API_KEY = "gsk_your_key"</code></span></div>',
            unsafe_allow_html=True,
        )
        return

    if launch and target.strip():
        start_time = time.time()
        results = run_osint_audit(target.strip(), target_type.lower())
        elapsed = round(time.time() - start_time, 1)

        st.markdown(
            '<div style="background:linear-gradient(135deg,rgba(16,185,129,0.1),'
            'rgba(59,130,246,0.1));border:1px solid rgba(16,185,129,0.3);'
            'border-radius:16px;padding:1.2rem 1.5rem;margin:1.5rem 0;text-align:center;">'
            '<span style="font-family:Exo 2,sans-serif;font-size:1.3rem;font-weight:900;'
            'color:#10b981;letter-spacing:3px;">✅ RECONNAISSANCE COMPLETE</span><br/>'
            '<span style="font-family:Fira Code,monospace;font-size:0.8rem;color:#94a3b8;">'
            '5 agents deployed • 12 tools executed • ' + str(elapsed)
            + 's elapsed • Target: ' + target + '</span></div>',
            unsafe_allow_html=True,
        )

        oracle_text = results.get("oracle", "")
        render_risk_gauge(extract_risk_score(oracle_text))

        tab_labels = [AGENT_PROFILES[k]["icon"] + " " + AGENT_PROFILES[k]["name"]
                      for k in ["aria", "raven", "vulcan", "cipher", "oracle"]]
        tabs = st.tabs(tab_labels)
        for tab, key in zip(tabs, ["aria", "raven", "vulcan", "cipher", "oracle"]):
            with tab:
                render_agent_findings(key, results.get(key, "_No data._"))

        st.markdown("---")
        export = {"target": target, "type": target_type,
                  "timestamp": datetime.now().isoformat(),
                  "risk_score": extract_risk_score(oracle_text),
                  "elapsed": elapsed, "model": MODEL_NAME, "findings": results}
        st.download_button(
            "⬇  Download Full Report (JSON)",
            data=json.dumps(export, indent=2, default=str),
            file_name="nexus_" + target.replace(".", "_") + ".json",
            mime="application/json",
            use_container_width=True,
        )

    elif launch:
        st.markdown(
            '<div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);'
            'border-radius:12px;padding:0.8rem 1.2rem;margin-top:1rem;'
            'font-family:Space Grotesk,sans-serif;color:#f59e0b;font-size:0.85rem;">'
            '⚠ Please enter a target.</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div style="text-align:center;margin-top:3rem;padding:1.5rem;'
        'border-top:1px solid #1e293b;">'
        '<span style="font-family:Fira Code,monospace;font-size:0.65rem;'
        'color:#475569;letter-spacing:2px;">'
        'NEXUS COMMAND v2.0 • Multi-Agent OSINT • Groq LLM • Hackathon Edition'
        '</span></div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
