"""Mocked-Groq tests for the live ORACLE 413 (no real key needed).

The live error was: 413, "Request too large ... Limit 8000, Requested
9750" TPM for gpt-oss-120b — an untruncated ORACLE synthesis prompt
(all four specialists' findings) plus 4096 requested output tokens.
Covers: (a) a >9750-token ORACLE context is trimmed before sending so
prompt + output stays under the 7000-token budget, (b) a mocked 413 on
the first synthesis attempt triggers a SMALLER retry that succeeds,
(c) ORACLE context compression keeps late risk sections within cap,
(d) fallback outputs are flagged, never presented as real synthesis.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from config.settings import AGENT_PROFILES
from ui.report import agent_tab_data, is_fallback_content
from utils import groq_client


class SizeError(Exception):
    """Mimics Groq APIStatusError for a 413 TPM size error."""

    def __init__(self):
        super().__init__(
            "Error code: 413 - {'error': {'message': 'Request too large for model "
            "openai/gpt-oss-120b in organization org_example service tier on_demand "
            "on tokens per minute (TPM): Limit 8000, Requested 9750, please reduce "
            "your message size and try again.', 'type': 'tokens', "
            "'code': 'rate_limit_exceeded'}}")
        self.status_code = 413


def resp(content):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content, tool_calls=[]))])


class Scripted:
    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def run(script, user_prompt, tools=None):
    client = SimpleNamespace(chat=SimpleNamespace(completions=Scripted(script)))
    events = []
    with patch.object(groq_client, "get_client", return_value=client):
        result = groq_client.run_agent_with_tools(
            "system", user_prompt, tools if tools is not None else [],
            lambda name, args: {}, max_rounds=1,
            activity_callback=lambda *e: events.append(e),
        )
    return result, client.chat.completions, events


class BudgetTests(unittest.TestCase):
    def test_large_oracle_context_is_trimmed_under_budget(self):
        # 4 specialists x 12000 chars ~= 12000 estimated tokens, well
        # over the live 9750-token request that Groq rejected.
        finding = ("# Executive Summary\nReal summary. " + "evidence " * 2500)
        user_prompt = "Target: example.com\n\n" + "\n\n".join(
            f"### AGENT {i} FINDINGS\n{finding}" for i in range(4))
        self.assertGreater(groq_client.estimate_tokens(user_prompt), 9750)
        result, completions, _events = run(
            [resp("REAL-SYNTHESIS")], user_prompt)
        self.assertEqual(result, "REAL-SYNTHESIS")
        request = completions.requests[0]
        total = groq_client._messages_tokens(request["messages"]) + request["max_tokens"]
        self.assertLessEqual(total, groq_client.REQUEST_TOKEN_BUDGET)

    def test_413_synthesis_retries_with_smaller_payload_and_succeeds(self):
        # Round 1 returns empty -> synthesis loop. Attempt 1 raises 413,
        # attempt 2 (smaller prompt, fewer output tokens) succeeds.
        large = "Specialist evidence. " * 3000  # ~15000 chars
        result, completions, events = run(
            [resp(""), SizeError(), resp("REAL-SYNTHESIS-AFTER-413")],
            f"Target: example.com\n\n{large}")
        self.assertEqual(result, "REAL-SYNTHESIS-AFTER-413")
        # Requests: [round 1, synthesis attempt 1 (413), synthesis attempt 2]
        self.assertEqual(len(completions.requests), 3)
        first = completions.requests[1]
        second = completions.requests[2]
        self.assertLess(groq_client._messages_tokens(second["messages"]),
                        groq_client._messages_tokens(first["messages"]))
        self.assertLess(second["max_tokens"], first["max_tokens"])
        event_text = " ".join(str(e) for e in events)
        self.assertIn("request too large", event_text.lower())

    def test_size_error_detection(self):
        self.assertTrue(groq_client._is_size_error(SizeError()))
        self.assertFalse(groq_client._is_size_error(ValueError("boom")))


class CompressionTests(unittest.TestCase):
    def test_compression_keeps_late_risk_section_within_cap(self):
        from agents.orchestrator import _compress_specialist_finding

        finding = (
            "# Executive Summary\nEXEC-SUMMARY-MARKER short summary.\n\n"
            "# Findings\n" + "filler evidence. " * 2000 + "\n\n"
            "# Risk Assessment\nRISK-MARKER-42 critical exposure.\n\n"
            "# Recommendations\nFix the exposure promptly.\n")
        compressed = _compress_specialist_finding(finding)
        self.assertLessEqual(len(compressed), 2600)
        self.assertIn("EXEC-SUMMARY-MARKER", compressed)
        self.assertIn("RISK-MARKER-42", compressed)
        self.assertNotIn("filler evidence. " * 100, compressed)


class FallbackLabellingTests(unittest.TestCase):
    def test_fallback_is_flagged_and_real_synthesis_is_not(self):
        fallback = ("# Preliminary findings — evidence fallback\n\n"
                    "Final language-model synthesis was unavailable: final synthesis "
                    "failed (APIStatusError: Error code: 413 ...)")
        self.assertTrue(is_fallback_content(fallback))
        self.assertFalse(is_fallback_content("ORACLE-UNIQUE report. Risk Score: 42/100"))
        rows = agent_tab_data(
            {"aria": "a", "raven": "r", "vulcan": "v", "cipher": "c", "oracle": fallback},
            {"oracle": {"status": "fallback", "activity_log": []}},
            AGENT_PROFILES)
        oracle_row = next(r for r in rows if r["key"] == "oracle")
        self.assertTrue(oracle_row["is_fallback"])

    def test_fallback_report_shows_banner_not_fake_risk(self):
        from pathlib import Path

        from streamlit.testing.v1 import AppTest

        fallback = ("# Preliminary findings — evidence fallback\n\n"
                    "Final language-model synthesis was unavailable: final synthesis "
                    "failed (APIStatusError: Error code: 413 ...)")
        results = {"aria": "ARIA-UNIQUE", "raven": "RAVEN-UNIQUE", "vulcan": "VULCAN-UNIQUE",
                   "cipher": "CIPHER-UNIQUE", "oracle": fallback}
        at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"))
        at.session_state["nexus_latest_activity"] = {
            k: {"status": "complete", "activity_log": []} for k in results}
        at.session_state["nexus_latest_report"] = {
            "target": "example.com", "target_type": "Domain",
            "timestamp": "2026-10-26T00:00:00+00:00", "elapsed": 12.5,
            "results": results}
        at.run()
        self.assertFalse(at.exception, f"AppTest raised: {at.exception}")
        self.assertEqual([t.label for t in at.tabs],
                         ["Overview", "ARIA", "RAVEN", "VULCAN", "CIPHER", "ORACLE"])

        def tab_text(tab):
            parts = [md.value for md in tab.markdown]
            parts += [w.value for w in getattr(tab, "warning", [])]
            return "\n".join(parts)

        self.assertIn("FALLBACK — NOT A REAL SYNTHESIS", tab_text(at.tabs[0]))
        self.assertIn("FALLBACK — NOT A REAL SYNTHESIS", tab_text(at.tabs[5]))


if __name__ == "__main__":
    unittest.main()
