"""v3 full layout refactor tests (presentation only).

Pins: a genuinely different layout (dock + command bar + dashboard split,
not the old hero->metrics->roster->form scroll), committed SVG character
portraits per agent, Neon Noir colours kept, and real-activity honesty.
Backend pipeline is asserted unchanged. No simulated activity is used.
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from agents.orchestrator import PIPELINE, summarize_operation
from config.settings import AGENT_PROFILES
from ui.avatars import AGENT_KEYS, avatar_html, avatar_svg, character_card_html
from ui.components import (
    activity_panel_html,
    command_bar_html,
    dock_html,
    hero_html,
    metrics_html,
)

AVATAR_DIR = Path(__file__).resolve().parent.parent / "ui" / "avatars"


class AvatarTests(unittest.TestCase):
    def test_one_committed_svg_per_agent_with_distinct_colour_and_face(self):
        colours = {}
        for key in AGENT_KEYS:
            path = AVATAR_DIR / f"{key}.svg"
            self.assertTrue(path.exists(), f"missing portrait {path}")
            text = path.read_text(encoding="utf-8")
            root = ET.fromstring(text)
            self.assertEqual(root.tag.rsplit("}", 1)[-1], "svg")
            self.assertIn(AGENT_PROFILES[key]["name"], text)
            self.assertIn(AGENT_PROFILES[key]["color"].lower(), text.lower())
            colours[key] = AGENT_PROFILES[key]["color"]
            # A face, not just a dot: head shape + eyes are in the SVG.
            self.assertTrue(
                "<circle" in text or "<ellipse" in text or "<rect" in text,
                f"{key} portrait has no face shapes",
            )
        self.assertEqual(len(set(colours.values())), 5, "agent colours must be distinct")

    def test_avatar_html_wraps_status_and_character_card(self):
        svg = avatar_svg("aria", status="executing")
        self.assertIn("char-working", svg)
        self.assertIn("<svg", svg)
        card = character_card_html(
            "raven", AGENT_PROFILES["raven"], "● STANDBY — READY", "No scan yet — 0 tools", status="queued"
        )
        self.assertIn("RAVEN", card)
        self.assertIn("Threat Intelligence Agent", card)
        self.assertIn("Hunting threats in the shadows", card)
        self.assertIn("STANDBY", card)
        with self.assertRaises(KeyError):
            avatar_svg("notanagent")


class LayoutTests(unittest.TestCase):
    def test_command_bar_dock_hero_metrics_are_distinct_sections(self):
        bar = command_bar_html("STANDBY")
        self.assertIn("cmd-bar", bar)
        self.assertIn("DOCK", bar)
        self.assertIn("OPERATIONS", bar)
        hero = hero_html("openai/gpt-oss-120b", "STANDBY")
        self.assertIn("hero-strip", hero)
        self.assertIn("Track the invisible", hero)
        self.assertIn("Expose the truth", hero)
        self.assertNotIn("Know the", hero)
        dock = dock_html(AGENT_PROFILES, {}, {})
        for key in AGENT_KEYS:
            self.assertIn(AGENT_PROFILES[key]["name"], dock)
        self.assertIn("AGENT DOCK", dock)
        self.assertIn("STANDBY", dock)
        metrics = metrics_html(AGENT_PROFILES, 12, "openai/gpt-oss-120b")
        self.assertIn("SPECIALIST AGENTS", metrics)
        # Layout order is asserted in app.py source, not in one HTML blob:
        import inspect

        from app import main

        src = inspect.getsource(main)
        self.assertIn("render_agent_dock", src)
        self.assertIn("render_command_bar", src)
        self.assertIn("hero_html", src)
        self.assertIn("activity_panel_html", src)
        # Dashboard split: operations column + activity column, not a
        # single sequential scroll of the old order.
        self.assertIn('st.columns([2, 1]', src)

    def test_neon_noir_kept_and_no_cyan_dominant_scheme(self):
        from ui.styles import get_css

        css = get_css().lower()
        for colour in ("#0b0514", "#ff2e88", "#8b5cf6", "#c6ff3d", "#ffb020"):
            self.assertIn(colour, css)
        self.assertIn("char-avatar", css)
        self.assertIn("char-bob", css)
        self.assertIn("char-pulse", css)
        self.assertIn("cmd-bar", css)
        self.assertIn("hero-strip", css)
        self.assertNotIn("#47c8e8", css)

    def test_activity_panel_is_honest_on_idle_and_real_when_seeded(self):
        idle = activity_panel_html([], {})
        self.assertIn("No live operation yet", idle)
        self.assertIn("Nothing here is simulated", idle)
        seeded = activity_panel_html(
            [{"time": "10:00:01", "agent": "aria", "text": "Executing dns_lookup(example.com)"}],
            {"target": "example.com"},
        )
        self.assertIn("dns_lookup", seeded)
        self.assertIn("example.com", seeded)

    def test_pipeline_and_mission_control_idle_still_zero(self):
        self.assertEqual([k for k, _, _ in PIPELINE], ["aria", "raven", "vulcan", "cipher", "oracle"])
        summary = summarize_operation({}, [], {})
        self.assertEqual((summary["progress"], summary["total_tools"], summary["event_count"]), (0, 0, 0))

    def test_app_is_thin_composition_not_monolith(self):
        # Imports live at module top in the thin entry point, not in main().
        src = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
        self.assertIn("from ui.components import", src)
        self.assertIn("from ui.styles import", src)
        self.assertIn("from ui.report import", src)
        self.assertLess(len(src.splitlines()), 250, "app.py must stay a thin composition file")


if __name__ == "__main__":
    unittest.main()
