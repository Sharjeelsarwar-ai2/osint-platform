"""
Multi-Agent Orchestrator with Animated Agent Avatars
Each agent displays its unique character while working.
"""

import time
import streamlit as st
from config.settings import AGENT_CONFIG
from utils.groq_client import run_agent_with_tools
from agents.tools import execute_tool, GROQ_TOOL_DEFINITIONS


# ── Agent System Prompts ──

DOMAIN_RECON_PROMPT = """You are ARIA, an elite OSINT Domain Reconnaissance Specialist.
Your job is to gather comprehensive intelligence about a target domain.

You MUST use the available tools to gather REAL data. Do NOT fabricate any information.

Workflow:
1. Call `dns_lookup` with record_type "ALL" to get all DNS records
2. Call `whois_lookup` to get registration data
3. Call `enumerate_subdomains` to discover subdomains
4. Call `resolve_domain_to_ips` to map all IP addresses
5. For each unique IP found, call `analyze_ip`

After gathering all data, provide a structured analysis:
- Domain registration details and age
- DNS infrastructure overview
- Discovered subdomains and their purpose
- IP address analysis and hosting information
- Notable findings and potential concerns

Format your output in clear markdown with tables."""


THREAT_INTEL_PROMPT = """You are RAVEN, a senior Threat Intelligence Analyst.
Your job is to search for and analyze threat data related to a target.

You MUST use the available tools to gather REAL data. Do NOT fabricate findings.

Workflow:
1. Call `search_threat_intel` with the target domain/company name
2. Call `search_domain_reputation` to check for abuse reports
3. Call `search_company_news` to find recent security-related news

After gathering data, provide:
- Known security incidents or breaches
- CVE or vulnerability mentions
- Reputation analysis (clean vs flagged)
- Recent news that may indicate security posture
- Threat actor mentions if any
- Overall threat level assessment: CRITICAL / HIGH / MEDIUM / LOW / CLEAN

Format in clear markdown."""


ATTACK_SURFACE_PROMPT = """You are VULCAN, an expert Attack Surface Analyst and penetration tester.
Your job is to map the attack surface of a target.

You MUST use the available tools to gather REAL data. Do NOT guess.

Workflow:
1. Call `check_security_headers` with the target URL
2. Call `check_ssl_info` to analyze TLS configuration
3. Call `detect_technologies` to fingerprint the tech stack

After gathering data, provide:
- HTTP security header analysis with score
- SSL/TLS certificate health
- Detected technologies and their known vulnerabilities
- Exposed services and potential attack vectors
- Missing security controls
- Prioritized list of attack surface risks

Rate each finding: CRITICAL / HIGH / MEDIUM / LOW / INFO
Format in clear markdown with tables."""


EMAIL_OSINT_PROMPT = """You are CIPHER, an Email Security & OSINT Specialist.
Your job is to analyze the email infrastructure of a target domain.

You MUST use the available tools to gather REAL data.

Workflow:
1. Call `check_email_security` to analyze SPF, DMARC, DKIM, and MX records

After gathering data, provide:
- Mail server infrastructure analysis
- SPF configuration and effectiveness
- DMARC policy analysis (none/quarantine/reject)
- DKIM deployment status
- Email spoofing vulnerability assessment
- Email security score interpretation
- Recommendations for improvement

Format in clear markdown."""


REPORT_PROMPT = """You are ORACLE, a Senior OSINT Report Writer creating an executive threat intelligence report.

Based on ALL the findings from the previous agents, compile a comprehensive final report:

1. **Executive Summary** (2-3 paragraphs for C-suite)
2. **Overall Risk Score**: Provide a score from 0-100 (100 = most risky)
   - Include the exact text "Overall Risk Score: X/100"
3. **Risk Level**: CRITICAL / HIGH / MEDIUM / LOW
4. **Key Findings Summary Table** (ID, Finding, Severity, Category)
5. **Attack Surface Overview**
6. **Email Security Posture**
7. **Threat Intelligence Summary**
8. **Top 10 Recommendations** (prioritized)
9. **Remediation Roadmap** (Immediate / Short-term / Long-term)
10. **Security Grade**: A+ through F
    - Include the exact text "Security Grade: [LETTER]"

Be specific and reference the actual data gathered. Do NOT fabricate findings.
Format as a professional report in markdown."""


def render_agent_avatar(agent_key: str, status: str = "WORKING") -> str:
    """Generate HTML for an animated agent avatar card."""
    agent = AGENT_CONFIG[agent_key]
    return f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 1.5rem;
        padding: 1.5rem 2rem;
        background: linear-gradient(135deg, rgba(17,24,39,0.9), rgba(30,41,59,0.6));
        border: 2px solid {agent['color']};
        border-radius: 20px;
        margin: 1rem 0;
        box-shadow: 0 0 30px {agent['color']}40, inset 0 0 20px rgba(0,0,0,0.3);
        animation: slideIn 0.5s ease-out;
        position: relative;
        overflow: hidden;
    ">
        <!-- Animated background pulse -->
        <div style="
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(circle at 10% 50%, {agent['color']}15 0%, transparent 60%);
            animation: bgPulse 2s ease-in-out infinite;
        "></div>

        <!-- Avatar with rotating ring -->
        <div style="
            position: relative;
            width: 100px;
            height: 100px;
            flex-shrink: 0;
            z-index: 2;
        ">
            <!-- Rotating ring -->
            <div style="
                position: absolute;
                top: -8px; left: -8px;
                width: 116px; height: 116px;
                border: 3px solid transparent;
                border-top-color: {agent['color']};
                border-right-color: {agent['color']}80;
                border-radius: 50%;
                animation: spin 2s linear infinite;
            "></div>

            <!-- Inner glow ring -->
            <div style="
                position: absolute;
                top: 0; left: 0;
                width: 100px; height: 100px;
                border-radius: 50%;
                background: {agent['color']};
                opacity: 0.2;
                animation: innerPulse 1.5s ease-in-out infinite;
            "></div>

            <!-- Avatar image -->
            <img src="{agent['avatar_url']}" style="
                width: 100px;
                height: 100px;
                border-radius: 50%;
                border: 3px solid {agent['color']};
                background: #0a0e17;
                box-shadow: 0 0 20px {agent['color']}80;
                animation: avatarFloat 3s ease-in-out infinite;
                position: relative;
                z-index: 1;
            " alt="{agent['codename']}"/>

            <!-- Status dot -->
            <div style="
                position: absolute;
                bottom: 5px; right: 5px;
                width: 20px; height: 20px;
                background: #00ff00;
                border: 3px solid #0a0e17;
                border-radius: 50%;
                animation: statusBlink 1s ease-in-out infinite;
                z-index: 3;
                box-shadow: 0 0 10px #00ff00;
            "></div>
        </div>

        <!-- Agent info -->
        <div style="flex: 1; z-index: 2;">
            <div style="display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.3rem;">
                <span style="font-size: 1.8rem;">{agent['icon']}</span>
                <div>
                    <div style="
                        font-family: 'Orbitron', monospace;
                        font-size: 1.3rem;
                        font-weight: 900;
                        color: {agent['color']};
                        letter-spacing: 3px;
                        text-shadow: 0 0 10px {agent['color']}80;
                    ">
                        {agent['codename']}
                    </div>
                    <div style="
                        font-family: 'Rajdhani', sans-serif;
                        font-size: 0.75rem;
                        color: #94a3b8;
                        letter-spacing: 2px;
                        text-transform: uppercase;
                    ">
                        {agent['name']} Agent
                    </div>
                </div>
            </div>

            <div style="
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-top: 0.6rem;
            ">
                <!-- Typing dots animation -->
                <div style="display: flex; gap: 4px;">
                    <span style="
                        width: 8px; height: 8px;
                        background: {agent['color']};
                        border-radius: 50%;
                        animation: typingDot 1.4s ease-in-out infinite;
                        animation-delay: 0s;
                    "></span>
                    <span style="
                        width: 8px; height: 8px;
                        background: {agent['color']};
                        border-radius: 50%;
                        animation: typingDot 1.4s ease-in-out infinite;
                        animation-delay: 0.2s;
                    "></span>
                    <span style="
                        width: 8px; height: 8px;
                        background: {agent['color']};
                        border-radius: 50%;
                        animation: typingDot 1.4s ease-in-out infinite;
                        animation-delay: 0.4s;
                    "></span>
                </div>

                <p style="
                    margin: 0;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.9rem;
                    color: #e2e8f0;
                    font-style: italic;
                ">
                    {agent['catchphrase']}
                </p>
            </div>

            <!-- Status badge -->
            <div style="margin-top: 0.6rem;">
                <span style="
                    display: inline-block;
                    padding: 3px 10px;
                    background: {agent['color']}20;
                    border: 1px solid {agent['color']};
                    border-radius: 12px;
                    font-family: 'Orbitron', monospace;
                    font-size: 0.65rem;
                    color: {agent['color']};
                    letter-spacing: 2px;
                    font-weight: 700;
                ">
                    ● {status}
                </span>
                <span style="
                    margin-left: 0.5rem;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.7rem;
                    color: #64748b;
                ">
                    Executing real-world tools...
                </span>
            </div>
        </div>
    </div>

    <style>
        @keyframes slideIn {{
            0% {{ transform: translateX(-30px); opacity: 0; }}
            100% {{ transform: translateX(0); opacity: 1; }}
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        @keyframes avatarFloat {{
            0%,100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-5px); }}
        }}
        @keyframes innerPulse {{
            0%,100% {{ transform: scale(1); opacity: 0.2; }}
            50% {{ transform: scale(1.15); opacity: 0.4; }}
        }}
        @keyframes statusBlink {{
            0%,100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.5; transform: scale(0.8); }}
        }}
        @keyframes typingDot {{
            0%,60%,100% {{ transform: translateY(0); opacity: 0.4; }}
            30% {{ transform: translateY(-8px); opacity: 1; }}
        }}
        @keyframes bgPulse {{
            0%,100% {{ opacity: 0.5; }}
            50% {{ opacity: 1; }}
        }}
    </style>
    """


def render_agent_complete(agent_key: str) -> str:
    """Show a 'complete' badge after agent finishes."""
    agent = AGENT_CONFIG[agent_key]
    return f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.8rem 1.5rem;
        background: linear-gradient(135deg, rgba(17,24,39,0.6), rgba(30,41,59,0.4));
        border-left: 4px solid {agent['color']};
        border-radius: 8px;
        margin: 0.3rem 0;
        opacity: 0.7;
    ">
        <img src="{agent['avatar_url']}" style="
            width: 40px; height: 40px;
            border-radius: 50%;
            border: 2px solid {agent['color']};
            background: #0a0e17;
        "/>
        <div style="flex: 1;">
            <span style="
                font-family: 'Orbitron', monospace;
                font-size: 0.75rem;
                color: {agent['color']};
                font-weight: 700;
                letter-spacing: 2px;
            ">
                {agent['codename']}
            </span>
            <span style="
                color: #94a3b8;
                font-size: 0.8rem;
                margin-left: 0.5rem;
            ">
                — {agent['name']} analysis complete
            </span>
        </div>
        <span style="
            color: #00ff00;
            font-size: 1.2rem;
        ">✓</span>
    </div>
    """


def run_osint_audit(target: str, target_type: str) -> dict:
    """Run the full OSINT audit pipeline with animated agent avatars."""

    results = {}
    progress_bar = st.progress(0, text="Initializing OSINT agents...")
    
    # Container for the active agent avatar
    active_agent_box = st.empty()
    # Container for completed agents (persistent)
    completed_container = st.container()
    completed_agents = []

    def show_working(agent_key):
        with active_agent_box.container():
            st.markdown(render_agent_avatar(agent_key, "WORKING"), unsafe_allow_html=True)

    def mark_complete(agent_key):
        completed_agents.append(agent_key)
        active_agent_box.empty()
        with completed_container:
            st.markdown(render_agent_complete(agent_key), unsafe_allow_html=True)

    # ── Agent 1: ARIA - Domain Recon ──
    show_working("domain_recon")
    results["domain_recon"] = run_agent_with_tools(
        system_prompt=DOMAIN_RECON_PROMPT,
        user_prompt=f"Perform full domain reconnaissance on: {target}",
        tools=GROQ_TOOL_DEFINITIONS,
        tool_executor=execute_tool,
        max_rounds=6
    )
    progress_bar.progress(20, text="ARIA finished domain recon")
    mark_complete("domain_recon")
    time.sleep(0.3)

    # ── Agent 2: RAVEN - Threat Intel ──
    show_working("threat_intel")
    results["threat_intel"] = run_agent_with_tools(
        system_prompt=THREAT_INTEL_PROMPT,
        user_prompt=f"Analyze threat intelligence for: {target}",
        tools=GROQ_TOOL_DEFINITIONS,
        tool_executor=execute_tool,
        max_rounds=4
    )
    progress_bar.progress(40, text="RAVEN finished threat intel")
    mark_complete("threat_intel")
    time.sleep(0.3)

    # ── Agent 3: VULCAN - Attack Surface ──
    show_working("attack_surface")
    url_target = target if target.startswith("http") else f"https://{target}"
    results["attack_surface"] = run_agent_with_tools(
        system_prompt=ATTACK_SURFACE_PROMPT,
        user_prompt=f"Map the attack surface for: {url_target}",
        tools=GROQ_TOOL_DEFINITIONS,
        tool_executor=execute_tool,
        max_rounds=4
    )
    progress_bar.progress(60, text="VULCAN finished attack surface mapping")
    mark_complete("attack_surface")
    time.sleep(0.3)

    # ── Agent 4: CIPHER - Email OSINT ──
    show_working("email_osint")
    results["email_osint"] = run_agent_with_tools(
        system_prompt=EMAIL_OSINT_PROMPT,
        user_prompt=f"Analyze email security for domain: {target}",
        tools=GROQ_TOOL_DEFINITIONS,
        tool_executor=execute_tool,
        max_rounds=3
    )
    progress_bar.progress(80, text="CIPHER finished email OSINT")
    mark_complete("email_osint")
    time.sleep(0.3)

    # ── Agent 5: ORACLE - Report Generator ──
    show_working("report_gen")
    combined = "\n\n".join([
        f"=== DOMAIN RECON (ARIA) ===\n{results.get('domain_recon', '')}",
        f"=== THREAT INTEL (RAVEN) ===\n{results.get('threat_intel', '')}",
        f"=== ATTACK SURFACE (VULCAN) ===\n{results.get('attack_surface', '')}",
        f"=== EMAIL OSINT (CIPHER) ===\n{results.get('email_osint', '')}"
    ])
    results["final_report"] = run_agent_with_tools(
        system_prompt=REPORT_PROMPT,
        user_prompt=f"Compile the final OSINT report for {target} using these findings:\n\n{combined[:8000]}",
        tools=[],
        tool_executor=execute_tool,
        max_rounds=1
    )
    progress_bar.progress(100, text="ORACLE finished compiling report!")
    mark_complete("report_gen")
    time.sleep(0.5)

    progress_bar.empty()

    return results