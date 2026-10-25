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

## UI — `ui-v3-full-refactor` branch (v3, replaces the v2 layout)

V2 kept the Neon Noir colours (user liked them) but kept the old vertical
layout (hero → metrics → roster → form → report), so it still looked like
the previous UI. V3 is a full layout + UI-architecture refactor:

- **New layout, not a scroll:** a persistent **Agent Dock in the sidebar**
  (5 large SVG character portraits, always visible), a top **Command Bar**,
  a dashboard hero strip + operation-status bento, a metrics bento row,
  and a dashboard split — Operations (launch form + Mission Control) on
  the left, Live Activity panel on the right — with workstations and the
  report below. No more hero → metrics → roster → form in the old order.
- **UI architecture (frontend only):** `osint-platform/app.py` is now a
  thin composition entry point. Presentation lives in `osint-platform/ui/`:
  `styles.py` (Neon Noir CSS + layout/character animation),
  `components.py` (command bar, hero, metrics, dock, activity panel,
  status bento, idle state — pure HTML builders + thin Streamlit wrappers),
  `avatars.py` + `ui/avatars/*.svg` (committed character portraits),
  `report.py` (risk panel, findings, JSON/PDF downloads).
- **Agent characters / avatars (headline):** each agent has a distinct
  committed SVG portrait with face, silhouette and accessory:
  ARIA (magenta scout, radar antenna), RAVEN (violet hooded hunter),
  VULCAN (amber angular forge mapper), CIPHER (lime round decoder with
  code eyes and envelope), ORACLE (fuchsia crowned synthesizer with
  crystal). Characters are large in the dock, in workstations and in the
  Mission Control timeline; they bob on idle, pulse/scan while working,
  glow on complete, and show an error state — driven by REAL status only.
- **Backend architecture unchanged:** same Streamlit framework, same
  5-agent pipeline ARIA → RAVEN → VULCAN → CIPHER → ORACLE, same Groq
  model and 12 tools, same `run_osint_audit` data flow, same findings /
  risk / JSON / PDF features (v1 PDF fix preserved).
- **Real activity, no simulation:** Mission Control and the Live Activity
  panel stay always-visible and are driven only by real orchestrator
  callbacks / session state. Idle honestly says standby.

## UI — `ui-v2-radical-animated` branch (v2, replaces the v1 look)

V1 kept the old cyan-blue hero and layout, so on idle it looked almost
unchanged. V2 is unmistakably different at first glance:

- **New colour scheme — NEON NOIR:** violet-black obsidian background
  with vivid magenta (#FF2E88), violet (#8B5CF6), electric lime (#C6FF3D)
  and amber (#FFB020). Agent accents: ARIA magenta, RAVEN violet, VULCAN
  amber, CIPHER lime, ORACLE fuchsia. No cyan-blue dominant scheme.
- **New hero:** "Track the invisible. / Expose the truth." in animated
  magenta→amber and lime→violet gradients, inside a glass panel with
  three drifting aurora orbs (magenta, violet, lime), staggered entrance,
  and badges "REAL AGENTS · NO SIMULATION".
- **Live Team Board, always at the top:** five large agent cards with
  bobbing glowing avatars, pulsing status dots, role, catchphrase and
  real status/tools from session state (STANDBY on idle, WORKING during
  a scan). Ambient motion only on idle — no fake work.
- **Mission Control, always visible:** on idle it honestly shows 0%,
  all agents queued and an empty feed; during a real scan it lights up
  with the pipeline timeline, live agent cards, progress, elapsed time
  and the chronological global activity feed (real events only).
- **Live agent activity — real, not simulated:** each agent workstation
  shows its true status (queued / analyzing / running tool / synthesizing /
  complete / partial / needs attention) and the exact tools it executed.
  A global activity feed merges every agent's real events chronologically.
  When idle, the UI honestly shows standby — no fake activity.
- `prefers-reduced-motion` is still honoured.
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
