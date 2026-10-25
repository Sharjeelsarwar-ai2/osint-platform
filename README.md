# osint-platform — NEXUS OSINT Intelligence

A coordinated, multi-agent OSINT platform (Streamlit). Passive reconnaissance
only — use only targets you are authorized to assess.

## Architecture (preserved — do not swap)

- **UI:** Streamlit, single page in `osint-platform/app.py`
- **Orchestration:** `osint-platform/agents/orchestrator.py` — sequential pipeline
  ARIA (domain recon, 3 rounds) → RAVEN (threat intel, 2) → VULCAN (attack
  surface, 2) → CIPHER (email OSINT, 1) → ORACLE (report synthesis, no tools,
  synthesizes the other four agents' findings)
- **Model/tools:** Groq (`openai/gpt-oss-120b`) tool-calling in
  `osint-platform/utils/groq_client.py`; 12 real OSINT tools in
  `osint-platform/agents/tools.py` (DNS, WHOIS, subdomains, security headers,
  SSL, IP, email security, threat/reputation/company search, tech detection)
- **Config:** `osint-platform/config/settings.py` — agent profiles, model, key
  from `GROQ_API_KEY` env / Streamlit secrets (never committed)

## UI — `ui-advanced-animated` branch

- Aurora/gradient dark theme, glass panels, staggered reveals, hover glow
  and sheen, breathing/pulsing cards for running agents, animated progress
  bars, and `prefers-reduced-motion` support.
- **Mission Control:** pipeline timeline (done / current / queued / error),
  overall progress, tools executed, event count, elapsed time.
- **Live agent activity — real, not simulated:** each agent workstation
  shows its true status (queued / analyzing / running tool / synthesizing /
  complete / partial / needs attention) and the exact tools it executed.
  A global activity feed merges every agent's real events chronologically.
  When idle, the UI honestly shows standby — no fake activity.
- Report view keeps the risk-score panel, per-agent findings with tools
  executed, JSON download, and a PDF download (fixed: it previously
  exported a blank PDF because it looked up legacy task keys).

## Run

```bash
cd osint-platform
pip install -r requirements.txt
GROQ_API_KEY=your-key streamlit run app.py
```

Without a Groq key the app loads, shows the standby state and a key
warning, and refuses to start a scan — it never fakes a run.

## Tests

```bash
cd osint-platform
python -m pytest tests/ -q
```
