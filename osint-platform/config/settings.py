import os

try:
    import streamlit as st
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
except Exception:
    from dotenv import load_dotenv
    load_dotenv()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

MODEL_NAME = "openai/gpt-oss-120b"
MAX_TOKENS = 4096
TEMPERATURE = 0.2

# Avatar URLs - DiceBear API (free, no key needed, SVG avatars)
# Each agent gets a unique character avatar

AGENT_CONFIG = {
    "domain_recon": {
        "name": "Domain Recon",
        "codename": "ARIA",
        "icon": "🌐",
        "color": "#00f5d4",
        "description": "DNS records, WHOIS, subdomain enumeration",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Aria&backgroundColor=00f5d4&eyes=glow",
        "catchphrase": "Scanning the digital perimeter..."
    },
    "threat_intel": {
        "name": "Threat Intel",
        "codename": "RAVEN",
        "icon": "🔍",
        "color": "#ff0040",
        "description": "Breach data, threat feeds, reputation",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Raven&backgroundColor=ff0040&eyes=robocop",
        "catchphrase": "Hunting threats in the shadows..."
    },
    "attack_surface": {
        "name": "Attack Surface",
        "codename": "VULCAN",
        "icon": "🗺️",
        "color": "#ff6b35",
        "description": "HTTP headers, exposed services, TLS",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Vulcan&backgroundColor=ff6b35&eyes=shade01",
        "catchphrase": "Mapping the attack vectors..."
    },
    "email_osint": {
        "name": "Email OSINT",
        "codename": "CIPHER",
        "icon": "📧",
        "color": "#7c3aed",
        "description": "SPF, DMARC, DKIM, mail server analysis",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Cipher&backgroundColor=7c3aed&eyes=sensor",
        "catchphrase": "Decoding email infrastructure..."
    },
    "report_gen": {
        "name": "Report Gen",
        "codename": "ORACLE",
        "icon": "📊",
        "color": "#ffd700",
        "description": "Risk scoring, executive summary, PDF",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Oracle&backgroundColor=ffd700&eyes=round",
        "catchphrase": "Synthesizing intelligence..."
    }
}

SEVERITY_COLORS = {
    "CRITICAL": "#FF0040",
    "HIGH": "#FF6B35",
    "MEDIUM": "#FFD700",
    "LOW": "#00D4AA",
    "INFO": "#4A90D9"
}