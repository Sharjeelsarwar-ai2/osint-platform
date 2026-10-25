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
existing round limit and 3 shrinking final-synthesis attempts.

Request-size budget (the 413 fix): Groq rejected a live ORACLE synthesis
with "Limit 8000, Requested 9750" TPM — the synthesis prompt (all four
specialists' findings, untruncated) plus MAX_TOKENS=4096 of requested
output exceeded the 8000-token on_demand limit. Every request is now
estimated (chars/4, a deliberately conservative heuristic for English/
Markdown — real tokenizers usually use MORE chars per token, so the
estimate overstates tokens) and trimmed BEFORE sending so that
prompt + requested output stays under GROQ_REQUEST_TOKEN_BUDGET (7000).
A 413 / rate_limit_exceeded error is retried with a progressively
smaller payload instead of falling straight back to a fallback report.
"""
import ast
import json
import os
import re

from groq import Groq

from config.settings import (GROQ_API_KEY, GROQ_REQUEST_TOKEN_BUDGET,
                             MAX_TOKENS, MODEL_NAME, SYNTHESIS_MAX_TOKENS,
                             TEMPERATURE)

_client = None
MAX_TOOL_RESULT_CHARS = 6000
REQUEST_TOKEN_BUDGET = int(GROQ_REQUEST_TOKEN_BUDGET or 7000)
SYNTHESIS_MAX_TOKENS = int(SYNTHESIS_MAX_TOKENS or 2048)
# Synthesis attempts: (max_tokens, prompt-budget divisor). Attempt 1 is
# the full budget; each retry halves the prompt and lowers output, so a
# 413 retry can never re-send the same oversized request.
_SYNTHESIS_ATTEMPTS = ((SYNTHESIS_MAX_TOKENS, 1), (1536, 2), (1024, 4))
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


def _is_size_error(exc):
    """True for Groq 413 / TPM rate-limit errors (Request too large)."""
    for attr in ("status_code", "status"):
        if getattr(exc, attr, None) == 413:
            return True
    text = str(exc).lower()
    return ("413" in text and ("large" in text or "token" in text or "rate_limit" in text)) \
        or "request too large" in text or "rate_limit_exceeded" in text \
        or "tokens per minute" in text or "tpm" in text


def estimate_tokens(text):
    """Conservative token estimate: 1 token per 4 chars, minimum 1."""
    if text is None:
        return 0
    return max(1, (len(str(text)) + 3) // 4)


def _message_tokens(message):
    total = 10  # role / ids / structure overhead
    content = message.get("content")
    if isinstance(content, str):
        total += estimate_tokens(content)
    elif isinstance(content, list):
        total += sum(estimate_tokens(str(p)) for p in content)
    for call in message.get("tool_calls", []) or []:
        function = call.get("function", {}) or {}
        total += estimate_tokens(function.get("arguments", ""))
        total += estimate_tokens(function.get("name", ""))
    total += estimate_tokens(message.get("name", ""))
    return total


def _messages_tokens(messages):
    return sum(_message_tokens(m) for m in (messages or []))


def _truncate_middle(text, max_chars):
    """Keep the head and tail of an over-long message, marking the cut."""
    if len(text) <= max_chars or max_chars < 100:
        return text[:max_chars]
    marker = "\n\n[... content trimmed for request-size budget ...]\n\n"
    head = int(max_chars * 0.7) - len(marker) // 2
    tail = max_chars - len(marker) - head
    return text[:head] + marker + text[len(text) - tail:]


def _trim_messages_to_budget(messages, prompt_token_budget, tool_defs_tokens=0):
    """Return a copy of messages whose estimated tokens fit the budget.

    Order of trimming (least destructive first):
      1. Drop the OLDEST assistant+tool blocks, keeping the most recent
         evidence — tool messages are never kept without their assistant
         call, so blocks are dropped whole.
      2. Halve tool-result contents, repeatedly, down to 750 chars.
      3. Middle-truncate the longest non-system message.
    The system message is never dropped. If the budget is impossibly
    small, the result is still the smallest safe shape (system + first
    user, truncated), never an unbounded original.
    """
    import copy

    budget = max(300, int(prompt_token_budget) - int(tool_defs_tokens or 0))
    msgs = copy.deepcopy(list(messages or []))
    if _messages_tokens(msgs) <= budget:
        return msgs
    # 1. Drop oldest blocks after system + first user. A block is an
    # assistant message plus the tool messages that follow it.
    while _messages_tokens(msgs) > budget and len(msgs) > 3:
        # Find the first droppable block: index 2 onwards, unless the
        # first messages are not system/user (then start at 1).
        start = 2 if len(msgs) >= 2 and msgs[0].get("role") == "system" else 1
        if start >= len(msgs):
            break
        end = start + 1
        while end < len(msgs) and msgs[end].get("role") == "tool":
            end += 1
        # If the block starts with tool messages (no assistant), drop them.
        if msgs[start].get("role") == "tool":
            end = start + 1
        del msgs[start:end]
    # 2. Halve tool contents.
    limit = MAX_TOOL_RESULT_CHARS
    while _messages_tokens(msgs) > budget and limit > 750:
        limit //= 2
        for m in msgs:
            if m.get("role") == "tool" and isinstance(m.get("content"), str):
                m["content"] = m["content"][:limit]
    # 3. Middle-truncate the longest non-system message, repeatedly.
    while _messages_tokens(msgs) > budget:
        candidates = [(i, len(str(m.get("content") or "")))
                      for i, m in enumerate(msgs) if m.get("role") != "system"]
        if not candidates:
            break
        idx, length = max(candidates, key=lambda t: t[1])
        if length < 200:
            break
        content = str(msgs[idx].get("content") or "")
        target_chars = max(100, length // 2)
        msgs[idx]["content"] = _truncate_middle(content, target_chars)
        if _messages_tokens(msgs) <= budget:
            break
    return msgs


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
        "**FALLBACK — NOT A REAL SYNTHESIS:** the language model did not produce a synthesis for "
        "this run. What follows is evidence only, compiled from tool results / specialist findings. "
        "Do not treat any risk score or summary below as a model-generated report.",
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
        size_retried = False
        message = None
        tool_defs_tokens = estimate_tokens(json.dumps(clean_tools, ensure_ascii=False)) if clean_tools else 0
        while True:
            prompt_budget = REQUEST_TOKEN_BUDGET - MAX_TOKENS
            if size_retried:
                prompt_budget //= 2
            kwargs = {
                "model": MODEL_NAME,
                "messages": _trim_messages_to_budget(
                    _clean_messages(messages), prompt_budget, tool_defs_tokens),
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
                if _is_size_error(exc) and not size_retried:
                    size_retried = True
                    _emit(activity_callback, "error",
                          f"Request too large in tool round {round_num} — retrying with compressed context.")
                    continue
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
    # Synthesis is where the live 413 happened: the base messages already
    # contain the (compressed) specialist findings, so each attempt is
    # budgeted — prompt + requested output under REQUEST_TOKEN_BUDGET —
    # and each retry after a size error sends a SMALLER payload, never
    # the same oversized request again.
    for attempt, (synth_max_tokens, divisor) in enumerate(_SYNTHESIS_ATTEMPTS, start=1):
        if client is None:
            break
        _emit(activity_callback, "finalizing", {"attempt": attempt, "tool_count": len(tool_results)})
        instruction = (
            "Tool execution is now closed. Do not request or call any tools. "
            "Using only the evidence already present in this conversation, write the final "
            "complete answer requested by the original user prompt. Distinguish verified "
            "observations from uncertainty, cite the tool names and returned facts, and include "
            "a short limitations section. Do not say that more rounds are needed."
            if attempt == 1 else
            "Your previous finalization attempt was empty, unusable, could not be parsed, "
            "or was too large. Return a substantive, complete Markdown answer now, using only "
            "the compressed evidence already present. Do not request tools, invent facts, "
            "or return an empty response."
        )
        prompt_budget = (REQUEST_TOKEN_BUDGET - synth_max_tokens) // divisor
        base_messages = _trim_messages_to_budget(
            _clean_messages(messages), prompt_budget - estimate_tokens(instruction))
        final_messages = base_messages + [{"role": "user", "content": instruction}]
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=final_messages,
                temperature=0.0 if attempt > 1 else TEMPERATURE,
                max_tokens=synth_max_tokens,
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
            if _is_size_error(exc):
                _emit(activity_callback, "error",
                      "Request too large during final synthesis — retrying with compressed context.")
            elif _is_parse_error(exc) and attempt == 1:
                _emit(activity_callback, "error",
                      "Parsing failed during final synthesis — retrying once with a clean continuation.")
        _emit(activity_callback, "error", last_error)

    fallback = _fallback_report(tool_results, last_error, fallback_context)
    _emit(activity_callback, "fallback", {"reason": last_error, "tool_count": len(tool_results)})
    _emit(activity_callback, "final", fallback)
    return fallback
