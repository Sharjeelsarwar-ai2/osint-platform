"""UI / activity-presentation tests (presentation layer only).

These tests pin the architecture that must NOT change, and prove the
new mission-control view is driven by real activity data — never by
simulated events.
"""
import unittest

from agents.orchestrator import (
    PIPELINE,
    render_agent_workstation,
    render_global_feed_html,
    summarize_operation,
)
from agents.tools import TOOL_REGISTRY
from utils.pdf_generator import SECTION_AGENT_KEYS, generate_pdf


class ArchitecturePreservedTests(unittest.TestCase):
    def test_pipeline_order_and_agents_unchanged(self):
        self.assertEqual(
            [key for key, _, _ in PIPELINE],
            ["aria", "raven", "vulcan", "cipher", "oracle"],
        )

    def test_tool_registry_unchanged(self):
        self.assertEqual(len(TOOL_REGISTRY), 12)
        self.assertIn("dns_lookup", TOOL_REGISTRY)
        self.assertIn("check_email_security", TOOL_REGISTRY)


class MissionControlTests(unittest.TestCase):
    def test_summarize_operation_counts_real_data_only(self):
        activity = {
            "aria": {"status": "complete", "activity_log": []},
            "raven": {"status": "executing", "activity_log": []},
            "vulcan": {"status": "queued", "activity_log": []},
            "cipher": {"status": "queued", "activity_log": []},
            "oracle": {"status": "queued", "activity_log": []},
        }
        operation = {
            "target": "example.com",
            "status": "running",
            "current_agent": "raven",
            "tool_counts": {"aria": 3, "raven": 1},
        }
        summary = summarize_operation(activity, [{"agent": "aria"}], operation)
        self.assertEqual(summary["progress"], 20)  # 1 of 5 finished
        self.assertEqual(summary["total_tools"], 4)
        self.assertEqual(summary["event_count"], 1)
        self.assertEqual(summary["current_agent"], "raven")
        self.assertEqual(summary["succeeded"], ["aria"])

    def test_global_feed_renders_real_events(self):
        events = [{
            "agent": "aria", "time": "12:00:01", "type": "tool_call",
            "text": "Executing dns_lookup(domain=example.com)",
        }]
        html_out = render_global_feed_html(events)
        self.assertIn("ARIA", html_out)
        self.assertIn("dns_lookup", html_out)
        self.assertIn("EXEC", html_out)

    def test_empty_feed_is_honest_not_simulated(self):
        html_out = render_global_feed_html([])
        self.assertIn("No live operation yet", html_out)
        self.assertIn("Nothing here is simulated", html_out)
        self.assertNotIn("ARIA", html_out)

    def test_agent_workstation_renders_status_and_events(self):
        html_out = render_agent_workstation(
            "aria", "executing",
            [{"time": "12:00:01", "type": "tool_call", "text": "Executing dns_lookup()", "tool_name": "dns_lookup"}],
            elapsed=2.5,
        )
        self.assertIn("status-executing", html_out)
        self.assertIn("RUNNING TOOL", html_out)
        self.assertIn("dns_lookup", html_out)
        self.assertIn("2.5s", html_out)


class PdfMappingFixTests(unittest.TestCase):
    def test_pdf_uses_real_agent_keys_not_legacy_keys(self):
        self.assertEqual(
            [key for _, key in SECTION_AGENT_KEYS],
            ["oracle", "aria", "raven", "vulcan", "cipher"],
        )
        real_results = {
            "aria": "ARIA domain findings for example.com",
            "raven": "RAVEN threat findings",
            "vulcan": "VULCAN surface findings",
            "cipher": "CIPHER email findings",
            "oracle": "ORACLE executive report",
        }
        with_sections = generate_pdf(real_results)
        blank = generate_pdf({})
        self.assertTrue(with_sections.startswith(b"%PDF"))
        # Real sections must actually add content vs. the old blank export.
        self.assertGreater(len(with_sections), len(blank) + 500)


if __name__ == "__main__":
    unittest.main()
