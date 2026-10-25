"""Mocked-Groq tests for the round-2 parsing failure (no real key needed).

Covers: (a) malformed tool arguments repaired, (b) a 400 parsing
BadRequest on round 2 followed by a successful retry, (c) a malformed
assistant message with extra reasoning fields cleaned before resend,
(d) final synthesis still working after a tool-round error, plus
dropped-call and tool-result truncation behaviour.
"""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from utils import groq_client


class FakeMessage:
    def __init__(self, content=None, tool_calls=None, reasoning=None, extra=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.reasoning = reasoning
        self.extra = extra or {}

    def model_dump(self, exclude_none=True):
        data = {"role": "assistant", "content": self.content, "reasoning": self.reasoning,
                "reasoning_content": "secret chain", "id": "chatcmpl-xyz",
                "tool_calls": [{"id": c.id, "type": "function",
                                "function": {"name": c.function.name, "arguments": c.function.arguments}}
                               for c in self.tool_calls]}
        data.update(self.extra)
        return {k: v for k, v in data.items() if v is not None} if exclude_none else data


def call(call_id, name, args_raw):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=args_raw))


def resp(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class ParseError(Exception):
    """Mimics Groq BadRequestError for a 400 parsing failure."""
    def __init__(self):
        super().__init__("Error code: 400 - {'error': {'message': 'Parsing failed. "
                         "The model generated output that could not be parsed. "
                         "Please adjust your prompt.', 'type': 'invalid_request_error'}}")
        self.status_code = 400


class ScriptedCompletions:
    """Replies/exceptions in order; records every request for inspection."""
    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        for message in kwargs["messages"]:
            if message.get("role") == "tool":
                assert message.get("name") and message.get("tool_call_id")
                assert isinstance(message.get("content"), str)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def run(script, tools=None, executor=None, max_rounds=3):
    client = SimpleNamespace(chat=SimpleNamespace(completions=ScriptedCompletions(script)))
    events = []
    with patch.object(groq_client, "get_client", return_value=client):
        result = groq_client.run_agent_with_tools(
            "system", "research example.com",
            tools if tools is not None else [{"type": "function", "function": {"name": "dns_lookup"}}],
            executor or (lambda name, args: {"A": ["203.0.113.8"]}),
            max_rounds=max_rounds,
            activity_callback=lambda *e: events.append(e),
        )
    return result, client.chat.completions, events


class ParsingTests(unittest.TestCase):
    def test_malformed_arguments_repaired(self):
        cases = [
            ('```json\n{"domain": "example.com",}\n```', {"domain": "example.com"}),
            ("Here is the call: {\"domain\": \"example.com\"} thanks", {"domain": "example.com"}),
            ("{'domain': 'example.com'}", {"domain": "example.com"}),
        ]
        for raw, expected in cases:
            seen = []
            result, _, _ = run([
                resp(FakeMessage(tool_calls=[call("c1", "dns_lookup", raw)])),
                resp(FakeMessage(content="## Done\n\nChecked.")),
            ], executor=lambda n, a: seen.append(a) or {"ok": True})
            self.assertIn("## Done", result)
            self.assertEqual(seen[0], expected)

    def test_unparsable_arguments_dropped_not_echoed(self):
        seen = []
        result, completions, _ = run([
            resp(FakeMessage(tool_calls=[call("bad-1", "dns_lookup", '{"domain": "exam') ])),
            resp(FakeMessage(content="## Done without tools")),
        ], executor=lambda n, a: seen.append(a))
        self.assertIn("## Done without tools", result)
        self.assertEqual(seen, [])
        # No tool message may ever carry the dropped call id.
        for req in completions.requests:
            for msg in req["messages"]:
                self.assertNotEqual(msg.get("tool_call_id"), "bad-1")

    def test_parse_error_round2_then_successful_retry(self):
        result, completions, events = run([
            resp(FakeMessage(tool_calls=[call("c1", "dns_lookup", '{"domain": "example.com"}')])),
            ParseError(),
            resp(FakeMessage(content="## Recovered\n\nDNS is 203.0.113.8.")),
        ], max_rounds=3)
        self.assertIn("## Recovered", result)
        self.assertNotIn("Preliminary findings", result)
        self.assertTrue(any(e[0] == "error" and "retrying once" in str(e[1]) for e in events))
        # Retry request carries the clean-continuation nudge.
        self.assertTrue(any("could not be parsed" in str(m.get("content", ""))
                            for req in completions.requests for m in req["messages"]))

    def test_extra_assistant_fields_cleaned_before_resend(self):
        result, completions, _ = run([
            resp(FakeMessage(tool_calls=[call("c1", "dns_lookup", '{"domain": "example.com"}')],
                             reasoning="chain", extra={"reasoning_content": "x"})),
            resp(FakeMessage(content="## Clean\n\nDone.")),
        ], max_rounds=2)
        self.assertIn("## Clean", result)
        # The second request's assistant message must be clean-only.
        assistant = next(m for m in completions.requests[1]["messages"] if m.get("role") == "assistant")
        self.assertEqual(set(assistant.keys()), {"role", "content", "tool_calls"})
        self.assertNotIn("reasoning", assistant)
        # Tool definitions must also be schema-clean.
        for req in completions.requests:
            for tool in req.get("tools", []):
                self.assertEqual(set(tool["function"].keys()), {"name", "description", "parameters"})

    def test_final_synthesis_after_failed_parse_retry(self):
        result, _, events = run([
            resp(FakeMessage(tool_calls=[call("c1", "dns_lookup", '{"domain": "example.com"}')])),
            ParseError(),
            ParseError(),  # retry also fails -> fall through to synthesis
            resp(FakeMessage(content="## Synthesis\n\nEvidence-based summary.")),
        ], max_rounds=3)
        self.assertIn("## Synthesis", result)
        self.assertNotIn("Preliminary findings", result)

    def test_tool_results_are_plain_truncated_strings(self):
        result, completions, _ = run([
            resp(FakeMessage(tool_calls=[call("c1", "dns_lookup", '{"domain": "example.com"}')])),
            resp(FakeMessage(content="## Done")),
        ], executor=lambda n, a: {"big": "x" * 20000})
        tool_msg = next(m for req in completions.requests for m in req["messages"]
                        if m.get("role") == "tool")
        self.assertIsInstance(tool_msg["content"], str)
        self.assertLessEqual(len(tool_msg["content"]), 6000)


if __name__ == "__main__":
    unittest.main()
