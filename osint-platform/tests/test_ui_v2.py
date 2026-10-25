"""V2 radical redesign tests (presentation only).

Pins the new, unmistakably different look while proving architecture
and real-activity wiring are unchanged. No simulated activity is used.
"""
import unittest

from agents.orchestrator import PIPELINE, render_mission_control, summarize_operation
from config.settings import AGENT_PROFILES


class V2PaletteTests(unittest.TestCase):
    def test_new_palette_is_not_the_old_cyan_blue_scheme(self):
        from app import get_css
        css = get_css().lower()
        # New dominant scheme: magenta / violet / lime / amber on violet-black.
        self.assertIn("#ff2e88", css)
        self.assertIn("#c6ff3d", css)
        self.assertIn("#8b5cf6", css)
        self.assertIn("#ffb020", css)
        self.assertIn("#0b0514", css)
        self.assertIn("nx-hero-v2", css)
        self.assertIn("nx-orb", css)
        self.assertIn("orb-drift", css)
        # Old hero headline must be gone.
        from app import render_header  # noqa: F401  (import proves module loads)
        import inspect
        src = inspect.getsource(render_header)
        self.assertIn("Track the invisible", src)
        self.assertIn("Expose the truth", src)
        self.assertNotIn("Know the", src)

    def test_agent_accents_are_the_new_set(self):
        self.assertEqual(
            {k: v["color"] for k, v in AGENT_PROFILES.items()},
            {
                "aria": "#FF2E88",
                "raven": "#A78BFA",
                "vulcan": "#FFB020",
                "cipher": "#C6FF3D",
                "oracle": "#E879F9",
            },
        )

    def test_pipeline_unchanged(self):
        self.assertEqual(
            [key for key, _, _ in PIPELINE],
            ["aria", "raven", "vulcan", "cipher", "oracle"],
        )


class V2BoardTests(unittest.TestCase):
    def test_live_board_function_exists_and_is_honest_on_idle(self):
        from app import render_live_team_board, render_idle_state
        import inspect
        board_src = inspect.getsource(render_live_team_board)
        self.assertIn("STANDBY", board_src)
        self.assertIn("nexus_latest_activity", board_src)
        self.assertIn("nexus_operation", board_src)
        idle_src = inspect.getsource(render_idle_state)
        self.assertIn("TEAM ON STANDBY", idle_src)
        self.assertIn("nothing is simulated", idle_src.lower())

    def test_mission_control_idle_summary_is_zero_not_faked(self):
        summary = summarize_operation({}, [], {})
        self.assertEqual(summary["progress"], 0)
        self.assertEqual(summary["total_tools"], 0)
        self.assertEqual(summary["event_count"], 0)
        self.assertEqual(summary["statuses"]["aria"], "queued")


if __name__ == "__main__":
    unittest.main()
