import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

st.set_page_config(
    page_title="NEXUS | OSINT Intelligence",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from agents.orchestrator import render_saved_agent_workstations, run_osint_audit
from agents.tools import TOOL_REGISTRY
from config.settings import AGENT_PROFILES, GROQ_API_KEY, MODEL_NAME


AGENT_ORDER = ["aria", "raven", "vulcan", "cipher", "oracle"]


def _escape(value):
    return html.escape(str(value), quote=True)


def get_css():
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root{--bg:#080d14;--panel:#0d141e;--raised:#111b27;--border:#1d2a38;--text:#edf4fb;--muted:#91a1b2;--subtle:#66788b;--accent:#47c8e8;--green:#55d6a5}
    html,body,[class*="css"]{font-family:'Manrope',sans-serif}
    .stApp{background:radial-gradient(ellipse at 50% -22%,rgba(33,94,132,.22),transparent 52%),var(--bg);color:var(--text)}
    .stApp:before{content:'';position:fixed;inset:0;pointer-events:none;opacity:.15;z-index:0;background-image:linear-gradient(rgba(112,159,191,.055) 1px,transparent 1px),linear-gradient(90deg,rgba(112,159,191,.055) 1px,transparent 1px);background-size:44px 44px}
    header[data-testid='stHeader']{background:transparent}#MainMenu,footer,div[data-testid='stDecoration']{visibility:hidden}
    .block-container{max-width:1460px;padding:1.8rem 2.1rem 3rem;position:relative;z-index:1}
    h1,h2,h3,p{color:var(--text)}
    .nx-topbar{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:.2rem 0 1.15rem;border-bottom:1px solid var(--border)}
    .nx-brand{display:flex;align-items:center;gap:.75rem}.nx-mark{width:38px;height:38px;display:grid;place-items:center;border:1px solid rgba(71,200,232,.45);border-radius:11px;color:var(--accent);font-weight:800;font-size:1.2rem;background:rgba(71,200,232,.08);box-shadow:0 0 24px rgba(71,200,232,.09)}
    .nx-brand-name{font-size:.96rem;font-weight:800;letter-spacing:.16em}.nx-brand-sub{font:500 .61rem 'DM Mono',monospace;color:var(--subtle);letter-spacing:.08em;margin-top:2px}
    .nx-live{display:flex;align-items:center;gap:.55rem;font:500 .67rem 'DM Mono',monospace;color:#a8bac9;letter-spacing:.08em}.nx-live-dot,.operation-indicator{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 12px rgba(85,214,165,.6);animation:signal-pulse 2s ease-in-out infinite}
    .nx-hero{padding:2.25rem 0 1.4rem;animation:fade-up .45s ease-out both}.nx-eyebrow{color:var(--accent);font:500 .67rem 'DM Mono',monospace;letter-spacing:.19em;text-transform:uppercase;margin-bottom:.75rem}
    .nx-title{font-size:clamp(2.1rem,4.1vw,3.55rem);line-height:1.02;font-weight:800;letter-spacing:-.055em;margin:0}.nx-title span{color:var(--accent)}
    .nx-subtitle{color:var(--muted);font-size:.93rem;margin:.8rem 0 0;max-width:700px;line-height:1.7}.nx-badges{display:flex;gap:.55rem;flex-wrap:wrap;margin-top:1.1rem}.nx-badge{padding:.37rem .63rem;border:1px solid var(--border);border-radius:6px;background:rgba(16,27,39,.62);color:#a6b8c8;font:500 .59rem 'DM Mono',monospace;letter-spacing:.07em}
    .metric-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem;margin:1rem 0 1.5rem}.metric-card{background:linear-gradient(145deg,rgba(16,26,37,.96),rgba(11,18,27,.94));border:1px solid var(--border);border-radius:11px;padding:.9rem 1rem;min-height:82px;animation:fade-up .4s ease-out both}.metric-card:nth-child(2){animation-delay:.06s}.metric-card:nth-child(3){animation-delay:.12s}.metric-card:nth-child(4){animation-delay:.18s}
    .metric-label{color:var(--subtle);font:500 .59rem 'DM Mono',monospace;letter-spacing:.12em;text-transform:uppercase}.metric-value{color:#e5eef6;font-size:1.06rem;font-weight:700;margin-top:.42rem}.metric-value small{font:500 .66rem 'DM Mono',monospace;color:var(--muted)}
    .section-kicker{color:var(--accent);font:500 .62rem 'DM Mono',monospace;letter-spacing:.14em}.section-heading{display:flex;align-items:end;justify-content:space-between;gap:1rem;margin:.9rem 0 .55rem}.section-heading h2{font-size:1.08rem;margin:.2rem 0 0}.section-heading>span{color:var(--subtle);font-size:.65rem}
    .agent-roster{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.65rem;margin:1rem 0 1.55rem}.roster-card{background:rgba(13,20,30,.92);border:1px solid var(--border);border-top:2px solid var(--agent-accent);border-radius:9px;padding:.78rem .8rem;transition:transform .18s ease,border-color .18s ease}.roster-card:hover{transform:translateY(-2px);border-color:color-mix(in srgb,var(--agent-accent) 55%,var(--border))}
    .roster-code{color:var(--agent-accent);font:500 .58rem 'DM Mono',monospace;letter-spacing:.11em}.roster-name{color:var(--text);font-weight:800;font-size:.83rem;margin:.28rem 0 .1rem;letter-spacing:.04em}.roster-role{color:var(--muted);font-size:.65rem;line-height:1.4}
    .stTextInput label,.stSelectbox label{color:#9dafbf!important;font:500 .64rem 'DM Mono',monospace!important;letter-spacing:.1em!important;text-transform:uppercase!important}.stTextInput input{background:#0a111a!important;border:1px solid #263746!important;border-radius:8px!important;color:var(--text)!important;min-height:44px}.stTextInput input:focus{border-color:var(--accent)!important;box-shadow:0 0 0 1px rgba(71,200,232,.2)!important}.stSelectbox [data-baseweb='select']>div{background:#0a111a!important;border:1px solid #263746!important;border-radius:8px!important;color:var(--text)!important;min-height:44px}
    div.stButton>button,div[data-testid='stFormSubmitButton'] button{width:100%;min-height:44px;border-radius:8px;border:1px solid rgba(71,200,232,.55);background:linear-gradient(115deg,#137a99,#14617c);color:#f4fbff;font:700 .72rem 'DM Mono',monospace;letter-spacing:.09em;transition:all .18s ease}div.stButton>button:hover,div[data-testid='stFormSubmitButton'] button:hover{border-color:#83e3fa;background:linear-gradient(115deg,#1691b3,#177393);box-shadow:0 7px 24px rgba(27,151,184,.18);transform:translateY(-1px)}
    .operation-banner,.operation-complete{display:flex;align-items:center;gap:.8rem;padding:.8rem 1rem;margin:1rem 0;border:1px solid rgba(71,200,232,.25);border-radius:9px;background:rgba(14,43,57,.47)}.operation-banner strong,.operation-complete strong{display:block;color:#ccebf4;font:500 .65rem 'DM Mono',monospace;letter-spacing:.11em}.operation-banner span:not(.operation-count),.operation-complete span:not(.complete-mark){color:var(--muted);font-size:.69rem;display:block;margin-top:.22rem}.operation-count{margin-left:auto;color:#9dc3d0;font:500 .58rem 'DM Mono',monospace;letter-spacing:.08em}.operation-complete{border-color:rgba(85,214,165,.28);background:rgba(17,52,43,.4)}.complete-mark{color:var(--green);font-size:1.1rem}
    .agent-console{--agent-accent:#47c8e8;position:relative;overflow:hidden;border:1px solid #21303e;border-radius:12px;margin:.2rem 0 .85rem;background:linear-gradient(150deg,#101923,#0b121a);transition:border-color .2s ease,box-shadow .2s ease}.agent-console.status-thinking,.agent-console.status-executing,.agent-console.status-finalizing{border-color:color-mix(in srgb,var(--agent-accent) 45%,#21303e);box-shadow:0 0 23px color-mix(in srgb,var(--agent-accent) 10%,transparent)}.agent-console.status-complete{border-color:rgba(85,214,165,.28)}.agent-console.status-error,.agent-console.status-fallback{border-color:rgba(242,166,109,.45)}
    .agent-console-topline{height:2px;background:linear-gradient(90deg,var(--agent-accent),transparent 72%);opacity:.9}.agent-console-header{display:flex;align-items:center;gap:.75rem;padding:.72rem .88rem .58rem}
    .agent-avatar{width:48px;height:48px;position:relative;flex:0 0 48px;display:grid;place-items:center;filter:drop-shadow(0 0 11px color-mix(in srgb,var(--agent-accent) 24%,transparent))}.agent-avatar-orbit{position:absolute;inset:3px;border:1px dashed color-mix(in srgb,var(--agent-accent) 62%,transparent);border-radius:50%;transform:rotate(-18deg)}.agent-avatar-satellite{position:absolute;z-index:3;top:4px;right:7px;width:5px;height:5px;border-radius:50%;background:var(--agent-accent);box-shadow:0 0 8px var(--agent-accent)}
    .agent-avatar-core{position:absolute;inset:9px;border:1px solid color-mix(in srgb,var(--agent-accent) 52%,#223242);border-radius:43% 43% 48% 48%;background:radial-gradient(circle at 50% 35%,color-mix(in srgb,var(--agent-accent) 18%,#142231),#0b131c 75%);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:5px;animation:avatar-float 3.2s ease-in-out infinite}.agent-avatar-eyes{display:flex;gap:8px}.agent-avatar-eyes i{width:4px;height:5px;border-radius:50%;background:var(--agent-accent);box-shadow:0 0 7px var(--agent-accent)}.agent-avatar-mouth{width:9px;height:2px;border-radius:2px;background:color-mix(in srgb,var(--agent-accent) 65%,#40505c)}.agent-avatar-scan{position:absolute;z-index:4;left:12px;right:12px;top:11px;height:1px;background:var(--agent-accent);opacity:0;box-shadow:0 0 8px var(--agent-accent)}
    .status-thinking .agent-avatar-orbit,.status-finalizing .agent-avatar-orbit{animation:avatar-orbit 4s linear infinite}.status-executing .agent-avatar-orbit{animation:avatar-orbit 1.55s linear infinite}.status-thinking .agent-avatar-core,.status-finalizing .agent-avatar-core{animation:avatar-float 1.4s ease-in-out infinite,avatar-glow 1.7s ease-in-out infinite}.status-executing .agent-avatar-core{animation:avatar-glow .72s ease-in-out infinite}.status-executing .agent-avatar-scan{opacity:.85;animation:avatar-scan 1.1s ease-in-out infinite}.status-complete .agent-avatar-satellite{background:var(--green);box-shadow:0 0 8px var(--green)}.status-error .agent-avatar-core,.status-fallback .agent-avatar-core{border-color:#f2a66d}
    .agent-heading{flex:1;min-width:0}.agent-name-row{display:flex;align-items:center;gap:.55rem;flex-wrap:wrap}.agent-name-row h3{font-size:.79rem;letter-spacing:.08em;margin:0}.agent-heading p{color:var(--muted);font-size:.63rem;margin:.12rem 0 0}.agent-duration{color:#a8bbc9;font:500 .63rem 'DM Mono',monospace}
    .agent-status{display:inline-flex;align-items:center;gap:.32rem;border:1px solid #304252;border-radius:20px;padding:.18rem .4rem;color:#91a4b5;font:500 .5rem 'DM Mono',monospace;letter-spacing:.05em}.agent-status i{width:5px;height:5px;border-radius:50%;background:#617587}.status-thinking .agent-status,.status-executing .agent-status,.status-finalizing .agent-status{color:var(--agent-accent);border-color:color-mix(in srgb,var(--agent-accent) 38%,transparent)}.status-thinking .agent-status i,.status-executing .agent-status i,.status-finalizing .agent-status i{background:var(--agent-accent);box-shadow:0 0 8px var(--agent-accent);animation:signal-pulse 1s ease-in-out infinite}.status-complete .agent-status{color:var(--green);border-color:rgba(85,214,165,.3)}.status-complete .agent-status i{background:var(--green)}.status-error .agent-status,.status-fallback .agent-status{color:#ffb27c;border-color:rgba(255,178,124,.32)}.status-error .agent-status i,.status-fallback .agent-status i{background:#f2a66d}
    .agent-current{display:flex;flex-direction:column;gap:.22rem;margin:0 .88rem .62rem;padding:.5rem .6rem;border:1px solid #1b2a38;border-radius:7px;background:#0a1119}.current-label,.agent-feed-heading{color:#728598;font:500 .51rem 'DM Mono',monospace;letter-spacing:.1em}.current-text{color:#d3dee8;font-size:.64rem;line-height:1.5;overflow-wrap:anywhere}.agent-feed-heading{display:flex;justify-content:space-between;margin:0 .9rem .35rem}.agent-feed{max-height:280px;overflow-y:auto;padding:0 .65rem .65rem .88rem;scrollbar-width:thin;scrollbar-color:#314657 transparent}
    .agent-event{display:grid;grid-template-columns:52px 52px minmax(0,1fr);gap:.42rem;align-items:start;padding:.42rem 0;border-top:1px solid rgba(34,49,64,.58);animation:fade-up .2s ease-out both}.agent-event time{color:#677c90;font:400 .53rem 'DM Mono',monospace;padding-top:.13rem}.event-tag{display:inline-block;width:max-content;color:#83a1b4;font:500 .49rem 'DM Mono',monospace;letter-spacing:.04em;border:1px solid #263b4a;border-radius:4px;padding:.11rem .25rem}.event-thinking,.event-finalizing{color:#b4a3ff;border-color:rgba(180,163,255,.27)}.event-tool_call{color:#83dcf0;border-color:rgba(71,200,232,.25)}.event-tool_result{color:#77dcb6;border-color:rgba(85,214,165,.25)}.event-error,.event-tool_blocked{color:#ff9a9a;border-color:rgba(255,112,112,.28)}.event-final{color:#d2c48d;border-color:rgba(210,196,141,.25)}.event-fallback{color:#ffc28d;border-color:rgba(242,166,109,.32)}.event-message{color:#b9c6d2;font-size:.61rem;line-height:1.48;overflow-wrap:anywhere}.event-tool-name{color:#8de5f4;background:rgba(71,200,232,.09);padding:.08rem .25rem;border-radius:4px;margin-right:.3rem;font:500 .56rem 'DM Mono',monospace}.agent-empty{color:#718395;padding:.45rem 0;font-size:.62rem}
    .report-summary{padding:1rem 1.1rem;border:1px solid rgba(85,214,165,.24);border-radius:10px;background:linear-gradient(110deg,rgba(14,50,42,.5),rgba(12,28,37,.6));margin:.65rem 0 1rem}.report-summary-title{color:#bdebd8;font-size:.91rem;font-weight:800}.report-summary-meta{color:#93a9b7;font:400 .61rem 'DM Mono',monospace;margin-top:.35rem}.risk-panel{display:flex;align-items:center;gap:1rem;padding:.88rem 1rem;border:1px solid var(--border);border-radius:10px;background:rgba(13,20,30,.9);margin:.6rem 0 1rem}.risk-number{color:var(--risk-color);font-size:1.65rem;line-height:1;font-weight:800;min-width:50px}.risk-copy strong{display:block;color:#dce7ef;font-size:.75rem}.risk-copy span{display:block;color:var(--muted);font-size:.63rem;margin-top:.18rem}
    [data-testid='stExpander']{border:1px solid var(--border)!important;border-radius:10px!important;background:rgba(13,20,30,.84)!important;margin:.5rem 0!important}[data-testid='stExpander'] summary{color:var(--text)!important;font-weight:700}[data-testid='stExpander'] details{border:0!important}.stDownloadButton button{border-radius:7px!important;background:#101a24!important;color:#c5d3df!important;border:1px solid #2a3c4c!important;font:500 .67rem 'DM Mono',monospace!important}
    .nx-footer{border-top:1px solid var(--border);margin-top:2.6rem;padding-top:.9rem;display:flex;justify-content:space-between;color:#586b7d;font:400 .56rem 'DM Mono',monospace;letter-spacing:.07em}
    @keyframes signal-pulse{0%,100%{opacity:.55;transform:scale(.88)}50%{opacity:1;transform:scale(1.16)}}@keyframes avatar-orbit{to{transform:rotate(342deg)}}@keyframes avatar-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}@keyframes avatar-glow{0%,100%{filter:brightness(.93);box-shadow:0 0 4px color-mix(in srgb,var(--agent-accent) 14%,transparent)}50%{filter:brightness(1.3);box-shadow:0 0 15px color-mix(in srgb,var(--agent-accent) 35%,transparent)}}@keyframes avatar-scan{0%{transform:translateY(0);opacity:0}18%{opacity:.9}82%{opacity:.9}100%{transform:translateY(26px);opacity:0}}@keyframes fade-up{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
    @media(max-width:850px){.block-container{padding:1.1rem 1rem 2rem}.metric-row{grid-template-columns:repeat(2,1fr)}.agent-roster{grid-template-columns:repeat(2,1fr)}.section-heading{align-items:start;flex-direction:column}}
    @media(max-width:520px){.nx-live{font-size:.55rem}.nx-hero{padding-top:1.7rem}.agent-roster{grid-template-columns:1fr 1fr}.operation-count{display:none}.nx-footer{gap:.6rem;flex-direction:column}.agent-event{grid-template-columns:42px 46px minmax(0,1fr);gap:.3rem}.agent-avatar{width:42px;height:42px;flex-basis:42px}}
    /* ===== Advanced animated layer (presentation only) ===== */
    .stApp{background:radial-gradient(ellipse 900px 480px at 12% -10%,rgba(71,200,232,.20),transparent 60%),radial-gradient(ellipse 800px 420px at 88% 8%,rgba(167,139,250,.16),transparent 60%),radial-gradient(ellipse at 50% -22%,rgba(33,94,132,.22),transparent 52%),var(--bg)}
    .nx-title span{background:linear-gradient(92deg,#47c8e8,#8ca8ff,#55d6a5,#47c8e8);background-size:220% 100%;-webkit-background-clip:text;background-clip:text;color:transparent;animation:gradient-slide 7s ease-in-out infinite}
    @keyframes gradient-slide{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
    .metric-card{position:relative;overflow:hidden;transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease}
    .metric-card:before{content:'';position:absolute;inset:0;background:linear-gradient(115deg,transparent 30%,rgba(71,200,232,.10) 50%,transparent 70%);transform:translateX(-120%);transition:transform .7s ease}
    .metric-card:hover{transform:translateY(-3px);border-color:rgba(71,200,232,.45);box-shadow:0 12px 30px rgba(0,0,0,.35)}
    .metric-card:hover:before{transform:translateX(120%)}
    .roster-card{position:relative;overflow:hidden;animation:fade-up .45s ease-out both}
    .roster-card:nth-child(2){animation-delay:.06s}.roster-card:nth-child(3){animation-delay:.12s}.roster-card:nth-child(4){animation-delay:.18s}.roster-card:nth-child(5){animation-delay:.24s}
    .roster-card:hover{transform:translateY(-4px);box-shadow:0 14px 30px rgba(0,0,0,.35)}
    .roster-card:after{content:'';position:absolute;left:0;right:0;bottom:0;height:2px;background:linear-gradient(90deg,var(--agent-accent),transparent);opacity:.7}
    .roster-icon{font-size:1.15rem;line-height:1}.roster-catch{color:#8fa5b6;font-size:.62rem;line-height:1.5;margin-top:.35rem;font-style:italic}.roster-status{margin-top:.5rem;color:#5f7487;font:500 .52rem 'DM Mono',monospace;letter-spacing:.12em}
    .agent-console{animation:fade-up .35s ease-out both}
    .agent-console.status-thinking,.agent-console.status-executing,.agent-console.status-finalizing{animation:console-breathe 2.2s ease-in-out infinite}
    @keyframes console-breathe{0%,100%{box-shadow:0 0 14px color-mix(in srgb,var(--agent-accent) 8%,transparent)}50%{box-shadow:0 0 30px color-mix(in srgb,var(--agent-accent) 20%,transparent)}}
    .agent-feed{scroll-behavior:smooth}
    .agent-event:nth-child(odd){background:rgba(255,255,255,.012)}
    /* Mission control */
    .mission-control{border:1px solid #223242;border-radius:14px;padding:1.05rem 1.15rem 1rem;margin:1rem 0 1.4rem;background:linear-gradient(150deg,rgba(17,28,40,.97),rgba(10,17,26,.96));box-shadow:0 18px 44px rgba(0,0,0,.30);animation:fade-up .4s ease-out both;position:relative;overflow:hidden}
    .mission-control:before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#47c8e8,#a78bfa,#55d6a5,transparent);background-size:200% 100%;animation:gradient-slide 6s linear infinite}
    .mission-live{border-color:rgba(71,200,232,.45);box-shadow:0 0 0 1px rgba(71,200,232,.12),0 18px 44px rgba(0,0,0,.35)}
    .mission-head{display:flex;justify-content:space-between;align-items:end;gap:1rem}.mission-head h2{font-size:1.15rem;margin:.2rem 0 0}
    .mission-live-label{color:#8fa5b6;font:500 .58rem 'DM Mono',monospace;letter-spacing:.1em}.mission-live .mission-live-label{color:#55d6a5;animation:signal-pulse 1.6s ease-in-out infinite}
    .mission-target{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin:.8rem 0 .6rem;padding:.6rem .75rem;border:1px solid #1b2a38;border-radius:8px;background:#0a1119;font-size:.68rem;color:#a8bbc9}.mission-target strong{color:#e5eef6}.mission-target span{color:#8193a2;font-family:'DM Mono',monospace;font-size:.6rem}
    .mission-progress{display:flex;align-items:center;gap:.8rem;margin:.2rem 0 .9rem}.mission-progress-track{flex:1;height:8px;border-radius:99px;background:#16222f;overflow:hidden}.mission-progress-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#47c8e8,#a78bfa,#55d6a5);background-size:200% 100%;animation:gradient-slide 4s linear infinite;transition:width .6s ease}.mission-progress-pct{color:#e5eef6;font:700 .72rem 'DM Mono',monospace;min-width:38px;text-align:right}
    .mission-timeline{display:flex;align-items:stretch;gap:.3rem;margin:.2rem 0 1rem;flex-wrap:wrap}.tl-node{flex:1;min-width:110px;border:1px solid #1d2a38;border-radius:9px;padding:.55rem .6rem;background:rgba(10,17,25,.8);transition:transform .18s ease,border-color .18s ease}.tl-node:hover{transform:translateY(-2px)}.tl-mark{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;border:1px solid var(--agent-accent);color:var(--agent-accent);font-size:.6rem;font-weight:800;margin-bottom:.3rem}.tl-name{display:block;color:#e5eef6;font-weight:800;font-size:.68rem;letter-spacing:.05em}.tl-meta{display:block;color:#8193a2;font-size:.58rem;margin-top:.15rem}.tl-node.node-done{border-color:rgba(85,214,165,.35)}.tl-node.node-done .tl-mark{background:rgba(85,214,165,.15);color:#55d6a5;border-color:rgba(85,214,165,.5)}.tl-node.node-current{border-color:color-mix(in srgb,var(--agent-accent) 50%,#1d2a38);box-shadow:0 0 18px rgba(71,200,232,.12);animation:console-breathe 2.2s ease-in-out infinite}.tl-node.node-current .tl-mark{animation:signal-pulse 1.2s ease-in-out infinite}.tl-node.node-error{border-color:rgba(255,115,115,.45)}.tl-node.node-error .tl-mark{color:#ff7373;border-color:#ff7373}.tl-connector{flex:0 0 14px;align-self:center;height:1px;background:#263746}
    .mission-feed-heading{display:flex;justify-content:space-between;color:#728598;font:500 .52rem 'DM Mono',monospace;letter-spacing:.1em;margin-bottom:.4rem}.mission-feed{max-height:340px;overflow-y:auto;padding-right:.4rem;scrollbar-width:thin;scrollbar-color:#314657 transparent;border-top:1px solid rgba(34,49,64,.58)}
    .feed-row{display:grid;grid-template-columns:52px 62px 62px minmax(0,1fr);gap:.42rem;align-items:start;padding:.42rem 0;border-bottom:1px solid rgba(34,49,64,.45);animation:fade-up .2s ease-out both}.feed-row time{color:#677c90;font:400 .53rem 'DM Mono',monospace;padding-top:.13rem}.feed-agent{color:var(--agent-accent);font:500 .52rem 'DM Mono',monospace;letter-spacing:.04em}.feed-text{color:#b9c6d2;font-size:.61rem;line-height:1.48;overflow-wrap:anywhere}.mission-feed-empty{color:#718395;padding:.6rem 0;font-size:.64rem;line-height:1.6}
    /* Idle standby panel + report downloads */
    .idle-panel{border:1px dashed #2a3c4c;border-radius:12px;padding:1.1rem 1.2rem;margin:1rem 0 1.4rem;background:rgba(13,20,30,.55);animation:fade-up .4s ease-out both}.idle-panel strong{display:block;color:#dce7ef;font-size:.82rem}.idle-panel span{display:block;color:#8193a2;font-size:.68rem;line-height:1.6;margin-top:.3rem}
    .download-row{display:grid;grid-template-columns:1fr 1fr;gap:.7rem;margin:.7rem 0 1rem}
    @media(max-width:850px){.mission-timeline{flex-direction:column}.tl-connector{display:none}.feed-row{grid-template-columns:42px 52px 52px minmax(0,1fr)}.download-row{grid-template-columns:1fr}}
    @media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition-duration:.01ms!important}}
    </style>
    """


def render_header():
    st.markdown(
        '<div class="nx-topbar"><div class="nx-brand"><div class="nx-mark">N</div>'
        '<div><div class="nx-brand-name">NEXUS</div><div class="nx-brand-sub">INTELLIGENCE OPERATIONS</div></div></div>'
        '<div class="nx-live"><i class="nx-live-dot"></i> SYSTEM READY <span style="color:#425465">/</span> '
        + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + '</div></div>'
        '<div class="nx-hero"><div class="nx-eyebrow">Open-source intelligence · multi-agent analysis</div>'
        '<h1 class="nx-title">Know the <span>exposure.</span><br>Make the next move.</h1>'
        '<p class="nx-subtitle">A coordinated intelligence workspace for domain, threat, attack-surface and email-security research. '
        'Watch each specialist work, inspect the exact tools executed, and review evidence-backed findings.</p>'
        '<div class="nx-badges"><span class="nx-badge">PASSIVE RECONNAISSANCE</span>'
        '<span class="nx-badge">5 SPECIALIST AGENTS</span><span class="nx-badge">GROQ · ' + _escape(MODEL_NAME) + '</span></div></div>',
        unsafe_allow_html=True,
    )


def render_metrics():
    cards = [
        ("SPECIALIST AGENTS", str(len(AGENT_PROFILES)), "coordinated roles"),
        ("AVAILABLE OSINT TOOLS", str(len(TOOL_REGISTRY)), "passive checks"),
        ("REPORT FORMAT", "Evidence-led", "source-aware findings"),
        ("MODEL", MODEL_NAME.split("/")[-1], "Groq inference"),
    ]
    markup = '<div class="metric-row">'
    for label, value, detail in cards:
        markup += (
            '<div class="metric-card"><div class="metric-label">' + _escape(label) + '</div>'
            '<div class="metric-value">' + _escape(value) + ' <small>' + _escape(detail) + '</small></div></div>'
        )
    st.markdown(markup + '</div>', unsafe_allow_html=True)


def render_agent_showcase():
    markup = '<div class="agent-roster">'
    for index, key in enumerate(AGENT_ORDER, start=1):
        agent = AGENT_PROFILES[key]
        markup += (
            '<div class="roster-card" style="--agent-accent:' + _escape(agent["color"]) + '">'
            '<div class="roster-code">SPECIALIST / ' + f'{index:02d}' + '</div>'
            '<div class="roster-icon">' + _escape(agent.get("icon", "")) + '</div>'
            '<div class="roster-name">' + _escape(agent["name"]) + '</div>'
            '<div class="roster-role">' + _escape(agent["role"]) + '</div>'
            '<div class="roster-catch">“' + _escape(agent.get("catchphrase", "")) + '”</div>'
            '<div class="roster-status">● STANDBY</div></div>'
        )
    st.markdown(markup + '</div>', unsafe_allow_html=True)


def render_idle_state():
    """Honest standby panel: agents are idle until a real scan starts.

    No simulated activity, no fake pulses pretending work is happening.
    """
    st.markdown(
        '<div class="idle-panel"><strong>No operation running — specialists on standby</strong>'
        '<span>Enter an authorized target above and run a scan. Mission Control will then '
        'show each agent working in real time: its status, the exact tools it executes, '
        'and a chronological activity feed. Until then, nothing here moves as if it were working.</span></div>',
        unsafe_allow_html=True,
    )


def extract_risk_score(text):
    for pattern in (
        r"[Rr]isk\s*[Ss]core[:\s]*(\d{1,3})",
        r"(\d{1,3})\s*/\s*100",
        r"(\d{1,3})\s*out\s*of\s*100",
        r"[Ss]core[:\s]*(\d{1,3})",
    ):
        match = re.search(pattern, text or "")
        if match and 0 <= int(match.group(1)) <= 100:
            return int(match.group(1))
    return None


def risk_level(score):
    if score is None:
        return "Not reported", "#91a1b2"
    if score >= 80:
        return "Critical", "#ff7373"
    if score >= 60:
        return "High", "#ffae69"
    if score >= 40:
        return "Moderate", "#f1cd72"
    if score >= 20:
        return "Low", "#66d5bb"
    return "Minimal", "#91a1b2"


def get_api_key():
    key = GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
    if key:
        return key
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        return ""


def _is_legacy_round_limit(content):
    normalized = (content or "").strip().lower().strip("_*() ")
    return normalized == "max rounds reached without final answer"


def render_report(report):
    results = report["results"]
    target = report["target"]
    target_type = report["target_type"]
    elapsed = report["elapsed"]
    oracle_text = str(results.get("oracle", ""))
    score = None if _is_legacy_round_limit(oracle_text) else extract_risk_score(oracle_text)
    activity = st.session_state.get("nexus_latest_activity", {})
    completed = sum(
        bool(str(results.get(key, "")).strip())
        and not str(results.get(key, "")).strip().lower().startswith("# agent execution failed")
        and not _is_legacy_round_limit(str(results.get(key, "")))
        for key in AGENT_ORDER
    )

    st.markdown(
        '<div class="section-heading"><div><span class="section-kicker">02 / FINDINGS</span>'
        '<h2>Intelligence report</h2></div><span>Full findings for every specialist · tools shown by name</span></div>',
        unsafe_allow_html=True,
    )
    try:
        report_time = datetime.fromisoformat(report["timestamp"]).astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    except (ValueError, TypeError):
        report_time = str(report.get("timestamp", "Time not recorded"))
    st.markdown(
        '<div class="report-summary"><div class="report-summary-title">Analysis complete · ' + _escape(target) + '</div>'
        '<div class="report-summary-meta">' + _escape(target_type) + ' · ' + str(completed) + '/5 agents returned usable findings · '
        + f'{elapsed:.1f}s elapsed' + ' · ' + _escape(report_time) + '</div></div>',
        unsafe_allow_html=True,
    )

    level, color = risk_level(score)
    if score is None:
        risk_value = "—"
        risk_detail = "No verified numeric synthesis was available. Review the full findings below."
    else:
        risk_value = str(score)
        risk_detail = f"{level} exposure · reported by the synthesis agent on a 0–100 scale."
    st.markdown(
        '<div class="risk-panel" style="--risk-color:' + color + '"><div class="risk-number">' + risk_value
        + '<span style="font-size:.63rem;color:#8193a2">/100</span></div><div class="risk-copy"><strong>Reported risk assessment · '
        + _escape(level) + '</strong><span>' + _escape(risk_detail) + '</span></div></div>',
        unsafe_allow_html=True,
    )

    for key in AGENT_ORDER:
        agent = AGENT_PROFILES[key]
        content = str(results.get(key, "")).strip()
        if _is_legacy_round_limit(content):
            content = ""
        record = activity.get(key, {})
        status = record.get("status", "complete" if content else "error")
        label = f"{agent['name']}  ·  {agent['role']}  ·  {status.replace('_', ' ').upper()}"
        with st.expander(label, expanded=True):
            tool_events = [
                item for item in record.get("activity_log", [])
                if item.get("type") == "tool_call" and item.get("tool_name")
            ]
            tool_names = list(dict.fromkeys(item["tool_name"] for item in tool_events))
            if tool_names:
                st.caption("TOOLS EXECUTED · " + "  /  ".join(tool_names))
            elif key == "oracle":
                st.caption("TOOLS EXECUTED · none (synthesis agent; uses the other specialists’ findings)")
            else:
                st.caption("TOOLS EXECUTED · none recorded")

            if not content:
                st.warning("This session contains a legacy incomplete response. Run a fresh scan to replace it.")
            elif content.startswith("# Preliminary findings — evidence fallback"):
                st.warning("Model synthesis was unavailable. The content below is a preliminary evidence compilation, not a validated risk assessment.")
                diagnostic = re.search(
                    r"Final language-model synthesis was unavailable:\s*([^\r\n]+)",
                    content,
                )
                if diagnostic:
                    st.caption("SYNTHESIS DIAGNOSTIC · " + diagnostic.group(1)[:320])
                st.markdown(content)
            elif content.startswith("# Agent execution failed"):
                st.error(content)
            else:
                st.markdown(content)

    export = {
        "target": target,
        "target_type": target_type,
        "timestamp": report["timestamp"],
        "risk_score": score,
        "elapsed_seconds": elapsed,
        "model": MODEL_NAME,
        "findings": results,
    }
    col_json, col_pdf = st.columns(2)
    with col_json:
        st.download_button(
            "Download full report · JSON",
            data=json.dumps(export, indent=2, ensure_ascii=False, default=str),
            file_name="nexus_" + re.sub(r"[^A-Za-z0-9_-]+", "_", target).strip("_") + ".json",
            mime="application/json",
            use_container_width=True,
        )
    with col_pdf:
        # Previously dead code: generate_pdf looked up task keys that
        # never exist in agent-keyed results, so it exported a blank PDF.
        # The mapping is fixed in utils/pdf_generator.py; wire it here.
        try:
            from utils.pdf_generator import generate_pdf

            pdf_bytes = generate_pdf(results)
            st.download_button(
                "Download report · PDF",
                data=pdf_bytes,
                file_name="nexus_" + re.sub(r"[^A-Za-z0-9_-]+", "_", target).strip("_") + ".pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"PDF export unavailable: {type(exc).__name__}: {exc}")


def main():
    st.markdown(get_css(), unsafe_allow_html=True)
    render_header()
    render_metrics()

    st.markdown(
        '<div class="section-heading"><div><span class="section-kicker">01 / TEAM</span>'
        '<h2>Five focused specialists</h2></div><span>One target · coordinated analysis</span></div>',
        unsafe_allow_html=True,
    )
    render_agent_showcase()

    st.markdown(
        '<div class="section-heading"><div><span class="section-kicker">START AN OPERATION</span>'
        '<h2>Define an authorized target</h2></div><span>Use only targets you are authorized to assess.</span></div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        with st.form("nexus_target_form"):
            col_target, col_type, col_button = st.columns([5, 1.6, 1.7])
            with col_target:
                target = st.text_input("Target", placeholder="example.com, 203.0.113.10, or Acme Corp")
            with col_type:
                target_type = st.selectbox("Target type", ["Domain", "IP Address", "Company"])
            with col_button:
                launch = st.form_submit_button("Run intelligence scan", use_container_width=True)

    if not get_api_key():
        st.warning("Groq API key required. Set GROQ_API_KEY in the environment or in Streamlit secrets to enable agent runs.")

    activity_rendered = False
    if launch:
        if not target.strip():
            st.error("Enter a domain, IP address, or company name before starting the scan.")
        elif not get_api_key():
            st.error("The scan was not started because no Groq API key is configured.")
        else:
            activity_rendered = True
            started = time.time()
            # FIX: a previous report stayed visible under the new live
            # consoles until the new run finished, which looked like
            # the old findings belonged to the new target. Clear it
            # before the run; it is rebuilt from the new results below.
            st.session_state["nexus_latest_report"] = None
            try:
                results = run_osint_audit(target.strip(), target_type.lower())
                st.session_state["nexus_latest_report"] = {
                    "target": target.strip(),
                    "target_type": target_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "elapsed": time.time() - started,
                    "results": results,
                }
            except Exception as exc:
                st.error(f"The scan could not be completed: {type(exc).__name__}: {exc}")

    if not activity_rendered:
        render_saved_agent_workstations()

    if (
        not activity_rendered
        and not st.session_state.get("nexus_latest_activity")
        and not st.session_state.get("nexus_latest_report")
    ):
        render_idle_state()

    latest_report = st.session_state.get("nexus_latest_report")
    if latest_report:
        render_report(latest_report)

    st.markdown(
        '<div class="nx-footer"><span>NEXUS INTELLIGENCE OPERATIONS</span>'
        '<span>PASSIVE OSINT · VERIFY SOURCES BEFORE ACTION</span></div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
