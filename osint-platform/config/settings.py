import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL_NAME = "openai/gpt-oss-120b"
MAX_TOKENS = 4096
TEMPERATURE = 0.2

SEVERITY_COLORS = {
    "CRITICAL": "#FF0040",
    "HIGH":     "#FF6B35",
    "MEDIUM":   "#FFD700",
    "LOW":      "#00D4AA",
    "INFO":     "#4A90D9",
}

AGENT_PROFILES = {
    "aria": {
        "name": "ARIA",
        "role": "Domain Recon Agent",
        "icon": "🌐",
        "color": "#FF2E88",
        "catchphrase": "Scanning the digital perimeter...",
        "description": "Expert in DNS enumeration, WHOIS analysis, subdomain discovery, and domain infrastructure mapping.",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Aria&backgroundColor=0a0e17&eyes=glow",
    },
    "raven": {
        "name": "RAVEN",
        "role": "Threat Intelligence Agent",
        "icon": "🔍",
        "color": "#A78BFA",
        "catchphrase": "Hunting threats in the shadows...",
        "description": "Specialist in threat intelligence gathering, reputation analysis, and dark-web mention detection.",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Raven&backgroundColor=0a0e17&eyes=robocop",
    },
    "vulcan": {
        "name": "VULCAN",
        "role": "Attack Surface Agent",
        "icon": "🗺️",
        "color": "#FFB020",
        "catchphrase": "Mapping the attack vectors...",
        "description": "Focused on attack surface mapping, security header analysis, SSL/TLS inspection, and technology fingerprinting.",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Vulcan&backgroundColor=0a0e17&eyes=shade01",
    },
    "cipher": {
        "name": "CIPHER",
        "role": "Email OSINT Agent",
        "icon": "📧",
        "color": "#C6FF3D",
        "catchphrase": "Decoding email infrastructure...",
        "description": "Expert in email security analysis including SPF, DMARC, DKIM record validation.",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Cipher&backgroundColor=0a0e17&eyes=sensor",
    },
    "oracle": {
        "name": "ORACLE",
        "role": "Report Synthesis Agent",
        "icon": "📊",
        "color": "#E879F9",
        "catchphrase": "Synthesizing intelligence...",
        "description": "Senior analyst that synthesizes all agent findings into a comprehensive threat intelligence report.",
        "avatar_url": "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=Oracle&backgroundColor=0a0e17&eyes=round",
    },
}

# Backwards compat
AGENT_CONFIG = AGENT_PROFILES
