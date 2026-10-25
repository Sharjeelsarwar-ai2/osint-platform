"""v3 styles — Neon Noir kept (user liked the v2 colours), layout rebuilt.

Dominant scheme: violet-black #0B0514, magenta #FF2E88, violet #8B5CF6,
lime #C6FF3D, amber #FFB020. No cyan-blue dominant scheme.
"""
import textwrap


def get_css():
    return textwrap.dedent(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800;900&display=swap');
        :root{--bg:#0b0514;--panel:#150a26;--raised:#1e0f38;--border:#3b1f5e;--text:#fff6ff;--muted:#c4b5d6;--subtle:#8a7aa3;--accent:#ff2e88;--violet:#8b5cf6;--lime:#c6ff3d;--amber:#ffb020}
        html,body,[class*="css"]{font-family:'Manrope',sans-serif}
        .stApp{background:radial-gradient(ellipse 1000px 520px at 8% -12%,rgba(255,46,136,.34),transparent 62%),radial-gradient(ellipse 900px 480px at 92% 4%,rgba(139,92,246,.32),transparent 60%),radial-gradient(ellipse 700px 380px at 50% 110%,rgba(198,255,61,.10),transparent 60%),#0b0514!important;color:#fff6ff}
        header[data-testid='stHeader']{background:transparent}#MainMenu,footer,div[data-testid='stDecoration']{visibility:hidden}
        .block-container{max-width:1560px;padding:1.2rem 1.8rem 3rem;position:relative;z-index:1}
        h1,h2,h3,p{color:var(--text)}
        section[data-testid="stSidebar"]{background:linear-gradient(180deg,#1a0b30,#0f061f)!important;border-right:1px solid #3b1f5e}
        section[data-testid="stSidebar"] .stMarkdown{color:#fff6ff}
        /* v2 class aliases kept for backwards compatibility (same Neon Noir) */
        .nx-hero-v2{border:1px solid rgba(255,46,136,.45);border-radius:22px}
        .nx-orb{position:absolute;border-radius:50%;filter:blur(38px);pointer-events:none;opacity:.75}
        /* ---- v3 command bar ---- */
        .cmd-bar{display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;border:1px solid #ff2e88;border-radius:18px;padding:.85rem 1.1rem;margin:.2rem 0 1rem;background:linear-gradient(120deg,rgba(38,10,64,.95),rgba(20,6,36,.95));box-shadow:0 18px 44px rgba(0,0,0,.45)}
        .cmd-brand{display:flex;align-items:center;gap:.8rem}.cmd-mark{width:44px;height:44px;display:grid;place-items:center;border-radius:13px;background:linear-gradient(135deg,#ff2e88,#8b5cf6);color:#fff;font-weight:900;font-size:1.3rem;box-shadow:0 0 26px rgba(255,46,136,.55)}
        .cmd-name{font-weight:900;letter-spacing:.18em}.cmd-sub{font:500 .58rem 'DM Mono',monospace;color:#8a7aa3;letter-spacing:.1em}
        .cmd-nav{display:flex;gap:.4rem;flex-wrap:wrap}.cmd-nav span{padding:.35rem .65rem;border:1px solid #3b1f5e;border-radius:99px;font:600 .58rem 'DM Mono',monospace;letter-spacing:.08em;color:#e9d5ff;background:rgba(255,46,136,.08)}
        .cmd-nav span.hot{background:#ff2e88;color:#fff;border-color:#ff2e88}
        .cmd-live{display:flex;align-items:center;gap:.5rem;font:600 .62rem 'DM Mono',monospace;color:#c6ff3d}
        .cmd-dot{width:9px;height:9px;border-radius:50%;background:#c6ff3d;box-shadow:0 0 12px #c6ff3d;animation:signal-pulse 1.6s ease-in-out infinite}
        /* ---- v3 hero strip + status bento ---- */
        .hero-strip{position:relative;overflow:hidden;border:1px solid rgba(255,46,136,.45);border-radius:22px;padding:2rem 2rem 1.6rem;margin:0 0 1rem;background:linear-gradient(120deg,rgba(38,10,64,.96),rgba(20,6,36,.96));box-shadow:0 24px 60px rgba(0,0,0,.5);animation:hero-in .7s ease-out both}
        .hero-orb{position:absolute;border-radius:50%;filter:blur(38px);pointer-events:none;opacity:.75}
        .hero-orb-a{width:320px;height:320px;left:-90px;top:-120px;background:#ff2e88;animation:orb-drift 16s ease-in-out infinite alternate}
        .hero-orb-b{width:280px;height:280px;right:-70px;top:-60px;background:#8b5cf6;animation:orb-drift 20s ease-in-out infinite alternate-reverse}
        .hero-orb-c{width:200px;height:200px;right:22%;bottom:-140px;background:#c6ff3d;opacity:.35;animation:orb-drift 14s ease-in-out infinite alternate}
        .hero-eyebrow{position:relative;z-index:1;color:#c6ff3d;font:500 .67rem 'DM Mono',monospace;letter-spacing:.19em;text-transform:uppercase}
        .hero-title{position:relative;z-index:1;font-size:clamp(2.4rem,4.8vw,4.2rem);line-height:.98;font-weight:900;letter-spacing:-.04em;margin:.4rem 0}
        .hero-title .line-a{background:linear-gradient(92deg,#ff2e88,#ffb020,#ff2e88);background-size:220% 100%;-webkit-background-clip:text;background-clip:text;color:transparent;animation:gradient-slide 6s ease-in-out infinite}
        .hero-title .line-b{background:linear-gradient(92deg,#c6ff3d,#8b5cf6,#c6ff3d);background-size:220% 100%;-webkit-background-clip:text;background-clip:text;color:transparent;animation:gradient-slide 7s ease-in-out infinite reverse}
        .hero-sub{position:relative;z-index:1;color:#d9c8f0;font-size:1rem;max-width:760px;line-height:1.7}
        .hero-badges{position:relative;z-index:1;display:flex;gap:.55rem;flex-wrap:wrap;margin-top:1rem}
        .hero-badge{padding:.37rem .63rem;border:1px solid #3b1f5e;border-radius:6px;background:rgba(255,46,136,.12);color:#ffd7ea;font:500 .59rem 'DM Mono',monospace;letter-spacing:.07em}
        .hero-badge.hot{background:#ff2e88;color:#fff;border-color:#ff2e88;box-shadow:0 0 18px rgba(255,46,136,.5)}
        .hero-badge.lime{background:rgba(198,255,61,.14);color:#e6ffb0;border-color:rgba(198,255,61,.45)}
        /* ---- dashboard / bento ---- */
        .section-kicker{color:#ff2e88;font:500 .62rem 'DM Mono',monospace;letter-spacing:.14em}
        .section-heading{display:flex;align-items:end;justify-content:space-between;gap:1rem;margin:.9rem 0 .55rem}
        .section-heading h2{font-size:1.08rem;margin:.2rem 0 0}.section-heading>span{color:#8a7aa3;font-size:.65rem}
        .metric-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem;margin:1rem 0}
        .metric-card{position:relative;overflow:hidden;background:linear-gradient(145deg,#1e0f38,#12081f);border:1px solid #3b1f5e;border-top:3px solid #ff2e88;border-radius:14px;padding:.9rem 1rem;min-height:82px;animation:fade-up .4s ease-out both;transition:transform .22s ease,box-shadow .22s ease}
        .metric-card:nth-child(2){border-top-color:#8b5cf6}.metric-card:nth-child(3){border-top-color:#ffb020}.metric-card:nth-child(4){border-top-color:#c6ff3d}
        .metric-card:hover{transform:translateY(-3px);box-shadow:0 14px 30px rgba(0,0,0,.4)}
        .metric-label{color:#c4b5d6;font:500 .59rem 'DM Mono',monospace;letter-spacing:.12em;text-transform:uppercase}
        .metric-value{color:#fff6ff;font-size:1.06rem;font-weight:700;margin-top:.42rem}.metric-value small{font:500 .66rem 'DM Mono',monospace;color:#c4b5d6}
        .dash-card{border:1px solid #3b1f5e;border-radius:18px;padding:1.1rem 1.2rem;background:linear-gradient(160deg,rgba(30,15,56,.96),rgba(18,8,31,.96));box-shadow:0 18px 40px rgba(0,0,0,.35)}
        .dash-card h3{margin:.2rem 0 .4rem}.dash-card p{color:#c4b5d6;font-size:.85rem;line-height:1.6}
        /* ---- characters ---- */
        .char-card{border:1px solid #3b1f5e;border-radius:16px;padding:1rem .85rem;background:linear-gradient(160deg,rgba(38,14,66,.95),rgba(16,7,30,.95));text-align:center;transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease}
        .char-card:hover{transform:translateY(-4px);border-color:var(--agent-accent);box-shadow:0 16px 32px rgba(0,0,0,.45)}
        .char-portrait{display:grid;place-items:center;margin-bottom:.4rem}
        .char-wrap{display:inline-block}.char-wrap svg{width:100%;height:100%;display:block}
        .char-avatar{display:inline-block;animation:char-bob 3.4s ease-in-out infinite}
        .char-avatar.char-working{animation:char-pulse 1.4s ease-in-out infinite}
        .char-avatar.char-complete{animation:char-glow 2.4s ease-in-out infinite}
        .char-avatar.char-error{filter:saturate(1.2)}
        .char-name{font-weight:900;letter-spacing:.06em}.char-role{color:#c4b5d6;font-size:.66rem;line-height:1.4}
        .char-catch{color:#e9d5ff;font-size:.64rem;font-style:italic;margin-top:.35rem;line-height:1.5}
        .char-status{display:inline-flex;align-items:center;gap:.4rem;margin-top:.6rem;padding:.22rem .55rem;border-radius:99px;border:1px solid var(--agent-accent);color:#fff;font:600 .55rem 'DM Mono',monospace;letter-spacing:.08em}
        .char-dot{width:8px;height:8px;border-radius:50%;background:var(--agent-accent);box-shadow:0 0 10px var(--agent-accent);animation:signal-pulse 1.6s ease-in-out infinite}
        .char-tools{color:#8a7aa3;font:500 .55rem 'DM Mono',monospace;margin-top:.4rem}
        .dock-title{font:700 .68rem 'DM Mono',monospace;letter-spacing:.14em;color:#ff2e88}
        .dock-sub{color:#c4b5d6;font-size:.72rem;line-height:1.5}
        /* sidebar dock cards are stacked, not a row */
        section[data-testid="stSidebar"] .char-card{margin-bottom:.8rem}
        /* ---- forms / buttons ---- */
        .stTextInput label,.stSelectbox label{color:#c4b5d6!important;font:500 .64rem 'DM Mono',monospace!important;letter-spacing:.1em!important;text-transform:uppercase!important}
        .stTextInput input{background:#12081f!important;border:1px solid #3b1f5e!important;border-radius:8px!important;color:#fff6ff!important;min-height:44px}
        .stTextInput input:focus{border-color:#ff2e88!important;box-shadow:0 0 0 1px rgba(255,46,136,.35)!important}
        .stSelectbox [data-baseweb='select']>div{background:#12081f!important;border:1px solid #3b1f5e!important;border-radius:8px!important;color:#fff6ff!important;min-height:44px}
        div.stButton>button,div[data-testid='stFormSubmitButton'] button{width:100%;min-height:44px;border-radius:8px;background:linear-gradient(115deg,#ff2e88,#8b5cf6)!important;border-color:#ff2e88!important;color:#fff!important;font:700 .72rem 'DM Mono',monospace;letter-spacing:.09em;box-shadow:0 10px 28px rgba(255,46,136,.35)!important;transition:all .18s ease}
        div.stButton>button:hover,div[data-testid='stFormSubmitButton'] button:hover{background:linear-gradient(115deg,#ff5aa3,#a78bfa)!important;box-shadow:0 14px 32px rgba(255,46,136,.5)!important;transform:translateY(-1px)}
        /* ---- Mission Control (v2, kept, restyled to v3) ---- */
        .mission-control{border:2px solid #ff2e88;border-radius:20px;padding:1.3rem 1.4rem;background:linear-gradient(150deg,#24103f,#0f061f);box-shadow:0 24px 60px rgba(0,0,0,.5),0 0 32px rgba(255,46,136,.18);position:relative;overflow:hidden;animation:fade-up .4s ease-out both}
        .mission-control:before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#ff2e88,#ffb020,#c6ff3d,#8b5cf6,transparent);background-size:200% 100%;animation:gradient-slide 6s linear infinite}
        .mission-live{border-color:#c6ff3d!important;box-shadow:0 0 0 1px rgba(198,255,61,.25),0 24px 60px rgba(0,0,0,.5)!important}
        .mission-head{display:flex;justify-content:space-between;align-items:end;gap:1rem}.mission-head h2{font-size:1.45rem;margin:.2rem 0 0}
        .mission-live-label{color:#c6ff3d;font:500 .58rem 'DM Mono',monospace;letter-spacing:.1em}.mission-live .mission-live-label{animation:signal-pulse 1.6s ease-in-out infinite}
        .mission-target{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin:.8rem 0 .6rem;padding:.6rem .75rem;border:1px solid #3b1f5e;border-radius:8px;background:#12081f;font-size:.68rem;color:#c4b5d6}.mission-target strong{color:#fff6ff}.mission-target span{color:#8a7aa3;font-family:'DM Mono',monospace;font-size:.6rem}
        .mission-progress{display:flex;align-items:center;gap:.8rem;margin:.2rem 0 .9rem}.mission-progress-track{flex:1;height:12px;border-radius:99px;background:#2a1447;overflow:hidden}.mission-progress-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#ff2e88,#ffb020,#c6ff3d);background-size:200% 100%;animation:gradient-slide 4s linear infinite;transition:width .6s ease}.mission-progress-pct{color:#c6ff3d;font:700 .9rem 'DM Mono',monospace;min-width:38px;text-align:right}
        .mission-timeline{display:flex;align-items:stretch;gap:.3rem;margin:.2rem 0 1rem;flex-wrap:wrap}.tl-node{flex:1;min-width:110px;border:1px solid #3b1f5e;border-radius:9px;padding:.55rem .6rem;background:#160a2a;transition:transform .18s ease}.tl-node:hover{transform:translateY(-2px)}.tl-mark{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;border:1px solid var(--agent-accent);color:var(--agent-accent);font-size:.6rem;font-weight:800;margin-bottom:.3rem}.tl-name{display:block;color:#fff6ff;font-weight:800;font-size:.68rem;letter-spacing:.05em}.tl-meta{display:block;color:#8a7aa3;font-size:.58rem;margin-top:.15rem}.tl-node.node-done{border-color:rgba(198,255,61,.5)}.tl-node.node-done .tl-mark{background:rgba(198,255,61,.15);color:#c6ff3d;border-color:rgba(198,255,61,.5)}.tl-node.node-current{border-color:#c6ff3d;box-shadow:0 0 22px rgba(198,255,61,.25);animation:console-breathe 2.2s ease-in-out infinite}.tl-node.node-current .tl-mark{animation:signal-pulse 1.2s ease-in-out infinite}.tl-node.node-error{border-color:rgba(255,115,115,.45)}.tl-node.node-error .tl-mark{color:#ff7373;border-color:#ff7373}.tl-connector{flex:0 0 14px;align-self:center;height:1px;background:#3b1f5e}
        .mission-feed-heading{display:flex;justify-content:space-between;color:#8a7aa3;font:500 .52rem 'DM Mono',monospace;letter-spacing:.1em;margin-bottom:.4rem}.mission-feed{max-height:340px;overflow-y:auto;padding-right:.4rem;scrollbar-width:thin;scrollbar-color:#3b1f5e transparent;border-top:1px solid rgba(59,31,94,.58)}
        .feed-row{display:grid;grid-template-columns:52px 62px 62px minmax(0,1fr);gap:.42rem;align-items:start;padding:.42rem 0;border-bottom:1px solid #3b1f5e;animation:fade-up .2s ease-out both}.feed-row time{color:#8a7aa3;font:400 .53rem 'DM Mono',monospace;padding-top:.13rem}.feed-agent{color:var(--agent-accent);font:500 .52rem 'DM Mono',monospace;letter-spacing:.04em}.feed-text{color:#e9d5ff;font-size:.61rem;line-height:1.48;overflow-wrap:anywhere}.mission-feed-empty{color:#8a7aa3;padding:.6rem 0;font-size:.64rem;line-height:1.6}
        .event-tag{display:inline-block;width:max-content;color:#c4b5d6;font:500 .49rem 'DM Mono',monospace;letter-spacing:.04em;border:1px solid #3b1f5e;border-radius:4px;padding:.11rem .25rem}
        /* ---- workstations (characters now, not abstract avatars) ---- */
        .agent-console{--agent-accent:#ff2e88;position:relative;overflow:hidden;border:1px solid #3b1f5e;border-radius:14px;margin:.2rem 0 .85rem;background:linear-gradient(150deg,#1a0b30,#0f061f);animation:fade-up .35s ease-out both}
        .agent-console.status-thinking,.agent-console.status-executing,.agent-console.status-finalizing{border-color:var(--agent-accent);animation:console-breathe 1.8s ease-in-out infinite}
        .agent-console.status-complete{border-color:rgba(198,255,61,.45)}.agent-console.status-error,.agent-console.status-fallback{border-color:rgba(255,178,124,.45)}
        .agent-console-topline{height:2px;background:linear-gradient(90deg,var(--agent-accent),transparent 72%)}
        .agent-console-header{display:flex;align-items:center;gap:.75rem;padding:.72rem .88rem .58rem}
        .agent-console-header .char-wrap{width:64px!important;height:64px!important;flex:0 0 64px}
        .agent-heading{flex:1;min-width:0}.agent-name-row{display:flex;align-items:center;gap:.55rem;flex-wrap:wrap}.agent-name-row h3{font-size:.79rem;letter-spacing:.08em;margin:0}.agent-heading p{color:#c4b5d6;font-size:.63rem;margin:.12rem 0 0}.agent-duration{color:#c4b5d6;font:500 .63rem 'DM Mono',monospace}
        .agent-status{display:inline-flex;align-items:center;gap:.32rem;border:1px solid #3b1f5e;border-radius:20px;padding:.18rem .4rem;color:#c4b5d6;font:500 .5rem 'DM Mono',monospace;letter-spacing:.05em}.agent-status i{width:5px;height:5px;border-radius:50%;background:#8a7aa3}.status-thinking .agent-status,.status-executing .agent-status,.status-finalizing .agent-status{color:var(--agent-accent);border-color:var(--agent-accent)}.status-thinking .agent-status i,.status-executing .agent-status i,.status-finalizing .agent-status i{background:var(--agent-accent);box-shadow:0 0 8px var(--agent-accent);animation:signal-pulse 1s ease-in-out infinite}.status-complete .agent-status{color:#c6ff3d;border-color:rgba(198,255,61,.3)}.status-complete .agent-status i{background:#c6ff3d}
        .agent-current{display:flex;flex-direction:column;gap:.22rem;margin:0 .88rem .62rem;padding:.5rem .6rem;border:1px solid #3b1f5e;border-radius:7px;background:#12081f}.current-label,.agent-feed-heading{color:#8a7aa3;font:500 .51rem 'DM Mono',monospace;letter-spacing:.1em}.current-text{color:#e9d5ff;font-size:.64rem;line-height:1.5;overflow-wrap:anywhere}.agent-feed-heading{display:flex;justify-content:space-between;margin:0 .9rem .35rem}.agent-feed{max-height:280px;overflow-y:auto;padding:0 .65rem .65rem .88rem;scrollbar-width:thin;scrollbar-color:#3b1f5e transparent}
        .agent-event{display:grid;grid-template-columns:52px 52px minmax(0,1fr);gap:.42rem;align-items:start;padding:.42rem 0;border-top:1px solid rgba(59,31,94,.58);animation:fade-up .2s ease-out both}.agent-event time{color:#8a7aa3;font:400 .53rem 'DM Mono',monospace;padding-top:.13rem}.event-tool-name{color:#e6ffb0;background:rgba(198,255,61,.09);padding:.08rem .25rem;border-radius:4px;margin-right:.3rem;font:500 .56rem 'DM Mono',monospace}.agent-empty{color:#8a7aa3;padding:.45rem 0;font-size:.62rem}
        /* ---- report / idle / footer ---- */
        .report-summary{padding:1rem 1.1rem;border:1px solid rgba(198,255,61,.4);border-radius:10px;background:linear-gradient(110deg,rgba(198,255,61,.08),rgba(139,92,246,.12));margin:.65rem 0 1rem}.report-summary-title{color:#e6ffb0;font-size:.91rem;font-weight:800}.report-summary-meta{color:#c4b5d6;font:400 .61rem 'DM Mono',monospace;margin-top:.35rem}
        .risk-panel{display:flex;align-items:center;gap:1rem;padding:.88rem 1rem;border:1px solid #3b1f5e;border-radius:10px;background:#160a2a;margin:.6rem 0 1rem}.risk-number{color:var(--risk-color);font-size:1.65rem;line-height:1;font-weight:800;min-width:50px}.risk-copy strong{display:block;color:#fff6ff;font-size:.75rem}.risk-copy span{display:block;color:#c4b5d6;font-size:.63rem;margin-top:.18rem}
        [data-testid='stExpander']{border:1px solid #3b1f5e!important;border-radius:10px!important;background:#160a2a!important;margin:.5rem 0!important}[data-testid='stExpander'] summary{color:#fff6ff!important;font-weight:700}[data-testid='stExpander'] details{border:0!important}
        .stDownloadButton button{border-radius:7px!important;background:#1e0f38!important;color:#fff6ff!important;border:1px solid #ff2e88!important;font:500 .67rem 'DM Mono',monospace!important}
        .idle-panel{border:2px dashed #ff2e88;border-radius:16px;padding:1.1rem 1.2rem;margin:1rem 0;background:linear-gradient(120deg,rgba(255,46,136,.12),rgba(139,92,246,.12))}.idle-panel strong{display:block;color:#fff6ff;font-size:.82rem}.idle-panel span{display:block;color:#d9c8f0;font-size:.68rem;line-height:1.6;margin-top:.3rem}
        .nx-footer{border-top:1px solid #3b1f5e;margin-top:2.6rem;padding-top:.9rem;display:flex;justify-content:space-between;color:#8a7aa3;font:400 .56rem 'DM Mono',monospace;letter-spacing:.07em}
        /* ---- animations ---- */
        @keyframes signal-pulse{0%,100%{opacity:.55;transform:scale(.88)}50%{opacity:1;transform:scale(1.16)}}
        @keyframes orb-drift{from{transform:translate(0,0) scale(1)}to{transform:translate(48px,28px) scale(1.18)}}
        @keyframes hero-in{from{opacity:0;transform:translateY(18px) scale(.995)}to{opacity:1;transform:translateY(0) scale(1)}}
        @keyframes gradient-slide{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
        @keyframes fade-up{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
        @keyframes char-bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
        @keyframes char-pulse{0%,100%{transform:scale(1);filter:brightness(1)}50%{transform:scale(1.06);filter:brightness(1.35)}}
        @keyframes char-glow{0%,100%{filter:drop-shadow(0 0 6px rgba(198,255,61,.25))}50%{filter:drop-shadow(0 0 18px rgba(198,255,61,.6))}}
        @keyframes console-breathe{0%,100%{box-shadow:0 0 14px rgba(255,46,136,.08)}50%{box-shadow:0 0 30px rgba(255,46,136,.22)}}
        @media(max-width:850px){.block-container{padding:1.1rem 1rem 2rem}.metric-row{grid-template-columns:repeat(2,1fr)}.mission-timeline{flex-direction:column}.tl-connector{display:none}.feed-row{grid-template-columns:42px 52px 52px minmax(0,1fr)}}
        @media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
        </style>
        """,
    )
