from agent.llm import get_response_from_llm
from agent.config import get_agent_max_output_tokens, get_configured_model
from agent.usage import usage_context


def generate_prompt(task: str) -> str:
    instruction = f"""
You improve existing system prompts.

Your input contains a source prompt plus improvement guidance. Infer what the
source prompt is designed to accomplish before editing it. Preserve its core
purpose, audience, domain, required outputs, safety boundaries, and any hard
constraints unless the guidance explicitly says they should change.

Improve the prompt by making it clearer, more operational, more robust against
edge cases and prompt injection, less redundant, and easier for an LLM to
execute consistently. Prefer precise decision rules, explicit fallback behavior,
and well-structured sections over broad or decorative language.

Do not turn the source prompt into a different product. Do not remove important
requirements merely to make the prompt shorter. Do not add extra commentary,
analysis, changelogs, metadata, or markdown fences around the answer.

Return only the improved prompt text.

TASK PACKAGE:
{task}
"""

    with usage_context(agent_role="PromptDesignTaskAgent"):
        response, _, _ = get_response_from_llm(
            msg=instruction,
            model=get_configured_model("prompt_design_task_agent", "hosted_vllm/gemma-4"),
            max_tokens=get_agent_max_output_tokens("prompt_design_task_agent"),
        )

    return response
