import streamlit as st
import re
import time
from config.settings import GROQ_API_KEY, AGENT_CONFIG, SEVERITY_COLORS
from agents.orchestrator import run_osint_audit
from utils.pdf_generator import generate_pdf

# ── Page Config ──
st.set_page_config(
    page_title="OSINT AI — Threat Intelligence Platform",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Embedded CSS ──
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --bg-primary: #0a0e17;
    --accent-cyan: #00f5d4;
    --accent-green: #00c896;
    --accent-purple: #7c3aed;
    --accent-red: #ff0040;
    --accent-orange: #ff6b35;
    --accent-yellow: #ffd700;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --glow-cyan: 0 0 20px rgba(0,245,212,0.3);
    --glow-purple: 0 0 20px rgba(124,58,237,0.3);
    --glass-bg: rgba(255,255,255,0.03);
    --glass-border: rgba(255,255,255,0.08);
}

.stApp {
    background: var(--bg-primary) !important;
    background-image:
        radial-gradient(ellipse at 10% 20%, rgba(0,245,212,0.03) 0%, transparent 50%),
        radial-gradient(ellipse at 90% 80%, rgba(124,58,237,0.03) 0%, transparent 50%) !important;
    font-family: 'Rajdhani', sans-serif !important;
}

.stApp::before {
    content: '';
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        linear-gradient(rgba(0,245,212,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,245,212,0.03) 1px, transparent 1px);
    background-size: 50px 50px;
    animation: gridMove 20s linear infinite;
    pointer-events: none; z-index: 0;
}

@keyframes gridMove {
    0% { transform: translate(0,0); }
    100% { transform: translate(50px,50px); }
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--accent-cyan), var(--accent-purple));
    border-radius: 3px;
}

.cyber-header { text-align: center; padding: 2rem 0; position: relative; z-index: 1; }

.cyber-header h1 {
    font-family: 'Orbitron', monospace !important;
    font-size: 2.8rem !important; font-weight: 900 !important;
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-green), var(--accent-purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; letter-spacing: 3px;
    animation: titleGlow 3s ease-in-out infinite alternate;
}

@keyframes titleGlow {
    0% { filter: drop-shadow(0 0 10px rgba(0,245,212,0.3)); }
    100% { filter: drop-shadow(0 0 25px rgba(124,58,237,0.4)); }
}

.cyber-header .subtitle {
    font-family: 'Rajdhani', sans-serif; font-size: 1.1rem;
    color: var(--text-secondary); letter-spacing: 5px;
    text-transform: uppercase; font-weight: 300;
}

.shield-icon {
    font-size: 4.5rem; display: block; text-align: center;
    animation: shieldPulse 2s ease-in-out infinite;
    filter: drop-shadow(0 0 30px rgba(0,245,212,0.4));
}

@keyframes shieldPulse {
    0%,100% { transform: scale(1); }
    50% { transform: scale(1.08); }
}

.glass-card {
    background: var(--glass-bg); border: 1px solid var(--glass-border);
    border-radius: 16px; padding: 1.2rem;
    backdrop-filter: blur(20px); transition: all 0.4s ease;
    position: relative; overflow: hidden; margin-bottom: 0.8rem;
}

.glass-card:hover {
    transform: translateY(-3px); border-color: rgba(0,245,212,0.3);
    box-shadow: var(--glow-cyan);
}

.agent-card {
    background: linear-gradient(145deg, rgba(17,24,39,0.9), rgba(30,41,59,0.6));
    border: 1px solid var(--glass-border); border-radius: 16px;
    padding: 1.2rem; text-align: center;
    transition: all 0.5s cubic-bezier(0.175,0.885,0.32,1.275);
    cursor: default;
}

.agent-card:hover {
    transform: translateY(-8px) rotateX(3deg);
    box-shadow: 0 15px 30px rgba(0,0,0,0.3), var(--glow-cyan);
    border-color: var(--accent-cyan);
}

.agent-card .agent-icon {
    font-size: 2rem; display: block; margin-bottom: 0.3rem;
    animation: float 3s ease-in-out infinite;
}

@keyframes float {
    0%,100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
}

.agent-card .agent-name {
    font-family: 'Orbitron', monospace; font-size: 0.7rem;
    font-weight: 700; color: var(--accent-cyan); letter-spacing: 1px;
}

.agent-card .agent-desc {
    font-size: 0.75rem; color: var(--text-secondary); line-height: 1.3;
}

.stTextArea textarea {
    background: rgba(17,24,39,0.8) !important;
    border: 1px solid rgba(0,245,212,0.2) !important;
    border-radius: 12px !important; color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1rem !important; padding: 1rem !important;
}

.stTextArea textarea:focus {
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 0 2px rgba(0,245,212,0.1), var(--glow-cyan) !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-green)) !important;
    color: #0a0e17 !important; font-family: 'Orbitron', monospace !important;
    font-weight: 700 !important; font-size: 1rem !important;
    letter-spacing: 2px !important; padding: 0.8rem 2rem !important;
    border: none !important; border-radius: 12px !important;
    transition: all 0.4s ease !important; text-transform: uppercase !important;
    width: 100% !important;
}

.stButton > button:hover {
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 10px 30px rgba(0,245,212,0.3), var(--glow-cyan) !important;
}

.risk-score-container {
    display: flex; justify-content: center; align-items: center; margin: 1.5rem 0;
}

.risk-score-circle {
    width: 160px; height: 160px; border-radius: 50%;
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    animation: scoreAppear 1s ease-out;
}

.risk-score-circle.critical {
    background: conic-gradient(#ff0040 var(--pct), rgba(255,255,255,0.05) 0);
    box-shadow: 0 0 40px rgba(255,0,64,0.3);
}
.risk-score-circle.high {
    background: conic-gradient(#ff6b35 var(--pct), rgba(255,255,255,0.05) 0);
    box-shadow: 0 0 40px rgba(255,107,53,0.3);
}
.risk-score-circle.medium {
    background: conic-gradient(#ffd700 var(--pct), rgba(255,255,255,0.05) 0);
    box-shadow: 0 0 40px rgba(255,215,0,0.3);
}
.risk-score-circle.low {
    background: conic-gradient(#00f5d4 var(--pct), rgba(255,255,255,0.05) 0);
    box-shadow: 0 0 40px rgba(0,245,212,0.3);
}

.risk-score-inner {
    width: 125px; height: 125px; border-radius: 50%;
    background: var(--bg-primary);
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
}

.risk-score-value {
    font-family: 'Orbitron', monospace; font-size: 2.2rem; font-weight: 900;
}

.risk-score-label {
    font-family: 'Rajdhani', sans-serif; font-size: 0.7rem;
    color: var(--text-secondary); text-transform: uppercase; letter-spacing: 2px;
}

@keyframes scoreAppear {
    0% { transform: scale(0) rotate(-180deg); opacity: 0; }
    100% { transform: scale(1) rotate(0deg); opacity: 1; }
}

.stat-card {
    background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(30,41,59,0.7));
    border: 1px solid var(--glass-border); border-radius: 14px;
    padding: 1.2rem; text-align: center; transition: all 0.4s ease;
}

.stat-card:hover {
    transform: translateY(-4px); box-shadow: var(--glow-cyan);
    border-color: rgba(0,245,212,0.3);
}

.stat-card .stat-value {
    font-family: 'Orbitron', monospace; font-size: 1.8rem; font-weight: 900;
}

.stat-card .stat-label {
    font-family: 'Rajdhani', sans-serif; font-size: 0.8rem;
    color: var(--text-secondary); text-transform: uppercase; letter-spacing: 2px;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: rgba(17,24,39,0.5); border-radius: 12px; padding: 4px;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important; border-radius: 10px !important;
    color: var(--text-secondary) !important;
    font-family: 'Orbitron', monospace !important; font-size: 0.65rem !important;
    letter-spacing: 1px !important; padding: 8px 12px !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(0,245,212,0.1) !important;
    color: var(--accent-cyan) !important;
    border-bottom: 2px solid var(--accent-cyan) !important;
}

.stTabs [data-baseweb="tab-panel"] {
    background: var(--glass-bg); border: 1px solid var(--glass-border);
    border-radius: 0 0 12px 12px; padding: 1.5rem;
}

.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Orbitron', monospace !important; color: var(--accent-cyan) !important;
}

.stMarkdown p, .stMarkdown li {
    color: var(--text-primary) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1rem !important; line-height: 1.7 !important;
}

.stMarkdown code {
    background: rgba(0,245,212,0.1) !important; color: var(--accent-cyan) !important;
    padding: 2px 8px !important; border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

.stMarkdown th {
    background: rgba(0,245,212,0.1) !important; color: var(--accent-cyan) !important;
    font-family: 'Orbitron', monospace !important; font-size: 0.7rem !important;
    padding: 8px !important; border-bottom: 2px solid rgba(0,245,212,0.3) !important;
}

.stMarkdown td {
    padding: 6px 8px !important; border-bottom: 1px solid var(--glass-border) !important;
    color: var(--text-primary) !important;
}

.scanner-line {
    width: 100%; height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent);
    animation: scan 2s ease-in-out infinite; margin: 1rem 0;
}

@keyframes scan {
    0% { transform: translateX(-100%); opacity: 0; }
    50% { opacity: 1; }
    100% { transform: translateX(100%); opacity: 0; }
}

@keyframes pulse {
    0%,100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.5); opacity: 0.5; }
}

.cyber-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-cyan), var(--accent-purple), transparent);
    margin: 2rem 0; border: none;
}

.stDownloadButton > button {
    background: linear-gradient(135deg, var(--accent-purple), #9333ea) !important;
    color: white !important; font-family: 'Orbitron', monospace !important;
    font-weight: 700 !important; letter-spacing: 1px !important;
    border: none !important; border-radius: 12px !important;
    padding: 0.7rem 2rem !important; width: 100% !important;
}

.stDownloadButton > button:hover {
    transform: translateY(-2px) !important; box-shadow: var(--glow-purple) !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(10,14,23,0.98), rgba(17,24,39,0.95)) !important;
    border-right: 1px solid var(--glass-border) !important;
}

.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple)) !important;
}

.stSpinner > div { border-top-color: var(--accent-cyan) !important; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

.cyber-footer {
    text-align: center; padding: 2rem 0; margin-top: 3rem;
    border-top: 1px solid var(--glass-border);
}

.cyber-footer .tech-badge {
    background: rgba(0,245,212,0.05); border: 1px solid rgba(0,245,212,0.15);
    border-radius: 20px; padding: 4px 12px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--accent-cyan);
}

@media (max-width: 768px) {
    .cyber-header h1 { font-size: 1.6rem !important; }
    .risk-score-circle { width: 120px; height: 120px; }
    .risk-score-inner { width: 95px; height: 95px; }
    .risk-score-value { font-size: 1.6rem; }
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ── Helper Functions ──
def extract_risk_score(report: str) -> int:
    for pattern in [r'Overall Risk Score[:\s]*(\d+)\s*/\s*100', r'Risk Score[:\s]*(\d+)', r'(\d+)\s*/\s*100']:
        m = re.search(pattern, report, re.IGNORECASE)
        if m and 0 <= int(m.group(1)) <= 100:
            return int(m.group(1))
    return 55


def extract_grade(report: str) -> str:
    for pattern in [r'Security Grade[:\s]*([A-F][+-]?)', r'Grade[:\s]*([A-F][+-]?)']:
        m = re.search(pattern, report, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return "B"


def get_risk_info(score: int):
    if score >= 75:
        return "CRITICAL", "#ff0040", "critical"
    elif score >= 50:
        return "HIGH", "#ff6b35", "high"
    elif score >= 25:
        return "MEDIUM", "#ffd700", "medium"
    return "LOW", "#00f5d4", "low"


def count_severity(results: dict) -> dict:
    text = " ".join(results.values()).upper()
    return {
        "critical": len(re.findall(r'\bCRITICAL\b', text)),
        "high": len(re.findall(r'\bHIGH\b', text)),
        "medium": len(re.findall(r'\bMEDIUM\b', text)),
        "low": len(re.findall(r'\bLOW\b', text))
    }


# ── Sidebar ──
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1rem 0;">
        <div style="font-size:3rem;">🕵️</div>
        <h2 style="font-family:'Orbitron',monospace;
                   background:linear-gradient(135deg,#00f5d4,#7c3aed);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   font-size:1.1rem;margin:0;">OSINT AI</h2>
        <p style="color:#64748b;font-size:0.75rem;letter-spacing:2px;">THREAT INTELLIGENCE</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="cyber-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 🤖 Agent Team")

    for key, agent in AGENT_CONFIG.items():
        st.markdown(f"""
        <div class="glass-card" style="padding:0.7rem;border-left:3px solid {agent['color']};">
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:1.2rem;">{agent['icon']}</span>
                <div>
                    <div style="font-family:'Orbitron',monospace;font-size:0.6rem;
                                color:{agent['color']};font-weight:700;">{agent['name'].upper()}</div>
                    <div style="font-size:0.7rem;color:#94a3b8;">{agent['description']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="cyber-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 🔧 Real Tools Used")
    tools_list = [
        "🌐 DNS Resolver (dnspython)",
        "📋 WHOIS Lookup (python-whois)",
        "🔒 SSL/TLS Inspector (ssl)",
        "🛡️ HTTP Header Scanner",
        "🔍 DuckDuckGo Search",
        "📧 Email Security (SPF/DMARC)",
        "🖥️ Tech Stack Detector",
        "📍 IP Analyzer (ipaddress)"
    ]
    for tool in tools_list:
        st.markdown(f"<p style='color:#94a3b8;font-size:0.75rem;margin:2px 0;'>{tool}</p>", unsafe_allow_html=True)

    st.markdown('<div class="cyber-divider"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center;">
        <p style="color:#475569;font-size:0.65rem;font-style:italic;">
            ⚠️ For authorized security testing only.<br>
            Always obtain proper authorization.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── Main Content ──
st.markdown("""
<div class="cyber-header">
    <span class="shield-icon">🕵️</span>
    <h1>OSINT AI</h1>
    <p class="subtitle">Multi-Agent Threat Intelligence Platform</p>
    <div class="scanner-line"></div>
</div>
""", unsafe_allow_html=True)

# ── Agent Showcase ──
cols = st.columns(5)
for i, (key, agent) in enumerate(AGENT_CONFIG.items()):
    with cols[i]:
        st.markdown(f"""
        <div class="agent-card">
            <span class="agent-icon">{agent['icon']}</span>
            <div class="agent-name">{agent['name'].upper()}</div>
            <div class="agent-desc">{agent['description']}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="cyber-divider"></div>', unsafe_allow_html=True)

# ── Input Section ──
st.markdown("""
<div style="text-align:center;margin-bottom:1rem;">
    <h3 style="font-family:'Orbitron',monospace;color:#00f5d4;
               font-size:1rem;letter-spacing:2px;">
        🎯 ENTER TARGET FOR RECONNAISSANCE
    </h3>
    <p style="color:#64748b;font-size:0.9rem;">
        Enter a domain name, IP address, or company name
    </p>
</div>
""", unsafe_allow_html=True)

target_input = st.text_input(
    label="target",
    label_visibility="collapsed",
    placeholder="e.g. tesla.com, 8.8.8.8, microsoft.com, github.com",
    key="target_input"
)

target_type = st.selectbox(
    "Target Type",
    ["Domain", "IP Address", "Company Name"],
    index=0,
    key="target_type"
)

# ── Example Targets ──
with st.expander("💡 Click for example targets"):
    ex_col1, ex_col2, ex_col3 = st.columns(3)
    with ex_col1:
        st.markdown("""
        <div class="glass-card" style="padding:0.8rem;">
            <div style="font-family:'Orbitron',monospace;font-size:0.7rem;color:#00f5d4;">🌐 DOMAINS</div>
            <p style="color:#94a3b8;font-size:0.8rem;margin:0.3rem 0 0 0;">
                tesla.com<br>github.com<br>stripe.com<br>cloudflare.com
            </p>
        </div>
        """, unsafe_allow_html=True)
    with ex_col2:
        st.markdown("""
        <div class="glass-card" style="padding:0.8rem;">
            <div style="font-family:'Orbitron',monospace;font-size:0.7rem;color:#ff0040;">📍 IP ADDRESSES</div>
            <p style="color:#94a3b8;font-size:0.8rem;margin:0.3rem 0 0 0;">
                8.8.8.8 (Google DNS)<br>1.1.1.1 (Cloudflare)<br>13.107.42.14 (Microsoft)
            </p>
        </div>
        """, unsafe_allow_html=True)
    with ex_col3:
        st.markdown("""
        <div class="glass-card" style="padding:0.8rem;">
            <div style="font-family:'Orbitron',monospace;font-size:0.7rem;color:#7c3aed;">🏢 COMPANIES</div>
            <p style="color:#94a3b8;font-size:0.8rem;margin:0.3rem 0 0 0;">
                Apple Inc<br>Amazon Web Services<br>Meta Platforms
            </p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("")

# ── Launch Button ──
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    launch = st.button("🚀  LAUNCH OSINT RECONNAISSANCE", use_container_width=True)

# ── Execution ──
if launch:
    if not GROQ_API_KEY:
        st.error("⚠️ **GROQ_API_KEY not found!** Add it to Streamlit Secrets or `.env` file.")
        st.code("GROQ_API_KEY=gsk_your_key_here", language="bash")
        st.stop()

    if not target_input or len(target_input.strip()) < 3:
        st.warning("⚠️ Please enter a valid target (at least 3 characters).")
        st.stop()

    target = target_input.strip().lower()

    st.markdown('<div class="cyber-divider"></div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align:center;margin:1rem 0;">
        <h2 style="font-family:'Orbitron',monospace;color:#00f5d4;
                   font-size:1.1rem;letter-spacing:3px;">
            🔄 RECONNAISSANCE IN PROGRESS
        </h2>
        <p style="color:#94a3b8;font-size:0.9rem;">Target: <strong style="color:#00f5d4;">{target}</strong></p>
        <div class="scanner-line"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Run All Agents ──
    start_time = time.time()
    results = run_osint_audit(target, target_type)
    elapsed = time.time() - start_time

    # ── Success Banner ──
    st.markdown(f"""
    <div class="glass-card" style="text-align:center;border-color:rgba(0,245,212,0.4);
                                    background:rgba(0,245,212,0.03);">
        <h2 style="font-family:'Orbitron',monospace;color:#00f5d4;margin:0 0 0.5rem 0;">
            ✅ RECONNAISSANCE COMPLETE
        </h2>
        <p style="color:#94a3b8;margin:0;">
            5 agents analyzed <strong style="color:#00f5d4;">{target}</strong>
            in <strong style="color:#00f5d4;">{elapsed:.1f}s</strong>
            using real DNS, WHOIS, SSL, and threat intel tools
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="cyber-divider"></div>', unsafe_allow_html=True)

    # ── Extract Metrics ──
    risk_score = extract_risk_score(results.get("final_report", ""))
    grade = extract_grade(results.get("final_report", ""))
    risk_level, risk_color, risk_class = get_risk_info(risk_score)
    findings = count_severity(results)

    # ── Dashboard Header ──
    st.markdown("""
    <div style="text-align:center;margin-bottom:1.5rem;">
        <h3 style="font-family:'Orbitron',monospace;color:#94a3b8;
                   font-size:0.9rem;letter-spacing:3px;">
            ── THREAT INTELLIGENCE DASHBOARD ──
        </h3>
    </div>
    """, unsafe_allow_html=True)

    # ── Risk Score Circles ──
    s1, s2, s3 = st.columns([1, 1, 1])

    with s1:
        st.markdown(f"""
        <div class="risk-score-container">
            <div class="risk-score-circle {risk_class}" style="--pct:{risk_score}%;">
                <div class="risk-score-inner">
                    <div class="risk-score-value" style="color:{risk_color};">{risk_score}</div>
                    <div class="risk-score-label">Risk Score</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with s2:
        st.markdown(f"""
        <div class="risk-score-container">
            <div class="risk-score-circle {risk_class}" style="--pct:{100 - risk_score}%;">
                <div class="risk-score-inner">
                    <div class="risk-score-value" style="color:{risk_color};">{grade}</div>
                    <div class="risk-score-label">Security Grade</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with s3:
        st.markdown(f"""
        <div class="risk-score-container">
            <div class="risk-score-circle {risk_class}" style="--pct:{risk_score}%;">
                <div class="risk-score-inner">
                    <div class="risk-score-value" style="color:{risk_color};font-size:1.4rem;">{risk_level}</div>
                    <div class="risk-score-label">Threat Level</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Findings Stats ──
    st.markdown("")
    f1, f2, f3, f4 = st.columns(4)

    with f1:
        st.markdown(f"""
        <div class="stat-card" style="border-top:3px solid #ff0040;">
            <div class="stat-value" style="color:#ff0040;">{findings['critical']}</div>
            <div class="stat-label">Critical</div>
        </div>
        """, unsafe_allow_html=True)

    with f2:
        st.markdown(f"""
        <div class="stat-card" style="border-top:3px solid #ff6b35;">
            <div class="stat-value" style="color:#ff6b35;">{findings['high']}</div>
            <div class="stat-label">High</div>
        </div>
        """, unsafe_allow_html=True)

    with f3:
        st.markdown(f"""
        <div class="stat-card" style="border-top:3px solid #ffd700;">
            <div class="stat-value" style="color:#ffd700;">{findings['medium']}</div>
            <div class="stat-label">Medium</div>
        </div>
        """, unsafe_allow_html=True)

    with f4:
        st.markdown(f"""
        <div class="stat-card" style="border-top:3px solid #00d4aa;">
            <div class="stat-value" style="color:#00d4aa;">{findings['low']}</div>
            <div class="stat-label">Low</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="cyber-divider"></div>', unsafe_allow_html=True)

    # ── Detailed Results Tabs ──
    st.markdown("""
    <div style="text-align:center;margin-bottom:1rem;">
        <h3 style="font-family:'Orbitron',monospace;color:#94a3b8;
                   font-size:0.9rem;letter-spacing:3px;">
            ── DETAILED INTELLIGENCE REPORTS ──
        </h3>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "📊 Executive Report",
        "🌐 Domain Recon",
        "🔍 Threat Intel",
        "🗺️ Attack Surface",
        "📧 Email OSINT"
    ])

    with tabs[0]:
        st.markdown(results.get("final_report", "No report generated."))

    with tabs[1]:
        st.markdown(results.get("domain_recon", "No domain recon generated."))

    with tabs[2]:
        st.markdown(results.get("threat_intel", "No threat intel generated."))

    with tabs[3]:
        st.markdown(results.get("attack_surface", "No attack surface analysis generated."))

    with tabs[4]:
        st.markdown(results.get("email_osint", "No email OSINT generated."))

    st.markdown('<div class="cyber-divider"></div>', unsafe_allow_html=True)

    # ── PDF Export ──
    st.markdown("""
    <div style="text-align:center;margin-bottom:1rem;">
        <h3 style="font-family:'Orbitron',monospace;color:#7c3aed;
                   font-size:0.9rem;letter-spacing:3px;">
            📥 EXPORT INTELLIGENCE REPORT
        </h3>
    </div>
    """, unsafe_allow_html=True)

    dl1, dl2, dl3 = st.columns([1, 2, 1])
    with dl2:
        try:
            pdf_bytes = generate_pdf(results)
            st.download_button(
                label="⬇️  DOWNLOAD PDF REPORT",
                data=pdf_bytes,
                file_name=f"OSINT_Report_{target.replace('.', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF generation error: {e}")


# ── Footer ──
st.markdown("""
<div class="cyber-footer">
    <p style="color:#94a3b8;font-size:0.85rem;letter-spacing:1px;">
        Built with ❤️ by <strong style="color:#00f5d4;">OSINT AI</strong>
    </p>
    <div style="display:flex;justify-content:center;gap:0.8rem;margin-top:0.5rem;flex-wrap:wrap;">
        <span class="tech-badge">Python</span>
        <span class="tech-badge">Streamlit</span>
        <span class="tech-badge">Groq</span>
        <span class="tech-badge">LLaMA 3.3</span>
        <span class="tech-badge">dnspython</span>
        <span class="tech-badge">WHOIS</span>
        <span class="tech-badge">DuckDuckGo</span>
        <span class="tech-badge">Multi-Agent</span>
    </div>
    <p style="color:#475569;font-size:0.7rem;margin-top:1rem;">
        ⚠️ For authorized security testing and educational purposes only.
    </p>
</div>
""", unsafe_allow_html=True)