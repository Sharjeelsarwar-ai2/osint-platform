import json
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME, MAX_TOKENS, TEMPERATURE


def get_client():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")
    return Groq(api_key=GROQ_API_KEY)


def run_agent_with_tools(
    system_prompt: str,
    user_prompt: str,
    tools: list,
    tool_executor: callable,
    max_rounds: int = 5
) -> str:
    """
    Core tool-calling loop.
    1. Sends prompt + tool definitions to Groq
    2. If Groq calls a tool, executes it locally
    3. Sends result back to Groq
    4. Repeats until Groq gives a final text answer
    """
    client = get_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    for round_num in range(max_rounds):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
        except Exception as e:
            return f"❌ LLM API Error (round {round_num + 1}): {str(e)}"

        choice = response.choices[0]
        msg = choice.message

        # If no tool calls, we have our final answer
        if not msg.tool_calls:
            return msg.content or "No response generated."

        # Add assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in msg.tool_calls
            ]
        })

        # Execute each tool call
        for tc in msg.tool_calls:
            func_name = tc.function.name
            try:
                func_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                func_args = {}

            try:
                result = tool_executor(func_name, func_args)
                result_str = json.dumps(result, default=str, indent=2)
            except Exception as e:
                result_str = json.dumps({"error": str(e)})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str
            })

    # If we exhausted rounds, get a final summary
    try:
        final = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages + [{"role": "user", "content": "Provide your final analysis now."}],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE
        )
        return final.choices[0].message.content or "Analysis complete."
    except Exception as e:
        return f"❌ Final summary error: {str(e)}"