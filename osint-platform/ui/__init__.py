"""v3 UI package: presentation only.

Backend agent architecture lives in agents/ and utils/ and is unchanged.
This package only composes what Streamlit shows: layout, characters,
Mission Control presentation, and the report view.
"""

from ui.avatars import avatar_html, avatar_svg  # noqa: F401
from ui.components import (  # noqa: F401
    activity_panel_html,
    command_bar_html,
    hero_html,
    metrics_html,
    render_agent_dock,
    render_command_bar,
    render_hero,
    render_idle_state,
)
from ui.report import render_report  # noqa: F401
from ui.styles import get_css  # noqa: F401
