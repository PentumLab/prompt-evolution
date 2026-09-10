import re
import json
from pathlib import Path

from agent.llm import USE_CONFIG_MAX_TOKENS, get_response_from_llm
from agent.tools import load_tools

def get_tooluse_prompt(tool_infos=[]):
    """
    Get the prompt for using the available tools.
    """
    # If no tools are available, return an empty string
    if not tool_infos or len(tool_infos) == 0:
        return ""
    # Create the prompt
    tools_available = [json.dumps(tool_info, ensure_ascii=False) for tool_info in tool_infos]
    tools_available = '\n\n'.join(tools_available) if tools_available else 'None'
    tooluse_prompt = """Here are the available tools:
```
{tools_available}
```

Use only one tool (if needed) in this format:
<json>
{{
    "tool_name": ...,
    "tool_input": ...
}}
</json>

ONLY USE ONE TOOL PER RESPONSE, AND STRICTLY FOLLOW THE FORMAT OF TOOL_NAME AND TOOL_INPUT ABOVE.
DO NOT HALLUCINATE OR MAKE UP ANYTHING.
Do not use <function_calls>, <invoke_tool>, XML tool calls, or any other
tool-call syntax.

The tool_input must be a JSON object, not a quoted JSON string. Use double
quotes for JSON strings and escape newlines inside strings as \\n.
After a tool call, stop and wait for the real tool result. When the task is
complete, reply with a short plain-text summary without a tool call.
""".format(tools_available=tools_available)
    names = {info["name"] for info in tool_infos}
    if "editor" in names:
        example = {"tool_name": "editor", "tool_input": {
            "command": "view", "path": "/absolute/path/to/target.py"}}
        tooluse_prompt += "\nExample (replace the path with the actual target):\n<json>" + json.dumps(example) + "</json>"
    return tooluse_prompt.strip()

def get_tool_retry_message(response, tool_uses=None):
    """
    Return a corrective message if the response appears to attempt tool use
    but no executable tool call could be parsed.
    """
    if tool_uses is not None and len(tool_uses) > 0:
        return None

    if "<function_calls>" in response or "<invoke_tool>" in response:
        return (
            "Error: Invalid tool-call syntax. Use exactly one tool call in this "
            "format only: <json>{\"tool_name\": \"...\", "
            "\"tool_input\": {...}}</json>. Do not use <function_calls> or "
            "<invoke_tool>."
        )

    # Find positions of the markers
    json_pos = response.find("<json>")
    tool_name_pos = response.find("tool_name")
    tool_input_pos = response.find("tool_input")

    # Check ordering and length condition
    if (
        json_pos != -1
        and tool_name_pos != -1
        and tool_input_pos != -1
        and json_pos < tool_name_pos < tool_input_pos
        and len(response) >= 2000
    ):
        return (
            "Error: Tool call appears incomplete or malformed. Retry with exactly "
            "one complete <json> block containing tool_name and tool_input."
        )

    return None

def _first_json_object(text):
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def _load_tool_input(value):
    value = str(value or "").strip()
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        json_text = _first_json_object(value)
        if not json_text:
            raise
        return json.loads(json_text)


def _extract_parameter(block, name):
    match = re.search(
        rf'<parameter\s+name=["\']{re.escape(name)}["\']\s*>(.*?)(?:</parameter>|$)',
        block,
        re.DOTALL,
    )
    return match.group(1).strip() if match else None


def _extract_json_tool_uses(response):
    pattern = r'<json>\s*(\{.*?\})\s*</json>'
    matches = re.findall(pattern, response, re.DOTALL)
    tool_uses = []

    for match in matches:
        try:
            tool_use = json.loads(match)
            if 'tool_name' not in tool_use or 'tool_input' not in tool_use:
                continue  # Skip invalid tool use
            tool_uses.append(tool_use)
        except json.JSONDecodeError:
            continue  # Skip malformed JSON blocks

    return tool_uses


def _extract_loose_json_tool_uses(response):
    tool_uses = []
    marker = "<json>"
    position = 0

    while True:
        start = response.find(marker, position)
        if start == -1:
            break

        position = start + len(marker)
        json_text = _first_json_object(response[position:])
        if not json_text:
            continue

        try:
            tool_use = json.loads(json_text)
            if 'tool_name' not in tool_use or 'tool_input' not in tool_use:
                continue
            tool_uses.append(tool_use)
        except json.JSONDecodeError:
            continue

    return tool_uses


def _extract_invoke_tool_uses(response):
    invoke_blocks = re.findall(
        r'<invoke_tool>\s*(.*?)\s*</invoke_tool>',
        response,
        re.DOTALL,
    )
    tool_uses = []

    for block in invoke_blocks:
        tool_name = _extract_parameter(block, "tool_name")
        tool_input = _extract_parameter(block, "tool_input")

        if not tool_name or not tool_input:
            continue

        try:
            tool_uses.append(
                {
                    "tool_name": tool_name,
                    "tool_input": _load_tool_input(tool_input),
                }
            )
        except json.JSONDecodeError:
            continue

    return tool_uses


def _extract_function_call_tool_uses(response):
    function_blocks = re.findall(
        r'<function_calls>\s*(.*?)\s*</function_calls>',
        response,
        re.DOTALL,
    )
    tool_uses = []

    for block in function_blocks:
        tool_name = _extract_parameter(block, "tool_name")
        tool_input = _extract_parameter(block, "tool_input")

        if not tool_name or not tool_input:
            continue

        try:
            tool_uses.append(
                {
                    "tool_name": tool_name,
                    "tool_input": _load_tool_input(tool_input),
                }
            )
        except json.JSONDecodeError:
            continue

    return tool_uses


def check_for_tool_uses(response):
    """
    Checks if the response contains one or more tool calls.
    Returns a list of tool use dictionaries.
    """
    tool_uses = _extract_json_tool_uses(response)
    if not tool_uses:
        tool_uses = _extract_loose_json_tool_uses(response)
    if not tool_uses:
        tool_uses = _extract_invoke_tool_uses(response)
    if not tool_uses:
        tool_uses = _extract_function_call_tool_uses(response)
    return tool_uses if tool_uses else None

def process_tool_call(tools_dict, tool_name, tool_input):
    try:
        if tool_name in tools_dict:
            return tools_dict[tool_name]['function'](**tool_input)
        else:
            return f"Error: Tool '{tool_name}' not found"
    except Exception as e:
        return f"Error executing tool '{tool_name}': {str(e)}"


def retain_executed_tool_call(response, history, multiple_tool_calls=False):
    """Do not feed unexecuted calls or imagined results back to the model."""
    calls = check_for_tool_uses(response)
    if multiple_tool_calls or not calls:
        return response
    response = '<json>\n' + json.dumps(calls[0], ensure_ascii=False) + '\n</json>'
    if history and history[-1].get('role') == 'assistant':
        history[-1] = dict(history[-1])
        key = 'text' if 'text' in history[-1] else 'content'
        history[-1][key] = response
    return response


def tool_budget_notice(limit, used):
    if limit <= 0:
        return ''
    remaining = max(0, limit - used)
    message = (f'TOOL BUDGET: {remaining} remaining out of {limit} for this entire run. '
               'Each executed tool attempt (including failures) and each tool-format correction '
               'consumes one slot. Corrections share this budget to prevent endless retry loops. '
               'Prioritize required work over optional documentation.')
    if remaining == 0:
        message += ' No further tools can execute. Reply in plain text and explicitly report any unfinished work.'
    return '\n\n' + message


def _save_resume_state(path, **state):
    if not path:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_resume_state(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Resume state not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def chat_with_agent(
    msg,
    model="claude-4-sonnet-genai",
    msg_history=None,
    logging=print,
    tools_available=[],  # Empty list means no tools, 'all' means all tools
    multiple_tool_calls=False,  # Whether to allow multiple tool calls in a single response
    max_tool_calls=40,  # Shared tool-attempt and format-correction budget; -1 for unlimited
    max_tokens=USE_CONFIG_MAX_TOKENS,
    resume_state_file=None,
    resume=False,
):
    get_response_fn = get_response_from_llm
    # Construct message
    if msg_history is None:
        msg_history = []
    new_msg_history = msg_history

    try:
        # Load all tools
        all_tools = load_tools(logging=logging, names=tools_available)
        tools_dict = {tool['info']['name']: tool for tool in all_tools}
        system_msg = f"{get_tooluse_prompt([tool['info'] for tool in all_tools])}\n\n"
        num_tool_calls = 0
        pending_msg = system_msg + msg
        response = None

        if resume:
            state = _load_resume_state(resume_state_file)
            new_msg_history = state.get("msg_history", new_msg_history)
            num_tool_calls = state.get("num_tool_calls", 0)
            if state.get("complete"):
                logging(f"Resume state is already complete: {resume_state_file}")
                return new_msg_history
            pending_msg = state.get("pending_msg")
            response = None if pending_msg else state.get("last_response")
            if pending_msg is None and response is None:
                pending_msg = system_msg + msg
            logging(f"Resuming from: {resume_state_file}")

        # Call API
        if response is None:
            logging(f"Input: {repr(msg)}")
            _save_resume_state(
                resume_state_file,
                msg_history=new_msg_history,
                pending_msg=pending_msg,
                num_tool_calls=num_tool_calls,
                complete=False,
            )
            response, new_msg_history, info = get_response_fn(
                msg=pending_msg + tool_budget_notice(max_tool_calls, num_tool_calls),
                model=model,
                msg_history=new_msg_history,
                max_tokens=max_tokens,
            )
            logging(f"Output: {repr(response)}")
            response = retain_executed_tool_call(response, new_msg_history, multiple_tool_calls)
            _save_resume_state(
                resume_state_file,
                msg_history=new_msg_history,
                pending_msg=None,
                num_tool_calls=num_tool_calls,
                last_response=response,
                complete=False,
            )
        else:
            logging("Continuing from last saved model response.")
            response = retain_executed_tool_call(response, new_msg_history, multiple_tool_calls)
        # logging(f"Info: {repr(info)}")

        # Tool use
        tool_uses = check_for_tool_uses(response)
        tool_retry_message = get_tool_retry_message(response, tool_uses)
        while tool_uses or tool_retry_message:
            # Check for max tool calls
            if max_tool_calls > 0 and num_tool_calls >= max_tool_calls:
                logging("Error: Maximum number of tool calls reached.")
                break

            tool_msgs = []

            # Process tool uses
            if tool_uses:
                tool_uses = tool_uses if multiple_tool_calls else tool_uses[:1]
                for tool_use in tool_uses:
                    tool_name = tool_use['tool_name']
                    tool_input = tool_use['tool_input']
                    tool_output = process_tool_call(tools_dict, tool_name, tool_input)
                    num_tool_calls += 1
                    tool_msg = "<json>\n" + json.dumps({
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_output": tool_output,
                    }, ensure_ascii=False) + "\n</json>"
                    logging(f"Tool output: {repr(tool_msg)}")
                    tool_msgs.append(tool_msg)

            # Check for retry
            if tool_retry_message:
                logging(tool_retry_message)
                tool_msgs.append(tool_retry_message)
                # Bound malformed-call retries using the same run budget.
                num_tool_calls += 1

            # Get tool response
            # Tool definitions remain in the first history message.
            pending_msg = '\n\n'.join(tool_msgs)
            _save_resume_state(
                resume_state_file,
                msg_history=new_msg_history,
                pending_msg=pending_msg,
                num_tool_calls=num_tool_calls,
                complete=False,
            )
            response, new_msg_history, info = get_response_fn(
                msg=pending_msg + tool_budget_notice(max_tool_calls, num_tool_calls),
                model=model,
                msg_history=new_msg_history,
                max_tokens=max_tokens,
            )
            logging(f"Output: {repr(response)}")
            response = retain_executed_tool_call(response, new_msg_history, multiple_tool_calls)
            _save_resume_state(
                resume_state_file,
                msg_history=new_msg_history,
                pending_msg=None,
                num_tool_calls=num_tool_calls,
                last_response=response,
                complete=False,
            )
            # logging(f"Info: {repr(info)}")

            # Check for next tool use
            tool_uses = check_for_tool_uses(response)
            tool_retry_message = get_tool_retry_message(response, tool_uses)

    except Exception as e:
        logging(f"Error: {str(e)}")
        raise e

    _save_resume_state(
        resume_state_file,
        msg_history=new_msg_history,
        pending_msg=None,
        num_tool_calls=num_tool_calls,
        complete=True,
    )
    return new_msg_history

if __name__ == "__main__":
    msg = """hello"""
    new_msg_history = chat_with_agent(msg)
