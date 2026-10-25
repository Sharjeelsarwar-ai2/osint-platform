"""Groq client — hardened against the round-2 parsing failure.

Root cause (see tests/test_groq_parsing.py):
  1. The old code echoed the provider's assistant message back verbatim via
     ``model_dump(exclude_none=True)``. For GPT-OSS that message can carry
     reasoning / provider metadata that Groq's own parser then rejects on
     the NEXT round ("Parsing failed. The model generated output that
     could not be parsed", HTTP 400). Every message sent back is now
     rebuilt from scratch: assistant messages contain ONLY role, content
     (string or null) and tool_calls (id/type/function name/arguments as
     a validated JSON string); tool messages contain ONLY role,
     tool_call_id, name and a plain-string content.
  2. Malformed tool-call arguments were echoed back unchanged. Arguments
     are now repaired (fences / wrapped text / trailing commas / Python
     literals) or the call is DROPPED — never echoed malformed, and never
     given a tool result for a call id that was not sent back.
  3. Any exception in a tool round used to break the whole agent. A 400
     parsing failure now retries that round ONCE with a clean, low-
     temperature continuation, and the retry is emitted as an activity
     event so the UI shows recovery instead of a silent break.

Tool results are always plain strings, truncated to 6000 chars.
Retries are bounded: at most 1 parsing retry per tool round, plus the
existing round limit and the 2 final-synthesis attempts.
"""
import ast
import json
import os
import re

from groq import Groq

from config.settings import GROQ_API_KEY, MAX_TOKENS, MODEL_NAME, TEMPERATURE

_client = None
MAX_TOOL_RESULT_CHARS = 6000
_PARSE_RETRY_NUDGE = (
    "Your last reply could not be parsed. Reply again with EITHER one "
    "single valid JSON tool call OR plain text only. Do not include "
    "reasoning, markdown fences, commentary, or extra fields."
)


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


def _is_parse_error(exc):
    """True for Groq 400 parsing failures (BadRequestError and friends)."""
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if value == 400:
            return True
    text = str(exc).lower()
    if "badrequest" in type(exc).__name__.lower():
        return True
    return "400" in text and ("pars" in text or "invalid_request" in text)


def _extract_json_object(text):
    """Return the first balanced {...} substring, respecting strings."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return None


def _try_parse_json_object(text):
    try:
        value = json.loads(text)
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _clean_tool_arguments(raw):
    """Return (args_dict, error_or_None, was_repaired).

    Accepts a dict, a clean JSON string, a fenced/wrapped JSON string, a
    trailing-comma JSON string, or a Python-literal dict string. Anything
    else (truncated JSON, non-object JSON) is an error — callers must drop
    that call rather than echo it back to the provider.
    """
    if raw is None or raw == "":
        return {}, None, False
    if isinstance(raw, dict):
        try:
            json.dumps(raw)
        except Exception as exc:
            return None, f"arguments are not JSON-serializable: {exc}", False
        return raw, None, False
    if not isinstance(raw, str):
        return None, f"arguments must be a JSON object string, got {type(raw).__name__}", False
    text = raw.strip()
    # Strip markdown fences: ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = _try_parse_json_object(text)
    if parsed is not None:
        return parsed, None, text != raw.strip()
    candidate = _extract_json_object(text)
    if candidate is not None and candidate != text:
        parsed = _try_parse_json_object(candidate)
        if parsed is not None:
            return parsed, None, True
    # Trailing commas: {"a": 1,} -> {"a": 1}
    repaired = re.sub(r",(\s*[}\]])", r"\1", candidate or text)
    parsed = _try_parse_json_object(repaired)
    if parsed is not None:
        return parsed, None, True
    # Python-literal dicts: {'domain': 'example.com'}
    try:
        value = ast.literal_eval(candidate or text)
    except Exception:
        value = None
    if isinstance(value, dict):
        return value, None, True
    return None, "arguments are not a valid JSON object (unparsable/truncated)", False


def _clean_tool_call(call):
    """Return (cleaned_call_dict, args_dict, error_or_None) for one call."""
    call_id = getattr(call, "id", None)
    function = getattr(call, "function", None)
    name = getattr(function, "name", None) if function is not None else None
    raw_args = getattr(function, "arguments", None) if function is not None else None
    if not call_id or not name:
        return None, None, "tool call is missing id or function name"
    args, error, _repaired = _clean_tool_arguments(raw_args)
    if error is not None:
        return None, None, error
    cleaned = {
        "id": str(call_id),
        "type": "function",
        "function": {"name": str(name), "arguments": json.dumps(args, ensure_ascii=False)},
    }
    return cleaned, args, None


def _clean_tool_definitions(tools):
    """Rebuild tool definitions with only provider-safe schema keys."""
    cleaned = []
    for tool in tools or []:
        if not isinstance(tool, dict):
            continue
        function = tool.get("function", {}) or {}
        name = function.get("name")
        if not name:
            continue
        params = function.get("parameters", {}) or {}
        properties = {}
        for key, spec in (params.get("properties", {}) or {}).items():
            if not isinstance(spec, dict):
                continue
            properties[key] = {k: spec[k] for k in ("type", "description", "default", "enum") if k in spec}
        cleaned.append({
            "type": "function",
            "function": {
                "name": name,
                "description": function.get("description", ""),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": list(params.get("required", []) or []),
                },
            },
        })
    return cleaned


def _result_text(result):
    if isinstance(result, str):
        text = result
    else:
        try:
            text = json.dumps(result, ensure_ascii=False, default=str)
        except Exception:
            text = str(result)
    return text.replace("\x00", "")[:MAX_TOOL_RESULT_CHARS]


def _clean_message(message):
    """Rebuild one history message with only provider-safe fields."""
    if not isinstance(message, dict):
        return {"role": "user", "content": str(message)}
    role = message.get("role")
    if role == "tool":
        return {
            "role": "tool",
            "tool_call_id": str(message.get("tool_call_id", "")),
            "name": str(message.get("name", "")),
            "content": str(message.get("content", ""))[:MAX_TOOL_RESULT_CHARS],
        }
    if role == "assistant":
        content = message.get("content")
        if isinstance(content, list):
            content = "\n".join(str(p) for p in content)
        cleaned_calls = []
        seen = set()
        for call in message.get("tool_calls", []) or []:
            if not isinstance(call, dict):
                continue
            function = call.get("function", {}) or {}
            call_id = str(call.get("id", ""))
            name = function.get("name")
            if not call_id or not name or call_id in seen:
                continue
            args, error, _r = _clean_tool_arguments(function.get("arguments", ""))
            if error is not None:
                continue
            seen.add(call_id)
            cleaned_calls.append({
                "id": call_id,
                "type": "function",
                "function": {"name": str(name), "arguments": json.dumps(args, ensure_ascii=False)},
            })
        out = {"role": "assistant", "content": content if content else None}
        if cleaned_calls:
            out["tool_calls"] = cleaned_calls
        return out
    return {"role": role, "content": str(message.get("content", ""))}


def _clean_messages(messages):
    return [_clean_message(m) for m in (messages or [])]


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
    clean_tools = _clean_tool_definitions(tools)
    tool_results = []
    tool_names = {
        tool.get("function", {}).get("name")
        for tool in clean_tools
    }
    tool_round_limit = max(1, int(max_rounds or 1))
    last_error = "the model returned no final answer"

    try:
        client = get_client()
    except Exception as exc:
        client = None
        last_error = f"client initialization failed ({type(exc).__name__}: {exc})"
        _emit(activity_callback, "error", last_error)

    broke_on_error = False
    for round_num in range(1, tool_round_limit + 1):
        if client is None:
            break
        _emit(activity_callback, "thinking", round_num)
        parse_retried = False
        message = None
        while True:
            kwargs = {
                "model": MODEL_NAME,
                "messages": _clean_messages(messages),
                "temperature": 0.0 if parse_retried else TEMPERATURE,
                "max_tokens": MAX_TOKENS,
            }
            if clean_tools:
                kwargs["tools"] = clean_tools
                kwargs["tool_choice"] = "auto"
            try:
                response = client.chat.completions.create(**kwargs)
                choices = getattr(response, "choices", None) or []
                if not choices:
                    raise RuntimeError("The model returned no choices.")
                message = choices[0].message
                break
            except Exception as exc:
                if _is_parse_error(exc) and not parse_retried:
                    parse_retried = True
                    _emit(activity_callback, "error",
                          f"Parsing failed in tool round {round_num} — retrying once with a clean continuation.")
                    messages.append({"role": "user", "content": _PARSE_RETRY_NUDGE})
                    continue
                last_error = f"model request failed in tool round {round_num} ({type(exc).__name__}: {exc})"
                _emit(activity_callback, "error", last_error)
                broke_on_error = True
                break
        if broke_on_error:
            break
        if message is None:
            break

        raw_tool_calls = getattr(message, "tool_calls", None) or []
        if not raw_tool_calls:
            final_text = _content_text(message)
            if final_text:
                _emit(activity_callback, "final", final_text)
                return final_text
            last_error = f"the model returned an empty response in tool round {round_num}"
            _emit(activity_callback, "error", last_error)
            break

        # Rebuild the assistant message from scratch (never model_dump):
        # only role/content/tool_calls, with validated JSON arguments.
        valid_calls = []  # (cleaned_call_dict, name, args)
        dropped = []
        seen_ids = set()
        for call in raw_tool_calls:
            cleaned, args, error = _clean_tool_call(call)
            if error is not None:
                dropped.append(error)
                _emit(activity_callback, "error", f"Tool call dropped in round {round_num}: {error}")
                continue
            if cleaned["id"] in seen_ids:
                continue
            seen_ids.add(cleaned["id"])
            valid_calls.append((cleaned, cleaned["function"]["name"], args))
        if not valid_calls:
            # Nothing safe to echo back: do NOT send a tool result for a
            # dropped call id. Ask the model to re-issue clean JSON.
            _emit(activity_callback, "error",
                  f"All tool calls in round {round_num} had unparsable arguments and were dropped; asking for a clean re-issue.")
            messages.append({"role": "user", "content": _PARSE_RETRY_NUDGE})
            continue
        text = _content_text(message)
        assistant_message = {"role": "assistant", "content": text if text else None,
                             "tool_calls": [c for c, _n, _a in valid_calls]}
        messages.append(assistant_message)

        for cleaned, name, args in valid_calls:
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
                    result_str = _result_text(result)
                except Exception as exc:
                    result_str = f"Tool execution error ({type(exc).__name__}): {exc}"
            tool_results.append({"name": name, "args": args, "result": result_str})
            _emit(activity_callback, "tool_result", {
                "name": name,
                "preview": result_str[:200],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": cleaned["id"],
                "name": name,
                "content": result_str,
            })

    # Tool execution is finished. Ask for an explicit synthesis without exposing tools again.
    for attempt in range(1, 3):
        if client is None:
            break
        _emit(activity_callback, "finalizing", {"attempt": attempt, "tool_count": len(tool_results)})
        final_messages = _clean_messages(messages) + [{
            "role": "user",
            "content": (
                "Tool execution is now closed. Do not request or call any tools. "
                "Using only the evidence already present in this conversation, write the final "
                "complete answer requested by the original user prompt. Distinguish verified "
                "observations from uncertainty, cite the tool names and returned facts, and include "
                "a short limitations section. Do not say that more rounds are needed."
                if attempt == 1 else
                "Your previous finalization attempt was empty, unusable, or could not be parsed. "
                "Return a substantive, complete Markdown answer now, using only the evidence already "
                "present. Do not request tools, invent facts, or return an empty response."
            ),
        }]
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=final_messages,
                temperature=0.0 if attempt == 2 else TEMPERATURE,
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
            if _is_parse_error(exc) and attempt == 1:
                _emit(activity_callback, "error",
                      "Parsing failed during final synthesis — retrying once with a clean continuation.")
                # Attempt 2 (loop continues) is the simplified, low-temperature retry.
        _emit(activity_callback, "error", last_error)

    fallback = _fallback_report(tool_results, last_error, fallback_context)
    _emit(activity_callback, "fallback", {"reason": last_error, "tool_count": len(tool_results)})
    _emit(activity_callback, "final", fallback)
    return fallback
