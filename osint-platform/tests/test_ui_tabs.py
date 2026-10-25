"""Agent-tab report tests: one dedicated tab per agent, no mixed output."""
import unittest

from config.settings import AGENT_PROFILES
from ui.report import agent_tab_data


def _results():
    return {
        "aria": "ARIA-UNIQUE domain findings for example.com",
        "raven": "RAVEN-UNIQUE threat findings",
        "vulcan": "VULCAN-UNIQUE surface findings",
        "cipher": "CIPHER-UNIQUE email findings",
        "oracle": "ORACLE-UNIQUE executive report. Risk Score: 42/100",
    }


def _activity():
    activity = {}
    for key, tool in [("aria", "dns_lookup"), ("raven", "search_threat_intel"),
                      ("vulcan", "check_security_headers"), ("cipher", "check_email_security")]:
        activity[key] = {"status": "complete",
                         "activity_log": [{"type": "tool_call", "tool_name": tool,
                                           "text": f"Executing {tool}()"}]}
    activity["oracle"] = {"status": "complete", "activity_log": []}
    return activity


class TabDataTests(unittest.TestCase):
    def test_each_agent_row_contains_only_its_own_output(self):
        rows = agent_tab_data(_results(), _activity(), AGENT_PROFILES)
        self.assertEqual([r["key"] for r in rows], ["aria", "raven", "vulcan", "cipher", "oracle"])
        for row in rows:
            self.assertIn(f"{row['name']}-UNIQUE", row["content"])
            for other in rows:
                if other is not row:
                    self.assertNotIn(f"{other['name']}-UNIQUE", row["content"])
        self.assertEqual(rows[0]["tools"], ["dns_lookup"])
        self.assertEqual(rows[4]["tools"], [])
        self.assertEqual(rows[4]["status"], "complete")

    def test_overview_summary_does_not_duplicate_full_outputs(self):
        rows = agent_tab_data(_results(), _activity(), AGENT_PROFILES)
        # Snippets are short; full per-agent text lives in its tab only.
        for row in rows:
            self.assertLessEqual(len(row["snippet"]), 181)


class AppTestTabTests(unittest.TestCase):
    def test_report_renders_overview_plus_five_agent_tabs(self):
        from pathlib import Path

        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"))
        at.session_state["nexus_latest_activity"] = _activity()
        at.session_state["nexus_latest_report"] = {
            "target": "example.com",
            "target_type": "Domain",
            "timestamp": "2026-10-26T00:00:00+00:00",
            "elapsed": 12.5,
            "results": _results(),
        }
        at.run()
        self.assertFalse(at.exception, f"AppTest raised: {at.exception}")
        labels = [t.label for t in at.tabs]
        self.assertEqual(labels, ["Overview", "ARIA", "RAVEN", "VULCAN", "CIPHER", "ORACLE"])

        def tab_text(tab):
            parts = []
            for md in tab.markdown:
                parts.append(md.value)
            return "\n".join(parts)

        agent_tabs = at.tabs[1:]
        markers = ["ARIA-UNIQUE", "RAVEN-UNIQUE", "VULCAN-UNIQUE", "CIPHER-UNIQUE", "ORACLE-UNIQUE"]
        for tab, marker in zip(agent_tabs, markers):
            text = tab_text(tab)
            self.assertIn(marker, text, f"{marker} missing from its own tab")
            for other in markers:
                if other != marker:
                    self.assertNotIn(other, text, f"{other} leaked into {marker} tab")
        # Overview summarises without being an agent tab.
        self.assertIn("Per-agent summary", tab_text(at.tabs[0]))


if __name__ == "__main__":
    unittest.main()
