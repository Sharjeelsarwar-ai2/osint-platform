import json
import os

from groq import Groq

from config.settings import GROQ_API_KEY, MAX_TOKENS, MODEL_NAME, TEMPERATURE

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


def _emit(callback, event_type, payload):
    if callback:
        callback(event_type, payload)


def _content_text(message):
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text is None and isinstance(item, dict):
                text = item.get("text")
            if text:
                parts.append(str(text))
        return "\n".join(parts).strip()
    return ""


def _fallback_report(tool_results, reason, source_context=None):
    lines = [
        "# Preliminary findings — evidence fallback",
        "",
        "The model did not produce a complete synthesis. The sections below preserve available "
        "evidence without adding unsupported interpretation. Verify source data before acting.",
        "",
    ]
    if tool_results:
        lines.extend(["## Tool evidence", ""])
        for item in tool_results:
            args = json.dumps(item["args"], ensure_ascii=False, default=str)
            result = item["result"][:1500]
            lines.append(f"- **{item['name']}** with `{args}`: {result}")
    if source_context:
        context_text = str(source_context).strip()
        if len(context_text) > 12000:
            context_text = context_text[:12000] + "\n\n[Additional specialist context omitted for length.]"
        lines.extend([
            "",
            "## Findings supplied by completed specialists",
            "",
            context_text,
        ])
    if not tool_results and not source_context:
        lines.extend(["## Tool evidence", "", "No tool evidence was collected."])
    lines.extend([
        "",
        "## Limitation",
        "",
        f"Final language-model synthesis was unavailable: {reason}",
        "",
        "This is not a complete risk assessment; do not infer findings that are not shown above.",
    ])
    return "\n".join(lines)


def run_agent_with_tools(system_prompt, user_prompt, tools, tool_executor,
                         max_rounds=5, activity_callback=None, fallback_context=None):
    """Run bounded tool rounds, then always request a tool-free final synthesis."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    tool_results = []
    tool_names = {
        tool.get("function", {}).get("name")
        for tool in (tools or [])
        if isinstance(tool, dict)
    }
    tool_round_limit = max(1, int(max_rounds or 1))
    last_error = "the model returned no final answer"

    try:
        client = get_client()
    except Exception as exc:
        client = None
        last_error = f"client initialization failed ({type(exc).__name__}: {exc})"
        _emit(activity_callback, "error", last_error)

    for round_num in range(1, tool_round_limit + 1):
        if client is None:
            break
        _emit(activity_callback, "thinking", round_num)
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
            choices = getattr(response, "choices", None) or []
            if not choices:
                raise RuntimeError("The model returned no choices.")
            message = choices[0].message
        except Exception as exc:
            last_error = f"model request failed in tool round {round_num} ({type(exc).__name__}: {exc})"
            _emit(activity_callback, "error", last_error)
            break

        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            final_text = _content_text(message)
            if final_text:
                _emit(activity_callback, "final", final_text)
                return final_text
            last_error = f"the model returned an empty response in tool round {round_num}"
            _emit(activity_callback, "error", last_error)
            break

        # Preserve provider-specific assistant fields (e.g. GPT-OSS reasoning metadata)
        # rather than rebuilding a partial tool-call message.
        dump_message = getattr(message, "model_dump", None)
        if callable(dump_message):
            assistant_message = dump_message(exclude_none=True)
            assistant_message["role"] = "assistant"
        else:
            assistant_message = {
                "role": "assistant",
                "content": _content_text(message),
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        messages.append(assistant_message)

        for call in tool_calls:
            name = call.function.name
            raw_args = call.function.arguments
            try:
                args = json.loads(raw_args) if raw_args else {}
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be a JSON object.")
            except Exception as exc:
                args = {}
                result_str = f"Tool argument error: {type(exc).__name__}: {exc}"
            else:
                if name not in tool_names:
                    _emit(activity_callback, "tool_blocked", {
                        "name": name,
                        "message": f"Blocked {name}: this tool is not enabled for this agent.",
                    })
                    result_str = f"Tool '{name}' was not enabled for this agent and was not executed."
                else:
                    _emit(activity_callback, "tool_call", {"name": name, "args": args})
                    try:
                        result = tool_executor(name, args)
                        result_str = json.dumps(result, ensure_ascii=False, default=str)
                    except Exception as exc:
                        result_str = f"Tool execution error ({type(exc).__name__}): {exc}"

            tool_results.append({"name": name, "args": args, "result": result_str})
            _emit(activity_callback, "tool_result", {
                "name": name,
                "preview": result_str[:200],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": name,
                "content": result_str[:6000],
            })

    # Tool execution is finished. Ask for an explicit synthesis without exposing tools again.
    for attempt in range(1, 3):
        if client is None:
            break
        _emit(activity_callback, "finalizing", {"attempt": attempt, "tool_count": len(tool_results)})
        final_messages = messages + [{
            "role": "user",
            "content": (
                "Tool execution is now closed. Do not request or call any tools. "
                "Using only the evidence already present in this conversation, write the final "
                "complete answer requested by the original user prompt. Distinguish verified "
                "observations from uncertainty, cite the tool names and returned facts, and include "
                "a short limitations section. Do not say that more rounds are needed."
                if attempt == 1 else
                "Your previous finalization attempt was empty or unusable. Return a substantive, "
                "complete Markdown answer now, using only the evidence already present. Do not "
                "request tools, invent facts, or return an empty response."
            ),
        }]
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=final_messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            choices = getattr(response, "choices", None) or []
            if not choices:
                raise RuntimeError("The synthesis request returned no choices.")
            final_text = _content_text(choices[0].message)
            if getattr(choices[0].message, "tool_calls", None):
                last_error = "the model attempted a tool call during tool-free synthesis"
                _emit(activity_callback, "error", last_error)
                continue
            if final_text:
                _emit(activity_callback, "final", final_text)
                return final_text
            last_error = f"the model returned an empty synthesis on attempt {attempt}"
        except Exception as exc:
            last_error = f"final synthesis failed ({type(exc).__name__}: {exc})"
        _emit(activity_callback, "error", last_error)

    fallback = _fallback_report(tool_results, last_error, fallback_context)
    _emit(activity_callback, "fallback", {"reason": last_error, "tool_count": len(tool_results)})
    _emit(activity_callback, "final", fallback)
    return fallback
