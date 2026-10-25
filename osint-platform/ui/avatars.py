"""Committed SVG character portraits, one per agent.

Files live in ui/avatars/<agent>.svg so the characters are part of the
repo, not an external avatar service and not an emoji. Each portrait has
a distinct silhouette, face and accessory matched to its role, in its
Neon Noir accent colour. Animation is applied by CSS classes on the
wrapper, driven by the agent's REAL status — idle bobbing is ambient
only and never claims a scan is running.
"""
import html
from pathlib import Path

AGENT_KEYS = ("aria", "raven", "vulcan", "cipher", "oracle")

_AVATAR_DIR = Path(__file__).resolve().parent / "avatars"

# Status -> wrapper class used by ui/styles.py. Working states pulse/scan;
# complete glows; error uses the amber/orange treatment; queued/idle bobs.
STATUS_CLASS = {
    "queued": "char-idle",
    "deploying": "char-working",
    "thinking": "char-working",
    "executing": "char-working",
    "finalizing": "char-working",
    "complete": "char-complete",
    "fallback": "char-error",
    "error": "char-error",
}


def avatar_svg(agent_key, status="queued"):
    """Return the raw SVG for one agent, wrapped for status animation.

    Raises FileNotFoundError for an unknown key, so a missing portrait
    fails loudly in tests instead of silently rendering nothing.
    """
    if agent_key not in AGENT_KEYS:
        raise KeyError(f"unknown agent: {agent_key}")
    svg = (_AVATAR_DIR / f"{agent_key}.svg").read_text(encoding="utf-8")
    cls = STATUS_CLASS.get(status, "char-idle")
    # The SVG already carries its own <title>; the wrapper only adds size
    # and the status animation class. Strip the XML declaration if present.
    svg = svg.strip()
    return f'<span class="char-avatar {cls}">{svg}</span>'


def avatar_html(agent_key, status="queued", size=120):
    """Avatar HTML at a given pixel size (CSS controls the inner SVG)."""
    if agent_key not in AGENT_KEYS:
        raise KeyError(f"unknown agent: {agent_key}")
    return (
        f'<span class="char-wrap" style="width:{int(size)}px;height:{int(size)}px">'
        f"{avatar_svg(agent_key, status)}</span>"
    )


def character_card_html(agent_key, profile, status_text, tools_text, status="queued"):
    """One large character card for the dock / team board / spotlight."""
    color = html.escape(str(profile.get("color", "#FF2E88")))
    return (
        f'<div class="char-card" style="--agent-accent:{color}">'
        f'<div class="char-portrait">{avatar_html(agent_key, status, size=132)}</div>'
        f'<div class="char-name">{html.escape(str(profile.get("name", agent_key)))}</div>'
        f'<div class="char-role">{html.escape(str(profile.get("role", "")))}</div>'
        f'<div class="char-catch">“{html.escape(str(profile.get("catchphrase", "")))}”</div>'
        f'<div class="char-status"><span class="char-dot"></span>{html.escape(status_text)}</div>'
        f'<div class="char-tools">{html.escape(tools_text)}</div>'
        "</div>"
    )
