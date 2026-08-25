from agent.llm import get_response_from_llm


def generate_prompt(task: str) -> str:
    instruction = f"""
You are designing a reusable system prompt.

Read the task below carefully and produce the best system prompt you can.

Return only the finished system prompt.

TASK:
{task}
"""

    response, _, _ = get_response_from_llm(
        msg=instruction,
        model="hosted_vllm/gemma-4",
        max_tokens=8000,
    )

    return response
