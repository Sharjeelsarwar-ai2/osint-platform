import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from utils import groq_client


class FakeMessage:
    def __init__(self, content=None, tool_calls=None, reasoning=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.reasoning = reasoning

    def model_dump(self, exclude_none=True):
        data = {
            "role": "assistant",
            "content": self.content,
            "reasoning": self.reasoning,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls
            ],
        }
        return {key: value for key, value in data.items() if value is not None} if exclude_none else data


def tool_call(name="dns_lookup", args=None):
    args = args or {"domain": "example.com"}
    return SimpleNamespace(
        id="call-123",
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        # Groq's documented local-tool flow needs a named tool result for
        # every tool_call_id before the next assistant completion.
        for message in kwargs["messages"]:
            if message.get("role") == "tool":
                assert message.get("name"), "tool result must include its function name"
                assert message.get("tool_call_id"), "tool result must match its function-call id"
        return self.replies.pop(0)


class GroqToolTranscriptTests(unittest.TestCase):
    def test_tool_exhaustion_sends_named_result_and_clean_assistant_message(self):
        first = response(FakeMessage(
            tool_calls=[tool_call()],
            reasoning="Use DNS evidence to answer.",
        ))
        final = response(FakeMessage(
            content="## Findings\n\nThe DNS check returned an A record.\n\n## Limitations\n\nPassive lookup only."
        ))
        client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions([first, final])))
        events = []

        with patch.object(groq_client, "get_client", return_value=client):
            result = groq_client.run_agent_with_tools(
                "system prompt",
                "research example.com",
                [{"type": "function", "function": {"name": "dns_lookup"}}],
                lambda name, args: {"A": ["203.0.113.8"]},
                max_rounds=1,
                activity_callback=lambda *event: events.append(event),
            )

        self.assertIn("## Findings", result)
        self.assertEqual(len(client.chat.completions.requests), 2)
        final_request = client.chat.completions.requests[1]
        self.assertNotIn("tools", final_request)
        transcript = final_request["messages"]
        assistant_message = next(message for message in transcript if message.get("role") == "assistant")
        tool_message = next(message for message in transcript if message.get("role") == "tool")
        # Regression: provider reasoning/metadata must NOT be echoed back —
        # that is what Groq rejected on the next round (400 parsing failure).
        self.assertNotIn("reasoning", assistant_message)
        self.assertEqual(set(assistant_message.keys()), {"role", "content", "tool_calls"})
        self.assertEqual(tool_message.get("name"), "dns_lookup")
        self.assertEqual(tool_message.get("tool_call_id"), "call-123")
        self.assertIn("203.0.113.8", tool_message.get("content", ""))
        self.assertTrue(any(event[0] == "final" for event in events))

    def test_empty_responses_return_explicit_fallback_instead_of_round_limit_message(self):
        empty = response(FakeMessage())
        client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions([empty, empty, empty])))

        with patch.object(groq_client, "get_client", return_value=client):
            result = groq_client.run_agent_with_tools(
                "system prompt", "research", [], lambda *_: None, max_rounds=1
            )

        self.assertIn("Preliminary findings — evidence fallback", result)
        self.assertIn("No tool evidence was collected", result)
        self.assertNotIn("Max rounds reached without final answer", result)

    def test_oracle_fallback_includes_findings_from_completed_specialists(self):
        empty = response(FakeMessage())
        client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions([empty, empty, empty])))
        upstream = "### ARIA FINDINGS\nDNS returned 203.0.113.8.\n\n### CIPHER FINDINGS\nSPF record observed."

        with patch.object(groq_client, "get_client", return_value=client):
            result = groq_client.run_agent_with_tools(
                "synthesis agent", "combine specialist findings", [], lambda *_: None,
                max_rounds=1, fallback_context=upstream,
            )

        self.assertIn("Findings supplied by completed specialists", result)
        self.assertIn("DNS returned 203.0.113.8", result)
        self.assertIn("SPF record observed", result)
        self.assertNotIn("No tool evidence was collected", result)

    def test_undeclared_tool_is_blocked_not_executed(self):
        first = response(FakeMessage(tool_calls=[tool_call("shell_exec", {"cmd": "echo unsafe"})]))
        final = response(FakeMessage(content="No tool was executed."))
        client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions([first, final])))
        executed = []
        events = []

        with patch.object(groq_client, "get_client", return_value=client):
            groq_client.run_agent_with_tools(
                "system prompt",
                "research",
                [{"type": "function", "function": {"name": "dns_lookup"}}],
                lambda *args: executed.append(args),
                max_rounds=1,
                activity_callback=lambda *event: events.append(event),
            )

        self.assertEqual(executed, [])
        self.assertTrue(any(event[0] == "tool_blocked" for event in events))
        self.assertFalse(any(event[0] == "tool_call" for event in events))


if __name__ == "__main__":
    unittest.main()
