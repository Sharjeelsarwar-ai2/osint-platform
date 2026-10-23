"""
NEXUS COMMAND — AI OSINT & Threat Intelligence Platform
Hackathon-grade holographic UI with live multi-agent visualization
"""

import streamlit as st
import streamlit.components.v1 as components
import time
import json
import re
from datetime import datetime

# ── Page config MUST be first ──
st.set_page_config(
    page_title="NEXUS • OSINT Intelligence",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from config.settings import GROQ_API_KEY, AGENT_PROFILES, SEVERITY_COLORS, MODEL_NAME
from agents.orchestrator import run_osint_audit

# ──────────────────────────────────────────────────────────
#  NEXUS DESIGN SYSTEM — Complete Embedded CSS
# ──────────────────────────────────────────────────────────
NEXUS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Exo+2:ital,wght@0,300;0,400;0,600;0,700;0,900&family=Space+Grotesk:wght@400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap');

/* ── ROOT VARIABLES ── */
:root {
    --nx-bg-primary: #030712;
    --nx-bg-secondary: #0f1629;
    --nx-bg-card: #111827;
    --nx-accent-blue: #3b82f6;
    --nx-accent-emerald: #10b981;
    --nx-accent-amber: #f59e0b;
    --nx-accent-rose: #f43f5e;
    --nx-accent-violet: #8b5cf6;
    --nx-accent-cyan: #06b6d4;
    --nx-text-primary: #f1f5f9;
    --nx-text-secondary: #94a3b8;
    --nx-text-muted: #475569;
    --nx-border: #1e293b;
    --nx-glow-blue: rgba(59, 130, 246, 0.4);
    --nx-glow-emerald: rgba(16, 185, 129, 0.4);
}

/* ── GLOBAL RESET ── */
.stApp {
    background: var(--nx-bg-primary) !important;
    color: var(--nx-text-primary) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    background:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59,130,246,0.12), transparent),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(16,185,129,0.08), transparent),
        radial-gradient(ellipse 50% 50% at 10% 50%, rgba(139,92,246,0.06), transparent);
    pointer-events: none;
    z-index: 0;
}

/* ── PARTICLE GRID BACKGROUND ── */
.stApp::after {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    background-image:
        linear-gradient(rgba(59,130,246,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(59,130,246,0.03) 1px, transparent 1px);
    background-size: 50px 50px;
    pointer-events: none;
    z-index: 0;
    animation: gridDrift 20s linear infinite;
}

@keyframes gridDrift {
    0% { transform: translate(0,0); }
    100% { transform: translate(50px,50px); }
}

/* ── HIDE STREAMLIT DEFAULTS ── */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { visibility: hidden !important; }
footer { visibility: hidden !important; }
div[data-testid="stDecoration"] { display: none !important; }
.stDeployButton { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--nx-bg-primary); }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--nx-accent-blue), var(--nx-accent-emerald));
    border-radius: 3px;
}

/* ── NEXUS HEADER ── */
.nexus-header {
    position: relative;
    text-align: center;
    padding: 2.5rem 1rem 2rem;
    margin-bottom: 2rem;
    overflow: hidden;
}

.nexus-header::before {
    content: '';
    position: absolute;
    top: 50%; left: 50%;
    width: 600px; height: 600px;
    transform: translate(-50%, -50%);
    background: radial-gradient(circle, rgba(59,130,246,0.08), transparent 60%);
    pointer-events: none;
}

.nexus-logo {
    font-family: 'Exo 2', sans-serif;
    font-size: 3.5rem;
    font-weight: 900;
    letter-spacing: 12px;
    background: linear-gradient(135deg, #3b82f6, #10b981, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
    position: relative;
    display: inline-block;
}

.nexus-logo::after {
    content: '';
    position: absolute;
    bottom: -4px; left: 10%;
    width: 80%; height: 2px;
    background: linear-gradient(90deg, transparent, #3b82f6, #10b981, transparent);
}

.nexus-subtitle {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.85rem;
    color: var(--nx-text-secondary);
    letter-spacing: 6px;
    text-transform: uppercase;
    margin-top: 0.6rem;
}

.nexus-version {
    display: inline-block;
    margin-top: 0.8rem;
    padding: 3px 14px;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.25);
    border-radius: 20px;
    font-family: 'Fira Code', monospace;
    font-size: 0.65rem;
    color: var(--nx-accent-blue);
    letter-spacing: 2px;
}

/* ── METRIC CARDS ── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
}

.metric-card {
    background: linear-gradient(145deg, #111827, #0f1629);
    border: 1px solid var(--nx-border);
    border-radius: 16px;
    padding: 1.2rem;
    position: relative;
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 3px;
    border-radius: 16px 16px 0 0;
}

.metric-card:hover {
    transform: translateY(-4px);
    border-color: rgba(59,130,246,0.4);
    box-shadow: 0 20px 40px rgba(0,0,0,0.4), 0 0 30px rgba(59,130,246,0.1);
}

.metric-card .mc-icon {
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
}

.metric-card .mc-value {
    font-family: 'Exo 2', sans-serif;
    font-size: 1.8rem;
    font-weight: 900;
    color: var(--nx-text-primary);
    line-height: 1;
}

.metric-card .mc-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.72rem;
    color: var(--nx-text-secondary);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 0.3rem;
}

/* ── NEXUS CARD (glass) ── */
.nx-card {
    background: linear-gradient(160deg, rgba(17,24,39,0.9), rgba(15,22,41,0.7));
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--nx-border);
    border-radius: 20px;
    padding: 1.8rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    transition: all 0.4s ease;
}

.nx-card:hover {
    border-color: rgba(59,130,246,0.3);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 0 60px rgba(59,130,246,0.02);
}

.nx-card-title {
    font-family: 'Exo 2', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 3px;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}

/* ── INPUT AREA ── */
.nx-input-wrapper {
    background: linear-gradient(160deg, rgba(17,24,39,0.95), rgba(15,22,41,0.8));
    border: 1px solid var(--nx-border);
    border-radius: 24px;
    padding: 2rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}

.nx-input-wrapper::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: linear-gradient(135deg, rgba(59,130,246,0.03), transparent, rgba(16,185,129,0.03));
    pointer-events: none;
}

/* ── STREAMLIT INPUT OVERRIDES ── */
.stTextInput > div > div {
    background: rgba(15, 22, 41, 0.8) !important;
    border: 1px solid var(--nx-border) !important;
    border-radius: 12px !important;
    color: var(--nx-text-primary) !important;
    font-family: 'Fira Code', monospace !important;
    font-size: 1rem !important;
    padding: 0.6rem 1rem !important;
    transition: all 0.3s ease !important;
}

.stTextInput > div > div:focus-within {
    border-color: var(--nx-accent-blue) !important;
    box-shadow: 0 0 20px rgba(59,130,246,0.15) !important;
}

.stTextInput label {
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--nx-text-secondary) !important;
    font-size: 0.8rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}

.stSelectbox > div > div {
    background: rgba(15, 22, 41, 0.8) !important;
    border: 1px solid var(--nx-border) !important;
    border-radius: 12px !important;
    color: var(--nx-text-primary) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

.stSelectbox label {
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--nx-text-secondary) !important;
    font-size: 0.8rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}

/* ── LAUNCH BUTTON ── */
div.stButton > button {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    color: white !important;
    font-family: 'Exo 2', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    letter-spacing: 4px !important;
    text-transform: uppercase !important;
    padding: 0.85rem 3rem !important;
    border: none !important;
    border-radius: 14px !important;
    cursor: pointer !important;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
    width: 100% !important;
}

div.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 35px rgba(59,130,246,0.35) !important;
}

div.stButton > button:active {
    transform: translateY(0px) !important;
}

/* ── EXPANDER OVERRIDES ── */
.streamlit-expanderHeader {
    background: var(--nx-bg-card) !important;
    border: 1px solid var(--nx-border) !important;
    border-radius: 12px !important;
    color: var(--nx-text-primary) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
}

.streamlit-expanderContent {
    background: var(--nx-bg-secondary) !important;
    border: 1px solid var(--nx-border) !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
}

/* ── RESULTS TABS ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: transparent;
    border-bottom: 1px solid var(--nx-border);
    padding-bottom: 0;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 10px 10px 0 0 !important;
    color: var(--nx-text-muted) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    letter-spacing: 1.5px !important;
    padding: 0.7rem 1.4rem !important;
    transition: all 0.3s ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--nx-text-primary) !important;
    background: rgba(59,130,246,0.08) !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(59,130,246,0.12) !important;
    border-color: var(--nx-border) !important;
    border-bottom-color: var(--nx-bg-primary) !important;
    color: var(--nx-accent-blue) !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--nx-accent-blue) !important;
}

/* ── AGENT TEAM GRID ── */
.agent-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 1rem;
    margin: 1.5rem 0;
}

.agent-mini-card {
    background: linear-gradient(160deg, #111827, #0f1629);
    border: 1px solid var(--nx-border);
    border-radius: 16px;
    padding: 1.2rem 0.8rem;
    text-align: center;
    transition: all 0.4s ease;
    position: relative;
    overflow: hidden;
}

.agent-mini-card::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0;
    width: 100%; height: 3px;
    border-radius: 0 0 16px 16px;
}

.agent-mini-card:hover {
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 15px 40px rgba(0,0,0,0.4);
}

.agent-mini-card .amc-avatar {
    width: 56px; height: 56px;
    border-radius: 50%;
    margin: 0 auto 0.6rem;
    display: block;
}

.agent-mini-card .amc-name {
    font-family: 'Exo 2', sans-serif;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 2px;
    margin-bottom: 0.2rem;
}

.agent-mini-card .amc-role {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6rem;
    color: var(--nx-text-secondary);
    letter-spacing: 1px;
}

/* ── RISK GAUGE ── */
.risk-gauge-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 2rem;
}

.risk-gauge {
    width: 200px; height: 200px;
    border-radius: 50%;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
}

.risk-gauge .rg-score {
    font-family: 'Exo 2', sans-serif;
    font-size: 3.2rem;
    font-weight: 900;
    position: relative;
    z-index: 2;
}

.risk-gauge .rg-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.7rem;
    color: var(--nx-text-secondary);
    letter-spacing: 3px;
    text-transform: uppercase;
    position: absolute;
    bottom: 45px;
    z-index: 2;
}

/* ── FINDING CARD ── */
.finding-card {
    background: linear-gradient(160deg, #111827, #0f1629);
    border-left: 4px solid;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    transition: all 0.3s ease;
}

.finding-card:hover {
    transform: translateX(4px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.finding-title {
    font-family: 'Exo 2', sans-serif;
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 0.4rem;
}

.finding-detail {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.82rem;
    color: var(--nx-text-secondary);
    line-height: 1.6;
}

/* ── SEVERITY BADGES ── */
.severity-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 8px;
    font-family: 'Fira Code', monospace;
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.severity-critical { background: rgba(244,63,94,0.15); color: #f43f5e; border: 1px solid rgba(244,63,94,0.3); }
.severity-high     { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
.severity-medium   { background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3); }
.severity-low      { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
.severity-info     { background: rgba(148,163,184,0.1); color: #94a3b8; border: 1px solid rgba(148,163,184,0.2); }

/* ── LIVE PULSE DOT ── */
.pulse-dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: #10b981;
    border-radius: 50%;
    margin-right: 6px;
    animation: pulseDot 2s ease-in-out infinite;
}

@keyframes pulseDot {
    0%, 100% { opacity: 1; box-shadow: 0 0 4px #10b981; }
    50%      { opacity: 0.4; box-shadow: 0 0 12px #10b981; }
}

/* ── LOADING SHIMMER ── */
@keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.shimmer-line {
    height: 12px;
    border-radius: 6px;
    background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
    margin-bottom: 0.5rem;
}

/* ── RESPONSIVE ── */
@media (max-width: 768px) {
    .metric-grid { grid-template-columns: repeat(2, 1fr); }
    .agent-grid { grid-template-columns: repeat(2, 1fr); }
    .nexus-logo { font-size: 2rem; letter-spacing: 6px; }
}
</style>
"""


# ──────────────────────────────────────────────────────────
#  HELPER: Render Agent Team Showcase (HTML)
# ──────────────────────────────────────────────────────────
def render_agent_showcase():
    """Display the 5-agent team as interactive cards."""
    cards_html = ""
    for key, a in AGENT_PROFILES.items():
        c = a["color"]
        cards_html += f"""
        <div class="agent-mini-card" style="border-color:{c}20;"
             onmouseover="this.style.borderColor='{c}60'"
             onmouseout="this.style.borderColor='{c}20'">
            <div style="position:absolute;bottom:0;left:0;width:100%;height:3px;
                        background:linear-gradient(90deg,transparent,{c},transparent);"></div>
            <img src="{a['avatar_url']}" class="amc-avatar"
                 style="border:2px solid {c};box-shadow:0 0 15px {c}30;background:#0f1629;" />
            <div class="amc-name" style="color:{c};">{a['icon']} {a['name']}</div>
            <div class="amc-role">{a['role']}</div>
        </div>
        """

    st.markdown(f'<div class="agent-grid">{cards_html}</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  HELPER: Render Live Metrics Bar
# ──────────────────────────────────────────────────────────
def render_metrics_bar():
    """Top metrics bar with live indicators."""
    now = datetime.now().strftime("%H:%M:%S UTC")
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card" style="border-top:3px solid var(--nx-accent-blue);">
            <div class="mc-icon">🤖</div>
            <div class="mc-value">5</div>
            <div class="mc-label">Active Agents</div>
        </div>
        <div class="metric-card" style="border-top:3px solid var(--nx-accent-emerald);">
            <div class="mc-icon">🔧</div>
            <div class="mc-value">12</div>
            <div class="mc-label">OSINT Tools</div>
        </div>
        <div class="metric-card" style="border-top:3px solid var(--nx-accent-amber);">
            <div class="mc-icon">⚡</div>
            <div class="mc-value">{MODEL_NAME.split('-')[0].upper()}</div>
            <div class="mc-label">LLM Engine</div>
        </div>
        <div class="metric-card" style="border-top:3px solid var(--nx-accent-violet);">
            <div class="mc-icon">🕐</div>
            <div class="mc-value" style="font-size:1.1rem;">{now}</div>
            <div class="mc-label">Session Time</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  HELPER: Risk Score Gauge
# ──────────────────────────────────────────────────────────
def render_risk_gauge(score: int):
    """Render a circular risk gauge."""
    if score >= 80:
        color = "#f43f5e"
        label = "CRITICAL"
    elif score >= 60:
        color = "#f59e0b"
        label = "HIGH"
    elif score >= 40:
        color = "#3b82f6"
        label = "MEDIUM"
    elif score >= 20:
        color = "#10b981"
        label = "LOW"
    else:
        color = "#94a3b8"
        label = "MINIMAL"

    gauge_html = f"""
    <div class="risk-gauge-container">
        <div class="risk-gauge" style="
            background: conic-gradient(
                {color} 0deg,
                {color}80 {score * 3.6}deg,
                #1e293b {score * 3.6}deg,
                #1e293b 360deg
            );
            box-shadow: 0 0 40px {color}30, inset 0 0 40px rgba(3,7,18,0.8);
        ">
            <div style="
                position:absolute; width:160px; height:160px;
                background: var(--nx-bg-primary);
                border-radius: 50%;
            "></div>
            <div class="rg-score" style="color:{color};">{score}</div>
            <div class="rg-label">{label} RISK</div>
        </div>
    </div>
    """
    st.markdown(gauge_html, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  HELPER: Parse risk score from Oracle report
# ──────────────────────────────────────────────────────────
def extract_risk_score(report_text: str) -> int:
    """Try to pull a 0-100 risk score from the Oracle report."""
    patterns = [
        r'[Rr]isk\s*[Ss]core[:\s]*(\d{1,3})',
        r'(\d{1,3})\s*/\s*100',
        r'(\d{1,3})\s*out\s*of\s*100',
        r'[Ss]core[:\s]*(\d{1,3})',
    ]
    for p in patterns:
        m = re.search(p, report_text)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                return val
    return 45  # default


# ──────────────────────────────────────────────────────────
#  HELPER: Format agent output nicely
# ──────────────────────────────────────────────────────────
def render_agent_findings(agent_key: str, content: str):
    """Render findings inside a styled card."""
    a = AGENT_PROFILES[agent_key]
    c = a["color"]

    st.markdown(f"""
    <div class="nx-card" style="border-left:4px solid {c};">
        <div class="nx-card-title" style="color:{c};">
            <img src="{a['avatar_url']}" style="
                width:36px;height:36px;border-radius:50%;
                border:2px solid {c};background:#0f1629;
            "/>
            {a['icon']} {a['name']} — {a['role']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(content)


# ──────────────────────────────────────────────────────────
#  HELPER: Live animated header component
# ──────────────────────────────────────────────────────────
def render_header():
    """Main NEXUS header with animated elements."""
    header_html = """
    <div style="
        position:relative; text-align:center;
        padding:2rem 1rem 1.5rem; margin-bottom:0.5rem;
    ">
        <div style="
            position:absolute; top:50%; left:50%;
            width:500px; height:500px;
            transform:translate(-50%,-50%);
            background:radial-gradient(circle,rgba(59,130,246,0.06),transparent 65%);
            pointer-events:none;
        "></div>

        <div style="
            font-family:'Exo 2',sans-serif;
            font-size:3.2rem; font-weight:900;
            letter-spacing:12px;
            background:linear-gradient(135deg,#3b82f6,#10b981,#f59e0b);
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
            position:relative;
        ">
            🔮 NEXUS
            <div style="
                position:absolute; bottom:-2px; left:15%; width:70%; height:2px;
                background:linear-gradient(90deg,transparent,#3b82f6,#10b981,transparent);
            "></div>
        </div>

        <div style="
            font-family:'Space Grotesk',sans-serif;
            font-size:0.8rem; color:#94a3b8;
            letter-spacing:6px; text-transform:uppercase;
            margin-top:0.6rem;
        ">
            AI-Powered OSINT & Threat Intelligence Platform
        </div>

        <div style="
            display:inline-block; margin-top:0.7rem;
            padding:3px 14px;
            background:rgba(59,130,246,0.1);
            border:1px solid rgba(59,130,246,0.25);
            border-radius:20px;
            font-family:'Fira Code',monospace;
            font-size:0.6rem; color:#3b82f6;
            letter-spacing:2px;
        ">
            <span style="display:inline-block;width:6px;height:6px;
                         background:#10b981;border-radius:50%;margin-right:6px;
                         box-shadow:0 0 6px #10b981;"></span>
            v2.0 • MULTI-AGENT • LIVE RECON
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  MAIN APP
# ──────────────────────────────────────────────────────────
def main():
    # Inject full CSS
    st.markdown(NEXUS_CSS, unsafe_allow_html=True)

    # Header
    render_header()

    # Live metrics
    render_metrics_bar()

    # Agent showcase
    st.markdown("""
    <div style="
        font-family:'Exo 2',sans-serif; font-size:0.85rem;
        font-weight:700; letter-spacing:3px; color:#94a3b8;
        text-transform:uppercase; margin-bottom:0.5rem;
        text-align:center;
    ">
        <span style="display:inline-block;width:6px;height:6px;
                     background:#3b82f6;border-radius:50%;margin-right:8px;
                     box-shadow:0 0 6px #3b82f6;"></span>
        AGENT SQUAD — READY FOR DEPLOYMENT
    </div>
    """, unsafe_allow_html=True)

    render_agent_showcase()

    # ── Input Section ──
    st.markdown("""
    <div style="
        font-family:'Exo 2',sans-serif; font-size:1rem;
        font-weight:700; letter-spacing:3px; color:#3b82f6;
        margin:1.5rem 0 0.8rem;
    ">
        🎯 TARGET ACQUISITION
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])

    with col1:
        target = st.text_input(
            "TARGET",
            placeholder="e.g. example.com, 192.168.1.1, Acme Corp",
            label_visibility="collapsed",
        )

    with col2:
        target_type = st.selectbox(
            "TYPE",
            ["Domain", "IP Address", "Company"],
            label_visibility="collapsed",
        )

    # ── Launch Button ──
    launch = st.button("🚀  DEPLOY AGENTS  —  BEGIN RECONNAISSANCE", use_container_width=True)

    # ── API Key Check ──
    api_key = GROQ_API_KEY or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.markdown("""
        <div style="
            background:rgba(244,63,94,0.08); border:1px solid rgba(244,63,94,0.25);
            border-radius:12px; padding:1rem 1.2rem; margin-top:1rem;
            font-family:'Space Grotesk',sans-serif; color:#f1f5f9;
        ">
            <span style="color:#f43f5e;font-weight:700;">⚠ GROQ API KEY REQUIRED</span><br/>
            <span style="font-size:0.82rem;color:#94a3b8;">
                Add your key in Streamlit Cloud → Settings → Secrets:<br/>
                <code style="background:#1e293b;padding:2px 8px;border-radius:4px;
                             font-family:'Fira Code',monospace;font-size:0.75rem;">
                    GROQ_API_KEY = "gsk_your_key_here"
                </code>
            </span>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Run Pipeline ──
    if launch and target.strip():
        start_time = time.time()

        results = run_osint_audit(target.strip(), target_type.lower())

        elapsed = round(time.time() - start_time, 1)

        # ── SUCCESS BANNER ──
        st.markdown(f"""
        <div style="
            background:linear-gradient(135deg,rgba(16,185,129,0.1),rgba(59,130,246,0.1));
            border:1px solid rgba(16,185,129,0.3);
            border-radius:16px; padding:1.2rem 1.5rem;
            margin:1.5rem 0; text-align:center;
        ">
            <span style="font-family:'Exo 2',sans-serif;font-size:1.3rem;
                         font-weight:900;color:#10b981;letter-spacing:3px;">
                ✅ RECONNAISSANCE COMPLETE
            </span><br/>
            <span style="font-family:'Fira Code',monospace;font-size:0.8rem;color:#94a3b8;">
                5 agents deployed • 12 tools executed •
                {elapsed}s total elapsed • Target: {target}
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ── RISK GAUGE ──
        oracle_text = results.get("oracle", "")
        risk_score = extract_risk_score(oracle_text)
        render_risk_gauge(risk_score)

        # ── RESULTS TABS ──
        tab_labels = [
            f"{AGENT_PROFILES[k]['icon']} {AGENT_PROFILES[k]['name']}"
            for k in ["aria", "raven", "vulcan", "cipher", "oracle"]
        ]
        tabs = st.tabs(tab_labels)

        agent_keys = ["aria", "raven", "vulcan", "cipher", "oracle"]
        for tab, key in zip(tabs, agent_keys):
            with tab:
                content = results.get(key, "_No data collected._")
                render_agent_findings(key, content)

        # ── DOWNLOAD RAW JSON ──
        st.markdown("---")
        st.markdown("""
        <div style="
            font-family:'Exo 2',sans-serif; font-size:0.85rem;
            font-weight:700; letter-spacing:3px; color:#94a3b8;
            margin-bottom:0.5rem;
        ">📥 EXPORT INTELLIGENCE</div>
        """, unsafe_allow_html=True)

        export_data = {
            "target": target,
            "type": target_type,
            "timestamp": datetime.now().isoformat(),
            "risk_score": risk_score,
            "elapsed_seconds": elapsed,
            "model": MODEL_NAME,
            "findings": results,
        }

        st.download_button(
            label="⬇  Download Full Report (JSON)",
            data=json.dumps(export_data, indent=2, default=str),
            file_name=f"nexus_report_{target.replace('.','_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

    elif launch and not target.strip():
        st.markdown("""
        <div style="
            background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);
            border-radius:12px;padding:0.8rem 1.2rem;margin-top:1rem;
            font-family:'Space Grotesk',sans-serif;color:#f59e0b;
            font-size:0.85rem;
        ">
            ⚠ Please enter a target domain, IP address, or company name.
        </div>
        """, unsafe_allow_html=True)

    # ── FOOTER ──
    st.markdown("""
    <div style="
        text-align:center; margin-top:3rem; padding:1.5rem;
        border-top:1px solid #1e293b;
    ">
        <span style="font-family:'Fira Code',monospace;font-size:0.65rem;
                     color:#475569;letter-spacing:2px;">
            NEXUS COMMAND v2.0 • Multi-Agent OSINT Platform •
            Powered by Groq LLM • Built for Hackathon Excellence
        </span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
