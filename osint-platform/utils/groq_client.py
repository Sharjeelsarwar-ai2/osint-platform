import os
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME, MAX_TOKENS, TEMPERATURE

_client = None

def get_client():
    global _client
    if _client is None:
        key = GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
        if not key:
            try:
                import streamlit as st
                key = st.secrets.get("GROQ_API_KEY", "")
            except Exception:
                pass
        _client = Groq(api_key=key)
    return _client


def run_agent_with_tools(system_prompt, user_prompt, tools, tool_executor,
                         max_rounds=5, activity_callback=None):
    """
    Groq tool-calling loop.
    activity_callback(event_type, payload) is called for every live event:
        - ('thinking', round_num)
        - ('tool_call', {'name':..., 'args':...})
        - ('tool_result', {'name':..., 'preview':...})
        - ('final', text)
    """
    client = get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    for round_num in range(1, max_rounds + 1):
        if activity_callback:
            activity_callback("thinking", round_num)

        # Build kwargs — only add tool params if tools exist
        kwargs = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as e:
            err = f"❌ LLM API Error (round {round_num}): {e}"
            if activity_callback:
                activity_callback("error", err)
            return err

        msg = response.choices[0].message

        # Final text answer (no tool calls)
        if not getattr(msg, "tool_calls", None):
            final = msg.content or "_(no content returned)_"
            if activity_callback:
                activity_callback("final", final)
            return final

        # Append assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                } for tc in msg.tool_calls
            ],
        })

        # Execute each tool
        for tc in msg.tool_calls:
            import json
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except Exception:
                args = {}

            if activity_callback:
                activity_callback("tool_call", {
                    "name": tc.function.name,
                    "args": args,
                })

            try:
                result = tool_executor(tc.function.name, args)
                result_str = str(result)[:3000]
            except Exception as e:
                result_str = f"Tool error: {e}"

            if activity_callback:
                activity_callback("tool_result", {
                    "name": tc.function.name,
                    "preview": result_str[:200],
                })

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })

    return "_(Max rounds reached without final answer)_"
