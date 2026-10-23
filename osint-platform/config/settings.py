"""
Global settings for the OSINT & Threat Intelligence Platform.
"""

import os

# ──────────────────────────────────────────────
#  GROQ / LLM SETTINGS
# ──────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL_NAME = "llama-3.3-70b-versatile"
MAX_TOKENS = 4096
TEMPERATURE = 0.2

# ──────────────────────────────────────────────
#  SEVERITY COLORS
# ──────────────────────────────────────────────
SEVERITY_COLORS = {
    "CRITICAL": "#FF0040",
    "HIGH":     "#FF6B35",
    "MEDIUM":   "#FFD700",
    "LOW":      "#00D4AA",
    "INFO":     "#4A90D9",
}

# ──────────────────────────────────────────────
#  AGENT PROFILES  (avatars via DiceBear — free, no key)
# ──────────────────────────────────────────────
AGENT_PROFILES = {
    "aria": {
        "name": "ARIA",
        "role": "Domain Recon Agent",
        "icon": "🌐",
        "color": "#00f5d4",
        "catchphrase": "Scanning the digital perimeter...",
        "description": (
            "Expert in DNS enumeration, WHOIS analysis, subdomain discovery, "
            "and domain infrastructure mapping."
        ),
        "avatar_url": (
            "https://api.dicebear.com/7.x/bottts-neutral/svg"
            "?seed=Aria&backgroundColor=0a0e17&eyes=glow"
        ),
    },
    "raven": {
        "name": "RAVEN",
        "role": "Threat Intelligence Agent",
        "icon": "🔍",
        "color": "#ff0040",
        "catchphrase": "Hunting threats in the shadows...",
        "description": (
            "Specialist in threat intelligence gathering, reputation analysis, "
            "and dark-web mention detection via open-source feeds."
        ),
        "avatar_url": (
            "https://api.dicebear.com/7.x/bottts-neutral/svg"
            "?seed=Raven&backgroundColor=0a0e17&eyes=robocop"
        ),
    },
    "vulcan": {
        "name": "VULCAN",
        "role": "Attack Surface Agent",
        "icon": "🗺️",
        "color": "#ff6b35",
        "catchphrase": "Mapping the attack vectors...",
        "description": (
            "Focused on attack surface mapping, security header analysis, "
            "SSL/TLS inspection, and technology fingerprinting."
        ),
        "avatar_url": (
            "https://api.dicebear.com/7.x/bottts-neutral/svg"
            "?seed=Vulcan&backgroundColor=0a0e17&eyes=shade01"
        ),
    },
    "cipher": {
        "name": "CIPHER",
        "role": "Email OSINT Agent",
        "icon": "📧",
        "color": "#7c3aed",
        "catchphrase": "Decoding email infrastructure...",
        "description": (
            "Expert in email security analysis including SPF, DMARC, DKIM "
            "record validation and mail server reconnaissance."
        ),
        "avatar_url": (
            "https://api.dicebear.com/7.x/bottts-neutral/svg"
            "?seed=Cipher&backgroundColor=0a0e17&eyes=sensor"
        ),
    },
    "oracle": {
        "name": "ORACLE",
        "role": "Report Synthesis Agent",
        "icon": "📊",
        "color": "#ffd700",
        "catchphrase": "Synthesizing intelligence...",
        "description": (
            "Senior analyst that synthesizes all agent findings into a "
            "comprehensive, executive-grade threat intelligence report."
        ),
        "avatar_url": (
            "https://api.dicebear.com/7.x/bottts-neutral/svg"
            "?seed=Oracle&backgroundColor=0a0e17&eyes=round"
        ),
    },
}
